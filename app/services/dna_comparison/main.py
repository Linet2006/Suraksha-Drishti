import os
from .aadhaar_dna import run_aadhaar_verification
from .pan_dna import run_pan_verification
from .kyc_ocr_mock import extract_aadhaar_data, extract_pan_data

def run_aadhaar_pan_cross_verification(aadhaar_result: dict, pan_result: dict) -> dict:
    flags = []
    risk_score = 0
    
    # Cross check 1: Name on Aadhaar QR vs Name on PAN
    aadhaar_name = aadhaar_result.get("qr_data", {}).get("name", "")
    pan_surname_initial = pan_result.get("pan_number", "XXXXX")[4] if pan_result.get("pan_number") else None
    
    if aadhaar_name and pan_surname_initial:
        name_parts = aadhaar_name.strip().upper().split()
        last_initial = name_parts[-1][0] if name_parts else ""
        first_initial = name_parts[0][0] if name_parts else ""
        
        if pan_surname_initial not in [last_initial, first_initial]:
            flags.append({
                "flag": "AADHAAR_PAN_NAME_MISMATCH",
                "severity": "CRITICAL",
                "description": "PAN surname initial does not match Aadhaar name",
                "aadhaar_name": aadhaar_name,
                "pan_initial": pan_surname_initial
            })
            risk_score += 35
    
    # Cross check 2: Both must belong to same person
    aadhaar_verified = aadhaar_result.get("verified", False)
    pan_verified = pan_result.get("verified", False)
    
    if not aadhaar_verified and not pan_verified:
        flags.append({
            "flag": "BOTH_ID_PROOFS_FAILED",
            "severity": "CRITICAL",
            "description": "Both Aadhaar and PAN verification failed — strong identity fraud signal",
        })
        risk_score += 50
    
    # Cross check 3: Individual risk scores
    combined_risk = (
        aadhaar_result.get("risk_score", 0) * 0.6 +
        pan_result.get("risk_score", 0) * 0.4
    )
    
    total_risk = min(100, combined_risk + risk_score)
    
    return {
        "identity_verified": total_risk < 30,
        "combined_risk_score": round(total_risk, 2),
        "aadhaar_risk": aadhaar_result.get("risk_score", 0),
        "pan_risk": pan_result.get("risk_score", 0),
        "cross_flags": flags,
        "all_flags": (
            aadhaar_result.get("flags", []) +
            pan_result.get("flags", []) +
            flags
        ),
        "decision": (
            "IDENTITY_CONFIRMED" if total_risk < 30 else
            "IDENTITY_UNCERTAIN" if total_risk < 60 else
            "IDENTITY_FRAUD_DETECTED"
        )
    }

import fitz

def ensure_image_format(filepath: str) -> str:
    if not filepath or not os.path.exists(filepath):
        return filepath
        
    lower_path = filepath.lower()
    
    # Convert PDF to Image
    if lower_path.endswith(".pdf"):
        try:
            import fitz
            doc = fitz.open(filepath)
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                new_path = filepath.replace(".pdf", "") + "_page0.jpg"
                pix.save(new_path)
                return new_path
        except Exception as e:
            print(f"PDF Conversion Error: {e}")
            
    # Guarantee OpenCV compatibility by re-saving the image using Pillow
    # This prevents errors if a user manually renames an .avif to .jpg
    try:
        from PIL import Image
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass
            
        img = Image.open(filepath)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        # Always save a fresh JPEG version
        base, _ = os.path.splitext(filepath)
        new_path = base + "_safe.jpg"
        img.save(new_path, "JPEG", quality=100)
        return new_path
    except Exception as e:
        print(f"Image Conversion Error: {e}")
            
    return filepath

def process_kyc_verification(aadhaar_path: str = None, pan_path: str = None, selfie_path: str = None):
    """
    Main Orchestrator for KYC verification.
    Takes image paths, runs mock OCR, passes to specific DNA engines, 
    and cross-verifies them.
    """
    results = {}
    
    # Transparently convert PDFs to Images before processing
    aadhaar_path = ensure_image_format(aadhaar_path)
    pan_path = ensure_image_format(pan_path)
    
    # 1. Process Aadhaar if provided
    aadhaar_result = {"verified": False, "risk_score": 100}
    if aadhaar_path and os.path.exists(aadhaar_path):
        ocr_data = extract_aadhaar_data(aadhaar_path)
        aadhaar_result = run_aadhaar_verification(aadhaar_path, selfie_path, ocr_data)
        results["aadhaar_engine"] = aadhaar_result
        
    # 2. Process PAN if provided
    pan_result = {"verified": False, "risk_score": 100}
    if pan_path and os.path.exists(pan_path):
        ocr_data = extract_pan_data(pan_path)
        pan_result = run_pan_verification(pan_path, ocr_data, aadhaar_result.get("qr_data", {}).get("name", ""), {})
        results["pan_engine"] = pan_result
        
    # 3. Cross Verification (If both provided)
    if aadhaar_path and pan_path:
        cross_result = run_aadhaar_pan_cross_verification(aadhaar_result, pan_result)
        results["cross_verification"] = cross_result
        
    return results
