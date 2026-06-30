import re
import os
import cv2
from app.services.dna_comparison.salary_slip_dna.image_forensics import error_level_analysis

# ==========================================
# LAYER 1: FORMAT AND STRUCTURE VALIDATION
# ==========================================
def validate_pan_format(pan: str) -> dict:
    if not pan:
        return {
            "valid": False,
            "flag": "EXTRACTION_FAILED",
            "severity": "HIGH",
            "description": "Could not extract PAN from image."
        }
        
    pan = pan.strip().upper()
    
    # Basic format: 5 letters + 4 digits + 1 letter
    pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]{1}$'
    
    if not re.match(pattern, pan):
        return {
            "valid": False,
            "flag": "PAN_FORMAT_INVALID",
            "severity": "CRITICAL",
            "description": f"PAN {pan} does not match format AAAAA0000A"
        }
    
    VALID_TAXPAYER_TYPES = {
        'P': 'Individual Person', 'C': 'Company', 'H': 'Hindu Undivided Family',
        'F': 'Firm', 'A': 'Association of Persons', 'B': 'Body of Individuals',
        'G': 'Government', 'J': 'Artificial Juridical Person', 'L': 'Local Authority',
        'T': 'Trust'
    }
    
    taxpayer_code = pan[3]
    if taxpayer_code not in VALID_TAXPAYER_TYPES:
        return {
            "valid": False,
            "flag": "PAN_TAXPAYER_CODE_INVALID",
            "severity": "CRITICAL",
            "description": f"4th character '{taxpayer_code}' is not a valid taxpayer type"
        }
    
    taxpayer_type = VALID_TAXPAYER_TYPES[taxpayer_code]
    
    if taxpayer_code != 'P':
        return {
            "valid": False,
            "flag": "PAN_NOT_INDIVIDUAL",
            "severity": "HIGH",
            "description": f"PAN belongs to {taxpayer_type}, not an individual person",
            "taxpayer_type": taxpayer_type
        }
    
    return {
        "valid": True,
        "pan": pan,
        "taxpayer_type": taxpayer_type,
        "surname_initial": pan[4],
        "sequence": pan[5:9]
    }

# ==========================================
# LAYER 2: SURNAME INITIAL CROSS CHECK WITH AADHAAR
# ==========================================
def verify_pan_surname_match(pan: str, full_name_from_aadhaar: str) -> dict:
    pan = pan.strip().upper()
    pan_surname_initial = pan[4]
    
    name_parts = full_name_from_aadhaar.strip().upper().split()
    if not name_parts:
        return {"match": False, "flag": "NAME_EXTRACTION_FAILED", "severity": "MEDIUM"}
    
    last_name_initial = name_parts[-1][0]
    first_name_initial = name_parts[0][0]
    
    if pan_surname_initial == last_name_initial:
        return {"match": True, "matched_on": "last_name", "pan_initial": pan_surname_initial, "name_initial": last_name_initial}
    elif pan_surname_initial == first_name_initial:
        return {"match": True, "matched_on": "first_name", "pan_initial": pan_surname_initial, "name_initial": first_name_initial, "note": "Matched on first name"}
    else:
        return {
            "match": False,
            "flag": "PAN_SURNAME_MISMATCH",
            "severity": "HIGH",
            "pan_initial": pan_surname_initial,
            "aadhaar_name": full_name_from_aadhaar,
            "description": f"PAN 5th character '{pan_surname_initial}' does not match any name initial from Aadhaar"
        }

# ==========================================
# LAYER 3: PAN CONSISTENCY ACROSS ALL DOCUMENTS
# ==========================================
def verify_pan_consistency(documents: dict) -> dict:
    pan_values = {}
    flags = []
    pan_sources = ["salary_slip", "form16", "itr", "bank_statement", "pan_card"]
    
    for source in pan_sources:
        if documents.get(source, {}).get("pan"):
            raw_pan = documents[source]["pan"].strip().upper()
            clean_pan = re.sub(r'[^A-Z0-9]', '', raw_pan)
            pan_values[source] = clean_pan
            
    unique_pans = set(pan_values.values())
    
    if len(unique_pans) > 1:
        flags.append({
            "flag": "PAN_INCONSISTENCY",
            "severity": "CRITICAL",
            "description": "Different PAN numbers found across documents",
            "details": pan_values
        })
    if len(unique_pans) == 0:
        flags.append({
            "flag": "PAN_NOT_FOUND",
            "severity": "HIGH",
            "description": "PAN number could not be extracted from any document"
        })
    
    return {
        "consistent": len(flags) == 0,
        "pan_found": list(unique_pans)[0] if unique_pans else None,
        "pan_across_documents": pan_values,
        "flags": flags,
        "risk_contribution": 40 if flags else 0
    }

# ==========================================
# LAYER 4: PAN CARD IMAGE FORENSICS
# ==========================================
def verify_pan_card_image(pan_card_image_path: str) -> dict:
    from app.services.dna_comparison.salary_slip_dna.image_forensics import run_image_forensics
    
    forensics = run_image_forensics(pan_card_image_path, output_dir="data/outputs/kyc")
    flags = []
    
    if forensics["forensics_score"] > 0:
        for issue in forensics["forensics_issues"]:
            flags.append({
                "flag": "FORENSICS_WARNING",
                "severity": "CRITICAL" if "tampering" in issue.lower() else "HIGH",
                "description": issue
            })
            
    return {
        "ela_clean": len(flags) == 0,
        "zone_flags": flags,
        "risk_contribution": forensics["forensics_score"],
        "detailed_forensics": forensics
    }

# ==========================================
# COMPLETE PAN VERIFICATION RUNNER
# ==========================================
def run_pan_verification(pan_card_image_path: str, ocr_extracted: dict, aadhaar_qr_name: str, all_documents: dict) -> dict:
    flags = []
    risk_score = 0
    results = {}
    
    # Layer 0: Image Forensics (ELA)
    if pan_card_image_path and os.path.exists(pan_card_image_path):
        image_check = verify_pan_card_image(pan_card_image_path)
        results["image_forensics"] = image_check
        if not image_check["ela_clean"]:
            flags.extend(image_check["zone_flags"])
            risk_score += image_check["risk_contribution"]
            
    # Layer 1: PAN number (extracted by Gemini in orchestrator)
    pan_number = ocr_extracted.get("pan_number", "").strip().upper() if ocr_extracted.get("pan_number") else ""
            
    format_check = validate_pan_format(pan_number if pan_number else None)
    results["format"] = format_check
    if not format_check["valid"]:
        flags.append(format_check)
        risk_score += 50
    
    # Layer 2
    if aadhaar_qr_name:
        surname_check = verify_pan_surname_match(pan_number, aadhaar_qr_name)
        results["surname_match"] = surname_check
        if not surname_check["match"]:
            flags.append(surname_check)
            risk_score += 30
            
    # Layer 3 (only if other documents provided for cross-referencing)
    if all_documents:
        consistency_check = verify_pan_consistency(all_documents)
        results["consistency"] = consistency_check
        if not consistency_check["consistent"]:
            flags.extend(consistency_check["flags"])
            risk_score += consistency_check["risk_contribution"]
        
    return {
        "verified": risk_score < 50,
        "pan_number": pan_number,
        "taxpayer_type": format_check.get("taxpayer_type"),
        "risk_score": min(100, risk_score),
        "flags": flags,
        "detailed_results": results
    }
