import sqlite3
import re
import cv2
from datetime import datetime
import os

# Use the globally cached EasyOCR reader from the salary slip agent to save memory
from app.services.agents.salary_slip_agent.ocr_engine import get_easyocr_reader

# ---------- 1. OCR extraction from the applicant's document image ----------

def extract_fields_from_document(image_path):
    image_cv = cv2.imread(image_path)
    if image_cv is None:
        raise ValueError(f"Could not load image at {image_path}")

    # Preprocessing
    gray = cv2.cvtColor(image_cv, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    
    # Run EasyOCR
    reader = get_easyocr_reader()
    results = reader.readtext(resized, detail=1)
    
    # Filter and construct raw text
    clean_results = [r for r in results if r[2] > 0.2]
    raw_text = " \n ".join([r[1] for r in clean_results])

    def find(pattern, default="UNKNOWN"):
        m = re.search(pattern, raw_text, re.IGNORECASE)
        return m.group(1).strip() if m else default

    survey_number = find(r'(?:Survey|Sy\.?)\s*No\.?\s*[:\-]?\s*([A-Za-z0-9/\-]+)')
    owner_name = find(r'(?:Owner|Vendor|Applicant|Name)\s*[:\-]?\s*([A-Za-z .]+?)(?:\n|$)')
    doc_date_raw = find(r'Date(?:\s*of\s*(?:Execution|Registration))?\s*[:\-]?\s*([\d]{1,2}[-/][A-Za-z0-9]{2,9}[-/][\d]{2,4})')
    doc_number = find(r'(?:Document|Deed)\s*No\.?\s*[:\-]?\s*([A-Za-z0-9\-]+)')

    return {
        "raw_text": raw_text,
        "survey_number": survey_number,
        "owner_name": owner_name,
        "document_date_raw": doc_date_raw,
        "document_number": doc_number,
    }


# ---------- 2. Date normalization ----------

def parse_date(date_str):
    if date_str == "UNKNOWN" or not date_str: return None
    formats = ["%d-%b-%Y", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d-%m-%y"]
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


# ---------- 3. Registry lookup (offline, local SQLite) ----------

def lookup_registry(survey_number, db_path="data/registry.db"):
    if not os.path.exists(db_path):
        return None
        
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        SELECT survey_number, current_owner, last_transaction_type,
               last_transaction_date, document_number, status
        FROM property_records
        WHERE survey_number = ?
    """, (survey_number,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return {
            "survey_number": row[0],
            "current_owner": row[1],
            "last_transaction_type": row[2],
            "last_transaction_date": row[3],
            "document_number": row[4],
            "status": row[5],
        }
    return None


# ---------- 4. Core anomaly detection logic ----------

def detect_anomaly(applicant_data, registry_record):
    flags = []
    score = 0

    if registry_record is None:
        flags.append("Survey number not found in registry — cannot verify, manual check required")
        return {"fraud_score": 25, "risk": "MEDIUM", "flags": flags, "decision": "MANUAL_REVIEW"}

    applicant_date = parse_date(applicant_data["document_date_raw"])
    registry_date = None
    if registry_record["last_transaction_date"]:
        try:
            registry_date = datetime.strptime(registry_record["last_transaction_date"], "%Y-%m-%d")
        except:
            pass

    # Check A: property already transferred AFTER applicant's document date
    if applicant_date and registry_date:
        if registry_date > applicant_date:
            if registry_record["current_owner"].lower() != applicant_data["owner_name"].lower():
                score += 100 # CRITICAL VETO
                flags.append(
                    f"CRITICAL VETO: Registry shows property already transferred to "
                    f"'{registry_record['current_owner']}' on "
                    f"{registry_record['last_transaction_date']}, which is AFTER "
                    f"the applicant's document date ({applicant_data['document_date_raw']}). ALREADY SOLD FRAUD."
                )

    # Check B: applicant name doesn't match current registered owner at all
    if registry_record["current_owner"].lower() != applicant_data["owner_name"].lower():
        score += 30
        flags.append(
            f"Applicant name '{applicant_data['owner_name']}' does not match "
            f"current registered owner '{registry_record['current_owner']}'."
        )

    # Check C: property under encumbrance/dispute
    if registry_record["status"] != "ACTIVE":
        score += 60
        flags.append(f"Registry status flag: property marked as '{registry_record['status']}'. Possible undisclosed lien or dispute.")

    # Check D: document number mismatch
    if applicant_data["document_number"] != "UNKNOWN" and \
       applicant_data["document_number"] != registry_record["document_number"]:
        score += 15
        flags.append(
            f"Document number on applicant's paper ('{applicant_data['document_number']}') "
            f"does not match registry ('{registry_record['document_number']}')."
        )

    if not flags:
        flags.append("No anomalies detected — applicant matches current registry record.")

    risk = "HIGH (REJECT)" if score >= 80 else "MEDIUM (REVIEW)" if score >= 20 else "LOW (APPROVE)"
    
    decision = "AUTO_REJECT" if score >= 80 else "HUMAN_REVIEW" if score >= 20 else "AUTO_APPROVE"
    
    return {"fraud_score": score, "risk": risk, "flags": flags, "decision": decision}


# ---------- 5. Full pipeline ----------

def generate_property_overlay(image_path, flags, score):
    """
    Generates a bounding box / text overlay for Property Papers (Aadhaar/PAN style).
    """
    if not image_path or not os.path.exists(image_path):
        return None
        
    img = cv2.imread(image_path)
    if img is None:
        return None
        
    h, w, _ = img.shape
    
    if score >= 80:
        # Draw massive red border for Fraud
        cv2.rectangle(img, (10, 10), (w - 10, h - 10), (0, 0, 255), 10)
        
        # Draw Fraud Stamp
        text = "FRAUD DETECTED: PROPERTY ALREADY SOLD / TAMPERED"
        if any("encumbrance" in f.lower() or "dispute" in f.lower() for f in flags):
            text = "FRAUD DETECTED: ACTIVE MORTGAGE / ENCUMBRANCE"
            
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (w - 20, 80), (0, 0, 255), -1)
        cv2.putText(img, text, (30, 60), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
    elif score >= 20:
        # Draw yellow border for Review
        cv2.rectangle(img, (10, 10), (w - 10, h - 10), (0, 255, 255), 10)
        text = "WARNING: MANUAL REVIEW REQUIRED"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (w - 20, 80), (0, 255, 255), -1)
        cv2.putText(img, text, (30, 60), font, 0.8, (0, 0, 0), 2, cv2.LINE_AA)
    else:
        # Draw green border for Success
        cv2.rectangle(img, (10, 10), (w - 10, h - 10), (0, 200, 0), 10)
        text = "SUCCESS: TITLE VERIFIED (CLEAN)"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (w - 20, 80), (0, 200, 0), -1)
        cv2.putText(img, text, (30, 60), font, 0.8, (255, 255, 255), 2, cv2.LINE_AA)
        
    basename = os.path.basename(image_path)
    name_only, ext = os.path.splitext(basename)
    filename = f"proof_property_{name_only}_{int(datetime.now().timestamp())}.jpg"
    output_dir = os.path.abspath("data/outputs/property")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, filename)
    cv2.imwrite(output_path, img)
    return filename

def process_property_verification(image_path, db_path="data/registry.db"):
    from app.services.agents.salary_slip_agent.image_forensics import run_image_forensics
    
    # 1. Run Image Forensics to detect any digital edits/photoshop!
    try:
        forensics_result = run_image_forensics(image_path, output_dir="data/outputs/property")
    except Exception as e:
        forensics_result = {"forensics_score": 0, "forensics_issues": [f"Forensics Error: {str(e)}"]}
        
    # 2. Run OCR Extraction
    try:
        applicant_data = extract_fields_from_document(image_path)
    except Exception as e:
        return {"error": f"Failed to extract document data: {str(e)}"}
        
    # 3. Registry Lookup & Anomaly Detection
    registry_record = lookup_registry(applicant_data["survey_number"], db_path)
    result = detect_anomaly(applicant_data, registry_record)
    
    # Merge Forensics into the final result
    f_score = forensics_result.get("forensics_score", 0)
    f_issues = forensics_result.get("forensics_issues", [])
    
    final_score = min(100, result["fraud_score"] + f_score)
    all_flags = result["flags"] + f_issues
    
    if f_score >= 50:
        result["decision"] = "AUTO_REJECT"
        result["risk"] = "HIGH (FORGED)"
        
    # Generate Aadhaar/PAN style overlay
    overlay_filename = generate_property_overlay(image_path, all_flags, final_score)

    return {
        "routing": {
            "score": final_score,
            "decision": result["decision"],
            "risk_level": result["risk"]
        },
        "explainability": {
            "issues": all_flags,
            "Visual Proof": f"http://localhost:8000/outputs/property/{overlay_filename}" if overlay_filename else None
        },
        "extracted_data": applicant_data,
        "registry_record": registry_record if registry_record else {"status": "NOT FOUND"}
    }
