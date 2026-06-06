from .ocr_engine import extract_data_from_image
from .scraper import run_sync_verification
from .utils import create_audit_log, generate_heatmap
import os

def process_verification(input_data, is_image=True, project_root="Suraksha-Drishti", show_heatmap=False):
    """
    Main entry point for the Verification Agent.
    Accepts either an image path or a direct file number.
    Returns a strict JSON-compatible dictionary.
    """
    extracted_data = {}
    image_cv = None
    ocr_data = None
    
    if is_image:
        try:
            extraction_result = extract_data_from_image(input_data)
            extracted_data = extraction_result["extracted_data"]
            image_cv = extraction_result["image_cv"]
            ocr_data = extraction_result["ocr_data"]
            ack_number = extracted_data.get("ack_number")
        except Exception as e:
            return {"status": "error", "message": str(e)}
    else:
        # Manual entry mode
        ack_number = str(input_data)
        extracted_data = {"ack_number": ack_number}
        
    risk_score = 0
    issues = []
    
    if not ack_number:
        risk_score += 100
        issues.append("Critical: No Acknowledgment Number found in document.")
        api_record = None
    else:
        pan = extracted_data.get("pan", "ABCDE1234F")
        api_record = run_sync_verification(pan, ack_number)
        
    if api_record and api_record.get("status") == "error":
        risk_score += 100
        issues.append(api_record.get("message", "Record NOT FOUND in Government DB."))
    elif api_record and api_record.get("status") == "success" and is_image:
        income = extracted_data.get("income")
        pan = extracted_data.get("pan")
        name = extracted_data.get("name")
        
        govt_income = api_record.get("govt_income")
        
        # Tamper Cross-Check (Mathematical Validation)
        if income is not None and govt_income is not None:
            try:
                # Basic string parsing to int for mathematical check
                income_val = int(str(income).replace(",", "").strip())
                govt_income_val = int(str(govt_income).replace(",", "").strip())
                if income_val != govt_income_val:
                    risk_score += 50
                    issues.append(f"Income Mismatch! Doc: {income}, Govt: {govt_income}")
            except ValueError:
                issues.append("Could not parse income mathematically.")
                
        # In a real scenario we'd also check name and PAN from the portal
        # For now, we trust the govt verification of the PAN/ACK combination


    # Bucket Routing
    if risk_score <= 30: 
        bucket = "Bucket 1"
        decision = "Auto-Approve"
    elif risk_score <= 65: 
        bucket = "Bucket 2"
        decision = "Human Review Required"
    else: 
        bucket = "Bucket 3"
        decision = "Auto-Reject"
        
    # Explainability & Heatmap
    heatmap_path = None
    if issues and is_image and image_cv is not None:
        heatmap_dir = os.path.join(project_root, "data", "heatmaps")
        heatmap_path = generate_heatmap(image_cv, ocr_data, issues, extracted_data, output_dir=heatmap_dir)
        
        if show_heatmap:
            import cv2
            import matplotlib.pyplot as plt
            # Convert BGR to RGB for matplotlib
            img_rgb = cv2.cvtColor(cv2.imread(heatmap_path), cv2.COLOR_BGR2RGB)
            plt.figure(figsize=(10, 5))
            plt.imshow(img_rgb)
            plt.title(f"Fraud Heatmap: {decision}")
            plt.axis("off")
            plt.show()
        
    # Audit Trail
    audit_data = {
        "input_data": input_data,
        "is_image": is_image,
        "extracted_data": extracted_data,
        "risk_score": risk_score,
        "decision": decision,
        "issues": issues
    }
    audit_dir = os.path.join(project_root, "data", "secure_audit_logs")
    audit_hash = create_audit_log(audit_data, log_dir=audit_dir)
    
    # Construct final output strictly matching specs
    output = {
        "routing": {
            "score": risk_score,
            "bucket": bucket,
            "decision": decision
        },
        "explainability": {
            "issues": issues,
            "heatmap_path": heatmap_path,
            "audit_trail_hash": audit_hash
        },
        "extracted_data": extracted_data
    }
    
    return output
