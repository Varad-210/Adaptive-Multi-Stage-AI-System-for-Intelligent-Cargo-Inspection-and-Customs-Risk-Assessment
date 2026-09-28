import os, json, base64, io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
try:
    from reportlab.platypus import Image as RLImage
except ImportError:
    from reportlab.platypus.flowables import Image as RLImage
from reportlab.lib.colors import HexColor
from PIL import Image

# Brand colors
C_PRIMARY  = HexColor('#2563EB')
C_DARK     = HexColor('#111827')
C_GRAY     = HexColor('#6B7280')
C_LGRAY    = HexColor('#F3F4F6')
C_BORDER   = HexColor('#E2E8F0')
C_DANGER   = HexColor('#DC2626')
C_WARNING  = HexColor('#D97706')
C_HIGH     = HexColor('#EA580C')
C_SUCCESS  = HexColor('#16A34A')
C_WHITE    = colors.white

RISK_COLORS = {
    'LOW':      C_SUCCESS,
    'MEDIUM':   C_WARNING,
    'HIGH':     C_HIGH,
    'CRITICAL': C_DANGER,
}
RISK_HEX = {
    'LOW':      '#16A34A',
    'MEDIUM':   '#D97706',
    'HIGH':     '#EA580C',
    'CRITICAL': '#DC2626',
}


