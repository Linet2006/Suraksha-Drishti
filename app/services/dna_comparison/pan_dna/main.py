import logging
from typing import Dict, Any
from app.services.dna_comparison.pan_dna.forensics import run_pan_verification

logger = logging.getLogger(__name__)

def run_pan_dna_analysis(file_path: str, is_pdf: bool, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("Starting PAN DNA Analysis...")
    try:
        # We might not have all_documents or aadhaar_qr_name in the unified orchestrator yet.
        # We pass empty dicts/strings for now.
        raw_result = run_pan_verification(
            pan_card_image_path=file_path if not is_pdf else None,
            ocr_extracted={"pan_number": extracted_metadata.get("pan_number", extracted_metadata.get("pan", ""))},
            aadhaar_qr_name="", 
            all_documents={}
        )
        
        flags = raw_result.get("flags", [])
        risk_score = raw_result.get("risk_score", 0)
        
        differences = []
        for f in flags:
            if isinstance(f, dict):
                desc = f.get("description", f.get("flag", str(f)))
                differences.append(desc)
            else:
                differences.append(str(f))
                
        if risk_score >= 80:
            bucket = 3
            status = "Forged"
            description = "Critical anomalies detected in PAN document."
        elif risk_score >= 20:
            bucket = 2
            status = "Requires Review"
            description = "Suspicious elements found. Manual review recommended."
        else:
            bucket = 1
            status = "Verified"
            description = "PAN document passed DNA forensics successfully."
            
        return {
            "bucket": bucket,
            "status": status,
            "description": description,
            "differences": differences,
            "data": raw_result.get("detailed_results", {})
        }
    except Exception as e:
        logger.error(f"PAN DNA Error: {e}")
        return {
            "bucket": 3,
            "status": "Error",
            "description": "Failed to complete PAN DNA analysis.",
            "differences": [str(e)]
        }
