from .ocr_engine import extract_data_from_image
from .mock_api import verify_with_government_api
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
        api_record = verify_with_government_api(ack_number)
        
    if not api_record and ack_number:
        risk_score += 100
        issues.append("Record NOT FOUND in Government DB.")
    elif api_record and is_image:
        income = extracted_data.get("income")
        pan = extracted_data.get("pan")
        name = extracted_data.get("name")
        
        if income is not None and income != api_record.get("gross_income"):
            risk_score += 50
            issues.append(f"Income Mismatch! Doc: {income}, Govt: {api_record.get('gross_income')}")
            
        if pan is not None and pan != api_record.get("pan_number"):
            risk_score += 40
            issues.append(f"PAN Mismatch! Doc: {pan}, Govt: {api_record.get('pan_number')}")
            
        api_name = api_record.get("name", "")
        if name and name.lower() != api_name.lower():
            risk_score += 30
            issues.append(f"Name Mismatch! Doc: {name}, Govt: {api_name}")

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
