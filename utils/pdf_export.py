import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import base64
from PIL import Image
import io

def export_to_pdf(data, filename_prefix="report"):
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
    os.makedirs(reports_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{filename_prefix}_{timestamp}.pdf"
    filepath = os.path.join(reports_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    
    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Cargo Inspection Report")
    
    # Meta data
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 80, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(50, height - 100, f"Officer Name: {data.get('officer_name', 'Unknown')}")
    c.drawString(50, height - 120, f"Filename: {data.get('filename', 'Unknown')}")
    c.drawString(50, height - 140, f"Selected Model: {data.get('model', 'Unknown')}")
    
    metrics = data.get('metrics', {})
    c.drawString(50, height - 160, f"Objects Detected: {len(data.get('detections', []))}")
    c.drawString(50, height - 180, f"Average Confidence: {metrics.get('avg_confidence', '0')}%")
    c.drawString(50, height - 200, f"Processing Time: {metrics.get('processing_time_ms', '0')} ms")
    c.drawString(50, height - 220, f"Inference Time: {metrics.get('inference_time_ms', '0')} ms")
    c.drawString(50, height - 240, f"Risk Level: {data.get('risk_score', '0')}%")
    
    # Table of objects
    y_pos = height - 280
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "Objects Detected:")
    y_pos -= 20
    
    c.setFont("Helvetica", 11)
    for det in data.get('detections', []):
        c.drawString(70, y_pos, f"- {det['class']} (Confidence: {det['confidence']}%)")
        y_pos -= 15
        if y_pos < 300: # Create new page if running out of space before image
            c.showPage()
            c.setFont("Helvetica", 11)
            y_pos = height - 50
            
    # Draw image if provided (base64)
    image_b64 = data.get('image_b64')
    if image_b64:
        try:
            if image_b64.startswith('data:image'):
                image_b64 = image_b64.split(',')[1]
            img_data = base64.b64decode(image_b64)
            img = Image.open(io.BytesIO(img_data))
            
            # Save temporarily to draw on canvas
            temp_img_path = os.path.join(reports_dir, f"temp_{timestamp}.jpg")
            img.save(temp_img_path, format="JPEG")
            
            if y_pos < 250:
                c.showPage()
                y_pos = height - 50
                
            c.drawImage(temp_img_path, 50, y_pos - 250, width=400, height=225, preserveAspectRatio=True)
            os.remove(temp_img_path)
        except Exception as e:
            c.drawString(50, y_pos - 20, f"Error rendering image: {e}")
            
    c.save()
    return filepath
