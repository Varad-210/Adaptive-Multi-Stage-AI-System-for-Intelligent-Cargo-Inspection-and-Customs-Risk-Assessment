from flask import Blueprint, render_template, request, jsonify
from auth.decorators import login_required
from utils.benchmark import run_benchmark
from auth.models import get_db_connection

comparison_bp = Blueprint('comparison', __name__)

@comparison_bp.route('/model-comparison', methods=['GET', 'POST'])
@login_required
def compare():
    if request.method == 'GET':
        return render_template('comparison.html')

@comparison_bp.route('/api/compare', methods=['POST'])
@login_required
def api_compare():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400
        
    file = request.files['image']
    img_bytes = file.read()
    
    # Run benchmark
    results = run_benchmark(img_bytes, file.filename)
    
    return jsonify({"results": results})

@comparison_bp.route('/history', methods=['GET'])
@login_required
def history():
    conn = get_db_connection()
    benchmarks = conn.execute('SELECT * FROM model_benchmarks ORDER BY date DESC').fetchall()
    conn.close()
    return render_template('history.html', benchmarks=[dict(b) for b in benchmarks])
