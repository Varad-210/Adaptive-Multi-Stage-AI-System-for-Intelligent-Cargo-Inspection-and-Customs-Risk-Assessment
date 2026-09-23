from flask import Flask, request, jsonify, render_template
from ultralytics import YOLO
from PIL import Image
import io
import os
import base64
import time

app = Flask(__name__)
import secrets
app.secret_key = secrets.token_hex(16)

from auth.models import init_db
from auth.routes import auth_bp
from auth.decorators import login_required
from utils.metrics import MetricsTracker

# Initialize database
init_db()

# Register auth blueprint
app.register_blueprint(auth_bp, url_prefix='/auth')

# Register comparison blueprint
from comparison.routes import comparison_bp
app.register_blueprint(comparison_bp)

# Load your model
MODEL_PATH = "yolo11n.pt"
model = YOLO(MODEL_PATH)

dashboard_stats = {
    "total_scans": 0,
    "clean_scans": 0, 
    "anomalies_found": 0,
    "re_scans": 0
}

# Define how dangerous each item actually is
THREAT_WEIGHTS = {
    'Gun': 1.0,      # Critical Threat: 100% of confidence becomes Risk
    'Knife': 0.85,   # High Threat: 85% of confidence becomes Risk
    'Scissors': 0.50,# Medium Threat: 50% of confidence becomes Risk
    'Pliers': 0.25,  # Low Threat (Tools): 25% of confidence becomes Risk
    'Wrench': 0.25   # Low Threat (Tools): 25% of confidence becomes Risk
}

# Create feedback folders automatically
FEEDBACK_FOLDERS = ["object_in_object", "undetectable", "half_object_detected"]
for folder in FEEDBACK_FOLDERS:
    os.makedirs(os.path.join("feedback_data", folder), exist_ok=True)

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/scan-history')
@login_required
def scan_history():
    return render_template('scan_history.html')

@app.route('/scan', methods=['POST'])
@login_required
def scan_image():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    tracker = MetricsTracker()
    tracker.start()

    file = request.files['image']
    img_bytes = file.read()
    img = Image.open(io.BytesIO(img_bytes))
    
    tracker.mark_pre_process()

    results = model.predict(source=img)
    
    tracker.mark_inference()
    
    detections = []
    total_risk_score = 0.0  # Start with 0 risk
    
    for r in results:
        for box in r.boxes:
            class_name = model.names[int(box.cls[0])]
            conf_percent = round(float(box.conf[0]) * 100, 2)
            
            # --- THE NEW RISK MATH ---
            # Get the weight (default to 0.5 if it's a new unknown class)
            weight = THREAT_WEIGHTS.get(class_name, 0.5) 
            # Multiply confidence by the danger weight and add it to the total bag risk
            total_risk_score += (conf_percent * weight)
            
            detections.append({
                "class": class_name,
                "confidence": conf_percent
            })

    # Cap the maximum risk at 100%
    final_risk = min(100.0, round(total_risk_score, 1))

    # Update Dashboard Stats
    dashboard_stats["total_scans"] += 1
    if len(detections) > 0:
        dashboard_stats["anomalies_found"] += 1
    else:
        dashboard_stats["clean_scans"] += 1 

    # Draw boxes and convert to Base64
    annotated_img_array = results[0].plot() 
    annotated_pil = Image.fromarray(annotated_img_array[..., ::-1])
    
    buffered = io.BytesIO()
    annotated_pil.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    tracker.mark_post_process()
    metrics = tracker.get_metrics()
    
    # Calculate some extra stats for frontend
    if detections:
        metrics['avg_confidence'] = round(sum(d['confidence'] for d in detections) / len(detections), 2)
    else:
        metrics['avg_confidence'] = 0

    return jsonify({
        "image": "data:image/jpeg;base64," + img_base64,
        "detections": detections,
        "stats": dashboard_stats,
        "risk_score": final_risk,
        "metrics": metrics
    })

@app.route('/feedback', methods=['POST'])
@login_required
def save_feedback():
    if 'image' not in request.files or 'reason' not in request.form:
        return jsonify({"error": "Missing data"}), 400

    file = request.files['image']
    reason = request.form['reason']
    
    filename = f"re_scan_{int(time.time())}.jpg"
    save_path = os.path.join("feedback_data", reason, filename)
    file.save(save_path)
    
    dashboard_stats["re_scans"] += 1
    return jsonify({"message": "Saved to " + reason, "stats": dashboard_stats})

from flask import send_file
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
    
    filepath = None
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