def generate_inspection_report(assessment: dict, filepath: str) -> str:
    """Generate a professional A4 PDF inspection report."""
    doc = SimpleDocTemplate(
        filepath, pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=14*mm, bottomMargin=18*mm
    )
    styles = getSampleStyleSheet()
    story  = []

    risk_level = assessment.get('risk_level', 'LOW')
    lvl_hex    = RISK_HEX.get(risk_level, '#111827')
    risk_score = assessment.get('final_risk_score', 0)

    # ----------------------------------------------------------------
    # HEADER
    # ----------------------------------------------------------------
    hdr = Table([[
        Paragraph('<font size="16" color="#2563EB"><b>CargoSight AI</b></font><br/>'
                  '<font size="9" color="#6B7280">AI Inspection Platform</font>', styles['Normal']),
        Paragraph('<font size="11" color="#111827"><b>AUTOMATED INSPECTION REPORT</b></font><br/>'
                  f'<font size="8" color="#6B7280">Generated: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</font>',
                  ParagraphStyle('rh', parent=styles['Normal'], alignment=TA_RIGHT))
    ]], colWidths=[95*mm, 75*mm])
    hdr.setStyle(TableStyle([
        ('VALIGN',       (0,0),(-1,-1),'MIDDLE'),
        ('LINEBELOW',    (0,0),(-1, 0),1, C_BORDER),
        ('BOTTOMPADDING',(0,0),(-1,-1),6),
    ]))
    story.append(hdr)
    story.append(Spacer(1, 6*mm))

    # ----------------------------------------------------------------
    # METADATA TABLE
    # ----------------------------------------------------------------
    meta_style = ParagraphStyle('mv', fontName='Helvetica', fontSize=9, textColor=C_DARK)
    meta_label = ParagraphStyle('ml', fontName='Helvetica-Bold', fontSize=9, textColor=C_GRAY)
    meta_rows = [
        [Paragraph('Report ID', meta_label),   Paragraph(assessment.get('report_id','N/A'), meta_style),
         Paragraph('Case ID',   meta_label),   Paragraph(assessment.get('case_id','N/A'),   meta_style)],
        [Paragraph('Operator',  meta_label),   Paragraph(assessment.get('operator_name','Unknown'), meta_style),
         Paragraph('File',      meta_label),   Paragraph(assessment.get('filename','Unknown'),       meta_style)],
        [Paragraph('Model',     meta_label),   Paragraph(assessment.get('model','YOLOv11'), meta_style),
         Paragraph('Inference', meta_label),   Paragraph(f"{assessment.get('inference_time_ms',0):.1f} ms", meta_style)],
        [Paragraph('System',    meta_label),   Paragraph('CargoSight AI v1.0', meta_style),
         Paragraph('Date',      meta_label),   Paragraph(str(assessment.get('scan_date',''))[:16], meta_style)],
    ]
    mt = Table(meta_rows, colWidths=[28*mm, 62*mm, 28*mm, 52*mm])
    mt.setStyle(TableStyle([
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[C_LGRAY, C_WHITE]),
        ('GRID',        (0,0),(-1,-1), 0.5, C_BORDER),
        ('TOPPADDING',  (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('LEFTPADDING', (0,0),(-1,-1), 5),
    ]))
    story.append(mt)
    story.append(Spacer(1, 6*mm))

    # ----------------------------------------------------------------
    # RISK SUMMARY BOX
    # ----------------------------------------------------------------
    status = assessment.get('inspection_status', 'PENDING')
    risk_box = Table([[
        Paragraph(
            f'<font size="32" color="{lvl_hex}"><b>{risk_score}</b></font>'
            f'<font size="12" color="{lvl_hex}"> / 100</font>',
            ParagraphStyle('rs', fontName='Helvetica', fontSize=32)
        ),
        Paragraph(
            f'<font size="18" color="{lvl_hex}"><b>{risk_level} RISK</b></font><br/>'
            f'<font size="10" color="#6B7280">Inspection Status: <b>{status}</b></font>',
            ParagraphStyle('rl', fontName='Helvetica', fontSize=18)
        )
    ]], colWidths=[50*mm, 120*mm])
    risk_box.setStyle(TableStyle([
        ('BOX',         (0,0),(-1,-1), 2, HexColor(lvl_hex)),
        ('BACKGROUND',  (0,0),(-1,-1), C_LGRAY),
        ('TOPPADDING',  (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING', (0,0),(-1,-1), 12),
        ('VALIGN',      (0,0),(-1,-1), 'MIDDLE'),
    ]))
    story.append(risk_box)
    story.append(Spacer(1, 6*mm))

    # ----------------------------------------------------------------
    # RISK FACTORS
    # ----------------------------------------------------------------
    h3 = ParagraphStyle('h3', fontName='Helvetica-Bold', fontSize=11, textColor=C_DARK, spaceAfter=4)
    bullet = ParagraphStyle('bullet', fontName='Helvetica', fontSize=9, textColor=C_DARK,
                            leftIndent=10, spaceAfter=3)
    story.append(Paragraph('Risk Assessment Factors', h3))
    factors = assessment.get('risk_factors', [])
    if factors:
        for f in factors:
            story.append(Paragraph(f'\u2022  {f}', bullet))
    else:
        story.append(Paragraph('No specific risk factors identified.', styles['Normal']))
    story.append(Spacer(1, 5*mm))

    # ----------------------------------------------------------------
    # DETECTION TABLE
    # ----------------------------------------------------------------
    story.append(Paragraph('AI Detection Results', h3))
    det_head_style = TableStyle([
        ('FONTNAME',   (0,0),(-1, 0),'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('BACKGROUND', (0,0),(-1, 0), C_PRIMARY),
        ('TEXTCOLOR',  (0,0),(-1, 0), C_WHITE),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[C_WHITE, C_LGRAY]),
        ('GRID',       (0,0),(-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1), 5),
    ])
    det_data = [['Object / Class', 'Confidence', 'Assessment']]
    dets = assessment.get('detections', [])
    for d in dets:
        det_data.append([
            d.get('class','Unknown'), f"{d.get('confidence',0)}%",
            'Potential anomaly \u2014 requires manual verification'
        ])
    if not dets:
        det_data.append(['No objects detected', '\u2014', 'Scan completed normally'])
    dt = Table(det_data, colWidths=[48*mm, 28*mm, 94*mm])
    dt.setStyle(det_head_style)
    story.append(dt)
    story.append(Spacer(1, 5*mm))

    # ----------------------------------------------------------------
    # SCORE BREAKDOWN
    # ----------------------------------------------------------------
    story.append(Paragraph('Score Breakdown', h3))
    sb_data = [
        ['Component', 'Score', 'Weight', 'Contribution'],
        ['AI Detection',        f"{assessment.get('detection_score',0):.1f}",      '40%', f"{assessment.get('detection_score',0):.1f} pts"],
        ['Anomaly Count',       f"{assessment.get('anomaly_score',0):.1f}",         '30%', f"{assessment.get('anomaly_score',0):.1f} pts"],
        ['Model Agreement',     f"{assessment.get('model_agreement_score',0):.1f}",'20%', f"{assessment.get('model_agreement_score',0):.1f} pts"],
        ['Historical Pattern',  f"{assessment.get('historical_score',0):.1f}",     '10%', f"{assessment.get('historical_score',0):.1f} pts"],
        ['FINAL RISK SCORE',    '',                                                  '',    f"{risk_score:.1f} / 100"],
    ]
    sb = Table(sb_data, colWidths=[65*mm, 28*mm, 28*mm, 49*mm])
    sb.setStyle(TableStyle([
        ('FONTNAME',   (0,0),(-1, 0),'Helvetica-Bold'),
        ('FONTNAME',   (0,-1),(-1,-1),'Helvetica-Bold'),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('BACKGROUND', (0,0),(-1, 0), C_PRIMARY),
        ('BACKGROUND', (0,-1),(-1,-1), C_LGRAY),
        ('TEXTCOLOR',  (0,0),(-1, 0), C_WHITE),
        ('ROWBACKGROUNDS',(0,1),(-1,-2),[C_WHITE, C_LGRAY]),
        ('GRID',       (0,0),(-1,-1), 0.5, C_BORDER),
        ('TOPPADDING', (0,0),(-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4),
        ('LEFTPADDING',(0,0),(-1,-1), 5),
    ]))
    story.append(sb)
    story.append(Spacer(1, 6*mm))

    # ----------------------------------------------------------------
    # X-RAY IMAGE
    # ----------------------------------------------------------------
    image_b64 = assessment.get('image_b64')
    if image_b64:
        try:
            if image_b64.startswith('data:image'):
                image_b64 = image_b64.split(',')[1]
            img_bytes = base64.b64decode(image_b64)
            pil = Image.open(io.BytesIO(img_bytes)).convert('RGB')
            tmp = filepath + '_tmp.jpg'
            pil.save(tmp, 'JPEG')
            story.append(Paragraph('X-Ray Image', h3))
            story.append(RLImage(tmp, width=140*mm, height=90*mm, kind='proportional'))
            story.append(Spacer(1, 4*mm))
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception as e:
            story.append(Paragraph(f'Image could not be rendered: {e}', styles['Normal']))

    # ----------------------------------------------------------------
    # FOOTER DISCLAIMER
    # ----------------------------------------------------------------
    story.append(Spacer(1, 6*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=C_BORDER))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        '<font size="8" color="#6B7280"><b>DISCLAIMER:</b> This is an automated inspection report generated by '
        'CargoSight AI. All findings represent potential anomalies requiring manual verification by authorized '
        'personnel. This report does NOT constitute evidence of criminal activity, smuggling, or any legal violation. '
        'Final determination must be made by a qualified customs officer. Unauthorized access to this report is prohibited.</font>',
        styles['Normal']
    ))

    doc.build(story)
    return filepath
