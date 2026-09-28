import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'database.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'Customs Officer',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')
    
    # Model Benchmarks table (for Phase 4 & Analytics)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_benchmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            filename TEXT,
            model TEXT,
            objects INTEGER,
            avg_confidence REAL,
            inference_time REAL,
            fps REAL,
            precision REAL,
            recall REAL,
            map50 REAL,
            map5095 REAL,
            memory_usage REAL,
            device TEXT
        )
    ''')
    
    # Risk Assessments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS risk_assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            operator_id INTEGER,
            filename TEXT,
            model TEXT,
            detections TEXT,
            avg_confidence REAL DEFAULT 0,
            num_detections INTEGER DEFAULT 0,
            detection_score REAL DEFAULT 0,
            anomaly_score REAL DEFAULT 0,
            model_agreement_score REAL DEFAULT 0,
            historical_score REAL DEFAULT 0,
            final_risk_score REAL DEFAULT 0,
            risk_level TEXT DEFAULT 'LOW',
            risk_factors TEXT,
            inspection_status TEXT DEFAULT 'PENDING',
            inference_time_ms REAL,
            FOREIGN KEY (operator_id) REFERENCES users(id)
        )
    ''')

    # Incident Reports table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS incident_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id TEXT UNIQUE NOT NULL,
            case_id TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            generated_by INTEGER,
            trigger_reason TEXT,
            risk_score REAL,
            risk_level TEXT,
            pdf_path TEXT,
            status TEXT DEFAULT 'GENERATED',
            FOREIGN KEY (case_id) REFERENCES risk_assessments(case_id),
            FOREIGN KEY (generated_by) REFERENCES users(id)
        )
    ''')

    # Insert default admin if not exists
    cursor.execute('SELECT * FROM users WHERE email = ?', ('admin@cargosight.com',))
    admin = cursor.fetchone()
    if not admin:
        cursor.execute(
            'INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)',
            ('System Admin', 'admin@cargosight.com', generate_password_hash('admin123'), 'Admin')
        )

    conn.commit()
    conn.close()

def authenticate_user(email, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    conn.close()
    
    if user and check_password_hash(user['password_hash'], password):
        return dict(user)
    return None

def create_user(name, email, password, role='Customs Officer'):
    conn = get_db_connection()
    try:
        conn.execute(
            'INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)',
            (name, email, generate_password_hash(password), role)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_last_login(user_id):
    conn = get_db_connection()
    conn.execute('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now(), user_id))
    conn.commit()
    conn.close()
    
def get_user_by_id(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return dict(user) if user else None


# =====================================================================
# Risk Assessment helpers
# =====================================================================

def save_risk_assessment(data: dict) -> bool:
    """Persist a risk assessment record."""
    import json
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO risk_assessments
            (case_id, operator_id, filename, model, detections, avg_confidence,
             num_detections, detection_score, anomaly_score, model_agreement_score,
             historical_score, final_risk_score, risk_level, risk_factors,
             inspection_status, inference_time_ms)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            data.get('case_id'), data.get('operator_id'), data.get('filename'),
            data.get('model'), json.dumps(data.get('detections', [])),
            data.get('avg_confidence', 0), data.get('num_detections', 0),
            data.get('detection_score', 0), data.get('anomaly_score', 0),
            data.get('model_agreement_score', 0), data.get('historical_score', 0),
            data.get('final_risk_score', 0), data.get('risk_level', 'LOW'),
            json.dumps(data.get('risk_factors', [])),
            data.get('inspection_status', 'PENDING'),
            data.get('inference_time_ms', 0)
        ))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_risk_assessments(limit=100, risk_level=None):
    import json
    conn = get_db_connection()
    q = 'SELECT * FROM risk_assessments'
    params = []
    if risk_level:
        q += ' WHERE risk_level = ?'
        params.append(risk_level)
    q += ' ORDER BY scan_date DESC LIMIT ?'
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        try: d['detections'] = json.loads(d.get('detections') or '[]')
        except: d['detections'] = []
        try: d['risk_factors'] = json.loads(d.get('risk_factors') or '[]')
        except: d['risk_factors'] = []
        result.append(d)
    return result


def get_risk_assessment_by_case(case_id: str):
    import json
    conn = get_db_connection()
    row = conn.execute('SELECT * FROM risk_assessments WHERE case_id = ?', (case_id,)).fetchone()
    conn.close()
    if not row: return None
    d = dict(row)
    try: d['detections'] = json.loads(d.get('detections') or '[]')
    except: d['detections'] = []
    try: d['risk_factors'] = json.loads(d.get('risk_factors') or '[]')
    except: d['risk_factors'] = []
    return d


def update_inspection_status(case_id: str, status: str):
    conn = get_db_connection()
    conn.execute('UPDATE risk_assessments SET inspection_status = ? WHERE case_id = ?', (status, case_id))
    conn.commit()
    conn.close()


# =====================================================================
# Incident Report helpers
# =====================================================================

def save_incident_report(data: dict) -> bool:
    conn = get_db_connection()
    try:
        conn.execute('''
            INSERT INTO incident_reports
            (report_id, case_id, generated_by, trigger_reason, risk_score, risk_level, pdf_path, status)
            VALUES (?,?,?,?,?,?,?,?)
        ''', (
            data.get('report_id'), data.get('case_id'), data.get('generated_by'),
            data.get('trigger_reason'), data.get('risk_score'), data.get('risk_level'),
            data.get('pdf_path'), data.get('status', 'GENERATED')
        ))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def get_incident_reports(limit=100):
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM incident_reports ORDER BY generated_at DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# =====================================================================
# Analytics helpers
# =====================================================================

def get_analytics_overview():
    import json
    from collections import Counter
    conn = get_db_connection()

    total = conn.execute('SELECT COUNT(*) as c FROM risk_assessments').fetchone()['c']
    dist = conn.execute('''
        SELECT risk_level, COUNT(*) as c FROM risk_assessments GROUP BY risk_level
    ''').fetchall()
    avg_score = conn.execute('SELECT AVG(final_risk_score) as a FROM risk_assessments').fetchone()['a'] or 0

    # Risk distribution
    risk_dist = {'LOW': 0, 'MEDIUM': 0, 'HIGH': 0, 'CRITICAL': 0}
    for row in dist:
        risk_dist[row['risk_level']] = row['c']

    # Last 7 days trend
    trend = conn.execute('''
        SELECT DATE(scan_date) as d, COUNT(*) as total,
               SUM(CASE WHEN risk_level IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END) as high_risk
        FROM risk_assessments
        WHERE scan_date >= DATE('now', '-7 days')
        GROUP BY DATE(scan_date) ORDER BY d DESC
    ''').fetchall()

    # Top detected classes
    all_dets = conn.execute('SELECT detections FROM risk_assessments WHERE detections IS NOT NULL').fetchall()
    class_counter = Counter()
    for row in all_dets:
        try:
            dets = json.loads(row['detections'])
            for d in dets:
                class_counter[d.get('class', 'Unknown')] += 1
        except: pass

    conn.close()
    return {
        'total_assessments': total,
        'risk_distribution': risk_dist,
        'avg_risk_score': round(avg_score, 1),
        'recent_trend': [dict(r) for r in trend],
        'top_detected_classes': class_counter.most_common(5)
    }


def get_trend_data(days=30):
    conn = get_db_connection()
    rows = conn.execute('''
        SELECT DATE(scan_date) as date,
               COUNT(*) as total_inspections,
               SUM(CASE WHEN risk_level IN ('HIGH','CRITICAL') THEN 1 ELSE 0 END) as high_risk_count,
               ROUND(AVG(final_risk_score), 1) as avg_risk_score
        FROM risk_assessments
        WHERE scan_date >= DATE('now', ? || ' days')
        GROUP BY DATE(scan_date)
        ORDER BY date ASC
    ''', (f'-{days}',)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
