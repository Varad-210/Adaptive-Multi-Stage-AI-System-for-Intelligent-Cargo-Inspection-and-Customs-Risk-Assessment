import json
import os
from datetime import datetime

def export_to_json(data, filename_prefix="report"):
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.json"
    filepath = os.path.join(reports_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)
        
    return filepath
