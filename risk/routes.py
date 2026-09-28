from flask import Blueprint, render_template, request, jsonify, session, send_file
from auth.decorators import login_required
from auth.models import (
    save_risk_assessment, get_risk_assessments, get_risk_assessment_by_case,
    update_inspection_status, save_incident_report, get_incident_reports
)
from utils.risk_engine import generate_report_id, RISK_CONFIG
from utils.enhanced_pdf_report import generate_inspection_report
import os, json

risk_bp = Blueprint('risk', __name__)


# ----------------------------------------------------------------
# Pages
# ----------------------------------------------------------------
@risk_bp.route('/risk-intelligence')
@login_required
def risk_intelligence():
    assessments = get_risk_assessments(limit=200)
    summary = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
    for a in assessments:
        lvl = a.get('risk_level', 'LOW')
        summary[lvl] = summary.get(lvl, 0) + 1
    return render_template('risk_intelligence.html', assessments=assessments, summary=summary)


@risk_bp.route('/risk-intelligence/<case_id>')
@login_required
def risk_detail(case_id):
    assessment = get_risk_assessment_by_case(case_id)
    if not assessment:
        return render_template('risk_detail.html', assessment=None, error='Case not found')
    return render_template('risk_detail.html', assessment=assessment)


@risk_bp.route('/automated-reports')
@login_required
def automated_reports():
    reports = get_incident_reports(limit=200)
    return render_template('automated_reports.html', reports=reports)


# ----------------------------------------------------------------
# APIs
# ----------------------------------------------------------------
@risk_bp.route('/api/risk/update-status', methods=['POST'])
@login_required
def update_status():
    data = request.json or {}
    case_id = data.get('case_id')
    status  = data.get('status')
    if not case_id or status not in ('PENDING', 'CLEARED', 'ESCALATED'):
        return jsonify({'error': 'Invalid request'}), 400
    update_inspection_status(case_id, status)
    return jsonify({'success': True})


@risk_bp.route('/api/risk/generate-report', methods=['POST'])
@login_required
def generate_report():
    data = request.json or {}
    case_id = data.get('case_id')
    if not case_id:
        return jsonify({'error': 'case_id required'}), 400

    assessment = get_risk_assessment_by_case(case_id)
    if not assessment:
        return jsonify({'error': 'Case not found'}), 404

    from auth.models import get_user_by_id
    operator = get_user_by_id(session.get('user_id', 0))
    assessment['operator_name'] = operator.get('name', 'Unknown') if operator else 'Unknown'

    report_id = generate_report_id()
    assessment['report_id'] = report_id

    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    pdf_path = os.path.join(reports_dir, f"{report_id}.pdf")

    try:
        generate_inspection_report(assessment, pdf_path)
        save_incident_report({
            'report_id':      report_id,
            'case_id':        case_id,
            'generated_by':   session.get('user_id'),
            'trigger_reason': 'manual',
            'risk_score':     assessment.get('final_risk_score'),
            'risk_level':     assessment.get('risk_level'),
            'pdf_path':       pdf_path,
            'status':         'GENERATED',
        })
        return jsonify({'success': True, 'report_id': report_id})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@risk_bp.route('/api/reports/download/<report_id>')
@login_required
def download_report(report_id):
    # Sanitise report_id to prevent path traversal
    safe_id = report_id.replace('/', '').replace('..', '')
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    pdf_path = os.path.join(reports_dir, f"{safe_id}.pdf")
    if not os.path.exists(pdf_path):
        return 'Report file not found', 404
    return send_file(pdf_path, as_attachment=True, download_name=f"{safe_id}.pdf")


@risk_bp.route('/api/analytics/overview')
@login_required
def analytics_overview():
    from auth.models import get_analytics_overview
    return jsonify(get_analytics_overview())


@risk_bp.route('/api/analytics/trends')
@login_required
def analytics_trends():
    from auth.models import get_trend_data
    days = int(request.args.get('days', 30))
    return jsonify(get_trend_data(days))
