import re
import cv2
from datetime import datetime
import os
from app.services.dna_comparison.salary_slip_dna.ocr_engine import get_easyocr_reader
from app.services.dna_comparison.salary_slip_dna.image_forensics import run_image_forensics

def extract_fields_from_document(image_path):
    image_cv = cv2.imread(image_path)
    if image_cv is None:
        raise ValueError(f"Could not load image at {image_path}")
    
    # Preprocessing for better OCR
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    
    reader = get_easyocr_reader()
    results = reader.readtext(resized, detail=1)
    
    clean_results = [r for r in results if r[2] > 0.2]
    raw_text = " \n ".join([r[1] for r in clean_results])

    # Karnataka Kaveri 2.0 Document No (e.g. BGN-1-01234-2023-24)
    doc_num_match = re.search(r'([A-Z]{3}-\d+-\d{4,5}-\d{4}-\d{2})', raw_text)
    doc_number = doc_num_match.group(1) if doc_num_match else "UNKNOWN"

    # E-Stamp Number (IN-KA...)
    estamp_match = re.search(r'(IN-KA[A-Z0-9]{14})', raw_text)
    estamp_number = estamp_match.group(1) if estamp_match else "UNKNOWN"
    
    def find_date(pattern):
        m = re.search(pattern, raw_text, re.IGNORECASE)
        return m.group(1).strip() if m else "UNKNOWN"
        
    execution_date_raw = find_date(r'Execution\s*Date\s*[:\-]?\s*([\d]{1,2}[-/][A-Za-z0-9]{2,9}[-/][\d]{2,4})')
    registration_date_raw = find_date(r'Registration\s*Date\s*[:\-]?\s*([\d]{1,2}[-/][A-Za-z0-9]{2,9}[-/][\d]{2,4})')
    
    return {
        "raw_text": raw_text,
        "document_number": doc_number,
        "estamp_number": estamp_number,
        "execution_date_raw": execution_date_raw,
        "registration_date_raw": registration_date_raw
    }

def parse_date(date_str):
    if date_str == "UNKNOWN" or not date_str: return None
    formats = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d-%m-%y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None

def process_property_verification(image_path):
    flags = []
    fraud_score = 0
    
    # 1. Image Forensics (ELA)
    try:
        forensics_result = run_image_forensics(image_path, output_dir="data/outputs/property")
        if forensics_result.get("forensics_score", 0) > 0:
            fraud_score += forensics_result["forensics_score"]
            for issue in forensics_result.get("forensics_issues", []):
                flags.append(f"Forensics: {issue}")
    except Exception as e:
        flags.append(f"Image Forensics failed: {str(e)}")
        fraud_score += 20
        
    # 2. Extract Data
    try:
        data = extract_fields_from_document(image_path)
    except Exception as e:
        return {"fraud_score": 100, "flags": [f"Failed to read document: {str(e)}"], "data": {}}
        
    # 3. Validation Logic
    if data["document_number"] == "UNKNOWN":
        flags.append("Missing or unreadable Karnataka Kaveri 2.0 Document Number.")
        fraud_score += 30
        
    if data["estamp_number"] == "UNKNOWN":
        flags.append("Missing or unreadable E-Stamp Certificate Number.")
        fraud_score += 40
        
    # 4. Temporal Check
    exec_date = parse_date(data["execution_date_raw"])
    reg_date = parse_date(data["registration_date_raw"])
    
    if exec_date and reg_date:
        if exec_date > reg_date:
            flags.append(f"Temporal Anomaly: Execution Date ({exec_date.strftime('%Y-%m-%d')}) is AFTER Registration Date ({reg_date.strftime('%Y-%m-%d')}).")
            fraud_score += 50
    elif data["execution_date_raw"] == "UNKNOWN" or data["registration_date_raw"] == "UNKNOWN":
        flags.append("Missing crucial dates (Execution or Registration).")
        fraud_score += 20

    return {
        "fraud_score": fraud_score,
        "flags": flags,
        "data": data
    }
