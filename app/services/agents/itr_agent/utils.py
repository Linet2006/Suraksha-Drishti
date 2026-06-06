import hashlib
import json
import cv2
from datetime import datetime
import os

def create_audit_log(transaction_data, log_dir="data/secure_audit_logs"):
    os.makedirs(log_dir, exist_ok=True)
    
    transaction_string = json.dumps(transaction_data, sort_keys=True)
    secure_hash = hashlib.sha256(transaction_string.encode()).hexdigest()
    
    audit_entry = {
        "hash_id": secure_hash,
        "data": transaction_data
    }
    
    log_file = os.path.join(log_dir, "audit_log.json")
    with open(log_file, "a") as f:
        f.write(json.dumps(audit_entry) + "\n")
        
    return secure_hash

def generate_heatmap(image_cv, ocr_data, issues, extracted_data, output_dir="data/heatmaps"):
    os.makedirs(output_dir, exist_ok=True)
    image_display = image_cv.copy()
    words_to_highlight = []
    
    ack_number = extracted_data.get("ack_number")
    income = extracted_data.get("income")
    pan = extracted_data.get("pan")
    name = extracted_data.get("name")
    
    if any("Acknowledgment" in issue for issue in issues) or any("NOT FOUND" in issue for issue in issues):
        words_to_highlight.append(str(ack_number) if ack_number else "Acknowledgment")
        
    if any("Income Mismatch" in issue for issue in issues):
        words_to_highlight.append(str(income) if income else "Gross")
        
    if any("PAN Mismatch" in issue for issue in issues):
        words_to_highlight.append(str(pan) if pan else "PAN")
        
    if any("Name Mismatch" in issue for issue in issues):
        first_name = name.split()[0] if name else "Name"
        words_to_highlight.append(str(first_name))
        
    for target in words_to_highlight:
        for i in range(len(ocr_data['text'])):
            if target and target in ocr_data['text'][i] and len(target) > 2:
                x, y, w, h = ocr_data['left'][i], ocr_data['top'][i], ocr_data['width'][i], ocr_data['height'][i]
                cv2.rectangle(image_display, (x-5, y-5), (x+w+5, y+h+5), (0, 0, 255), 3)
                cv2.putText(image_display, "FLAGGED", (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
    
    filename = f"heatmap_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    filepath = os.path.join(output_dir, filename)
    cv2.imwrite(filepath, image_display)
    
    return os.path.abspath(filepath)
