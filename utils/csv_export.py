import csv
import os
from datetime import datetime

def export_to_csv(data, filename_prefix="report"):
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.csv"
    filepath = os.path.join(reports_dir, filename)
    
    # data is expected to contain: filename, detections (list of dicts), metrics
    detections = data.get('detections', [])
    metrics = data.get('metrics', {})
    
    with open(filepath, mode='w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Filename', 'Class', 'Confidence', 'Inference Time (ms)', 'Processing Time (ms)'])
        
        orig_filename = data.get('filename', 'Unknown')
        inf_time = metrics.get('inference_time_ms', 'N/A')
        proc_time = metrics.get('processing_time_ms', 'N/A')
        
        for det in detections:
            writer.writerow([
                orig_filename,
                det.get('class', 'Unknown'),
                det.get('confidence', 0),
                inf_time,
                proc_time
            ])
            
    return filepath
