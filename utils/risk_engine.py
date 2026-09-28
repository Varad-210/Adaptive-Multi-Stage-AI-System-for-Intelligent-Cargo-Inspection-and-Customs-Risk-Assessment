import json
import secrets
from datetime import datetime, timezone

# =====================================================================
# RISK SCORING CONFIGURATION  (single source of truth)
# =====================================================================
RISK_CONFIG = {
    'weights': {
        'detection': 0.40,
        'anomaly': 0.30,
        'model_agreement': 0.20,
        'historical': 0.10,
    },
    'thresholds': {
        'MEDIUM': 30,
        'HIGH': 60,
        'CRITICAL': 80,
    },
    'threat_weights': {
        'Gun': 1.0, 'Pistol': 1.0, 'Rifle': 1.0,
        'Knife': 0.85, 'Blade': 0.85,
        'Scissors': 0.50,
        'Pliers': 0.25, 'Wrench': 0.25,
        'default': 0.40,
    },
    'auto_report_threshold': 60,
}


def get_risk_level(score: float) -> str:
    t = RISK_CONFIG['thresholds']
    if score >= t['CRITICAL']:
        return 'CRITICAL'
    if score >= t['HIGH']:
        return 'HIGH'
    if score >= t['MEDIUM']:
        return 'MEDIUM'
    return 'LOW'


def generate_case_id() -> str:
    return f"CASE-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def generate_report_id() -> str:
    return f"RPT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"


def calculate_risk_score(detections: list, benchmark_results: list = None, inference_time_ms: float = 0) -> dict:
    """
    Calculate a 0-100 risk score from detection data.

    Returns a dict with:
      final_risk_score, risk_level, detection_score, anomaly_score,
      model_agreement_score, historical_score, avg_confidence, risk_factors
    """
    tw = RISK_CONFIG['threat_weights']
    risk_factors = []

    # ----------------------------------------------------------------
    # Component 1: Detection Score  (max contribution 40 pts)
    # ----------------------------------------------------------------
    detection_raw = 0.0
    if detections:
        total_weighted = 0.0
        for d in detections:
            cls = d.get('class', '')
            conf = d.get('confidence', 0) / 100.0     # normalise 0-1
            weight = tw.get(cls, tw['default'])
            total_weighted += conf * weight

        avg_weighted = total_weighted / len(detections)
        detection_raw = min(100.0, avg_weighted * 100)

        # Build factor strings
        high_threat = [d for d in detections if tw.get(d.get('class', ''), tw['default']) >= 0.85]
        if high_threat:
            risk_factors.append(
                f"High-severity object detected: {high_threat[0]['class']} "
                f"({high_threat[0]['confidence']}% confidence)"
            )
        else:
            risk_factors.append(
                f"Suspicious object detected: {detections[0]['class']} "
                f"({detections[0]['confidence']}% confidence)"
            )
    else:
        detection_raw = 0.0
        risk_factors.append('No suspicious objects detected by AI model')

    detection_score = detection_raw * RISK_CONFIG['weights']['detection']

    # ----------------------------------------------------------------
    # Component 2: Anomaly Count Score  (max contribution 30 pts)
    # ----------------------------------------------------------------
    n = len(detections)
    anomaly_raw = min(100.0, n * 15.0)   # 15 pts per detection, max 100
    anomaly_score = anomaly_raw * RISK_CONFIG['weights']['anomaly']
    if n > 1:
        risk_factors.append(f'Multiple potential anomalies detected ({n} items require review)')

    # ----------------------------------------------------------------
    # Component 3: Model Agreement Score  (max contribution 20 pts)
    # ----------------------------------------------------------------
    agreement_raw = 0.0
    if benchmark_results and len(benchmark_results) >= 2:
        models_with_detections = sum(1 for r in benchmark_results if r.get('objects', 0) > 0)
        agreement_raw = (models_with_detections / len(benchmark_results)) * 100
        if models_with_detections >= 2:
            risk_factors.append(
                f'Multiple AI models confirmed potential anomaly '                f'({models_with_detections}/{len(benchmark_results)} models in agreement)'
            )
    agreement_score = agreement_raw * RISK_CONFIG['weights']['model_agreement']

    # ----------------------------------------------------------------
    # Component 4: Historical Score  (reserved — always 0 for now)
    # ----------------------------------------------------------------
    historical_score = 0.0

    # ----------------------------------------------------------------
    # Final
    # ----------------------------------------------------------------
    raw_total = detection_score + anomaly_score + agreement_score + historical_score
    final_score = min(100.0, round(raw_total, 1))
    risk_level = get_risk_level(final_score)

    if not risk_factors:
        risk_factors = ['Scan completed — no anomalies detected']

    avg_conf = (
        round(sum(d.get('confidence', 0) for d in detections) / len(detections), 2)
        if detections else 0
    )

    return {
        'final_risk_score': final_score,
        'risk_level': risk_level,
        'detection_score': round(detection_score, 2),
        'anomaly_score': round(anomaly_score, 2),
        'model_agreement_score': round(agreement_score, 2),
        'historical_score': round(historical_score, 2),
        'avg_confidence': avg_conf,
        'risk_factors': risk_factors,
    }
