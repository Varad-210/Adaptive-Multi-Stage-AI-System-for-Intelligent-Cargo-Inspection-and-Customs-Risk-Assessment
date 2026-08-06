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
