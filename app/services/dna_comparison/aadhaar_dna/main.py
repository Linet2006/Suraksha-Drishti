import logging
from typing import Dict, Any
from app.services.dna_comparison.aadhaar_dna.forensics import run_aadhaar_verification

logger = logging.getLogger(__name__)

def run_aadhaar_dna_analysis(file_path: str, is_pdf: bool, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardized orchestrator for Aadhaar DNA analysis.
    """
    logger.info("Starting Aadhaar DNA Analysis...")
    try:
        raw_result = run_aadhaar_verification(
            aadhaar_image_path=file_path if not is_pdf else None,  
            selfie_path=None, 
            ocr_extracted_fields=extracted_metadata, 
            itr_address=None
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
            description = "Critical anomalies detected in Aadhaar document."
        elif risk_score >= 20:
            bucket = 2
            status = "Requires Review"
            description = "Suspicious elements found. Manual review recommended."
        else:
            bucket = 1
            status = "Verified"
            description = "Aadhaar document passed DNA forensics successfully."
            
        return {
            "bucket": bucket,
            "status": status,
            "description": description,
            "differences": differences,
            "data": raw_result.get("detailed_results", {})
        }
    except Exception as e:
        logger.error(f"Aadhaar DNA Error: {e}")
        return {
            "bucket": 3,
            "status": "Error",
            "description": "Failed to complete Aadhaar DNA analysis.",
            "differences": [str(e)]
        }
