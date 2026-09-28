from flask import Flask, request, jsonify, render_template, session, send_file
from ultralytics import YOLO
from PIL import Image
import io
import os
import base64
import time
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

from auth.models import init_db, save_risk_assessment
from auth.routes import auth_bp
from auth.decorators import login_required
from utils.metrics import MetricsTracker
from utils.risk_engine import calculate_risk_score, generate_case_id, RISK_CONFIG

# Initialize database (creates all tables including new ones)
init_db()

# Register Blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')

from comparison.routes import comparison_bp
app.register_blueprint(comparison_bp)

from risk.routes import risk_bp
app.register_blueprint(risk_bp)

from analytics.routes import analytics_bp
app.register_blueprint(analytics_bp)

# Load primary YOLO model
MODEL_PATH = "yolo11n.pt"
model = YOLO(MODEL_PATH)

# In-memory session stats (resets on restart)
dashboard_stats = {
    "total_scans": 0,
    "clean_scans": 0,
    "anomalies_found": 0,
    "re_scans": 0,
}

# Create feedback folders
FEEDBACK_FOLDERS = ["object_in_object", "undetectable", "half_object_detected"]
for folder in FEEDBACK_FOLDERS:
    os.makedirs(os.path.join("feedback_data", folder), exist_ok=True)


# ----------------------------------------------------------------
# Pages
# ----------------------------------------------------------------
@app.route('/')
@login_required
def index():
    return render_template('index.html')


@app.route('/scan-history')
@login_required
def scan_history():
    return render_template('scan_history.html')


# ----------------------------------------------------------------
# Scan — AI detection + Risk Assessment persistence
# ----------------------------------------------------------------
@app.route('/scan', methods=['POST'])
@login_required
def scan_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    tracker = MetricsTracker()
    tracker.start()

    file = request.files['image']
    filename = file.filename or "unknown.jpg"
    img_bytes = file.read()
    img = Image.open(io.BytesIO(img_bytes))

    tracker.mark_pre_process()
    results = model.predict(source=img, verbose=False)
    tracker.mark_inference()

    detections = []
    for r in results:
        for box in r.boxes:
            class_name = model.names[int(box.cls[0])]
            conf_percent = round(float(box.conf[0]) * 100, 2)
            detections.append({"class": class_name, "confidence": conf_percent})

    # ── NEW: use the risk engine ──────────────────────────────────
    risk_result = calculate_risk_score(detections)
    final_risk  = risk_result['final_risk_score']
    risk_level  = risk_result['risk_level']
    # ─────────────────────────────────────────────────────────────

    # Annotated image → Base64
    annotated_pil = Image.fromarray(results[0].plot()[..., ::-1])
    buffered = io.BytesIO()
    annotated_pil.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    tracker.mark_post_process()
    metrics = tracker.get_metrics()
    metrics['avg_confidence'] = risk_result['avg_confidence']

    # Update session stats
    dashboard_stats["total_scans"] += 1
    if detections:
        dashboard_stats["anomalies_found"] += 1
    else:
        dashboard_stats["clean_scans"] += 1

    # ── Persist risk assessment ───────────────────────────────────
    case_id = generate_case_id()
    try:
        save_risk_assessment({
            'case_id':               case_id,
            'operator_id':           session.get('user_id'),
            'filename':              filename,
            'model':                 MODEL_PATH,
            'detections':            detections,
            'avg_confidence':        risk_result['avg_confidence'],
            'num_detections':        len(detections),
            'detection_score':       risk_result['detection_score'],
            'anomaly_score':         risk_result['anomaly_score'],
            'model_agreement_score': risk_result['model_agreement_score'],
            'historical_score':      risk_result['historical_score'],
            'final_risk_score':      final_risk,
            'risk_level':            risk_level,
            'risk_factors':          risk_result['risk_factors'],
            'inspection_status':     'PENDING',
            'inference_time_ms':     metrics['inference_time_ms'],
        })

        # Auto-generate report if score meets threshold (non-blocking)
        if final_risk >= RISK_CONFIG['auto_report_threshold']:
            try:
                _auto_generate_report(case_id, session.get('user_id'), risk_result, filename)
            except Exception:
                pass  # never block the scan response
    except Exception:
        pass  # never block the scan response
    # ─────────────────────────────────────────────────────────────

    return jsonify({
        "image":      "data:image/jpeg;base64," + img_base64,
        "detections": detections,
        "stats":      dashboard_stats,
        "risk_score": final_risk,
        "risk_level": risk_level,
        "risk_factors": risk_result['risk_factors'],
        "case_id":    case_id,
        "metrics":    metrics,
    })


def _auto_generate_report(case_id, operator_id, risk_result, filename):
    """Generate a PDF report automatically when threshold is met."""
    from auth.models import get_risk_assessment_by_case, save_incident_report, get_user_by_id
    from utils.enhanced_pdf_report import generate_inspection_report
    from utils.risk_engine import generate_report_id

    assessment = get_risk_assessment_by_case(case_id)
    if not assessment:
        return

    operator = get_user_by_id(operator_id or 0)
    assessment['operator_name'] = operator.get('name', 'System') if operator else 'System'
    report_id = generate_report_id()
    assessment['report_id'] = report_id

    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"{report_id}.pdf")

    generate_inspection_report(assessment, pdf_path)
    save_incident_report({
        'report_id':      report_id,
        'case_id':        case_id,
        'generated_by':   operator_id,
        'trigger_reason': 'auto_threshold',
        'risk_score':     risk_result['final_risk_score'],
        'risk_level':     risk_result['risk_level'],
        'pdf_path':       pdf_path,
        'status':         'GENERATED',
    })


# ----------------------------------------------------------------
# Feedback / retraining
# ----------------------------------------------------------------
@app.route('/feedback', methods=['POST'])
@login_required
def save_feedback():
    if 'image' not in request.files or 'reason' not in request.form:
        return jsonify({"error": "Missing data"}), 400

    file   = request.files['image']
    reason = request.form['reason']
    filename = f"re_scan_{int(time.time())}.jpg"
    save_path = os.path.join("feedback_data", reason, filename)
    file.save(save_path)

    dashboard_stats["re_scans"] += 1
    return jsonify({"message": "Saved to " + reason, "stats": dashboard_stats})


# ----------------------------------------------------------------
# Export endpoints (unchanged)
# ----------------------------------------------------------------
from utils.pdf_export import export_to_pdf
from utils.csv_export import export_to_csv
from utils.json_export import export_to_json

@app.route('/export/<format>', methods=['POST'])
@login_required
def export_result(format):
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    data['officer_name'] = session.get('name', 'Unknown')

    if format == 'pdf':
        filepath = export_to_pdf(data)
    elif format == 'csv':
        filepath = export_to_csv(data)
    elif format == 'json':
        filepath = export_to_json(data)
    else:
        return jsonify({"error": "Invalid format"}), 400

    return send_file(filepath, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, port=5000)
