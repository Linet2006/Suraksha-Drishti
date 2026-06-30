import logging
from typing import Dict, Any
from app.services.dna_comparison.property_dna.forensics import process_property_verification

logger = logging.getLogger(__name__)

def run_property_dna_analysis(file_path: str, is_pdf: bool, extracted_metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Standardized orchestrator for Property DNA analysis (Karnataka focus).
    """
    logger.info("Starting Property DNA Analysis...")
    try:
        raw_result = process_property_verification(image_path=file_path)
        
        flags = raw_result.get("flags", [])
        risk_score = raw_result.get("fraud_score", 0)
        
        differences = []
        for f in flags:
            differences.append(str(f))
                
        if risk_score >= 80:
            bucket = 3
            status = "Forged"
            description = "Critical anomalies detected in Property document."
        elif risk_score >= 20:
            bucket = 2
            status = "Requires Review"
            description = "Suspicious elements found. Manual review recommended."
        else:
            bucket = 1
            status = "Verified"
            description = "Property document passed registry and DNA forensics."
            
        return {
            "bucket": bucket,
            "status": status,
            "description": description,
            "differences": differences,
            "data": raw_result.get("data", {})
        }
    except Exception as e:
        logger.error(f"Property DNA Error: {e}")
        return {
            "bucket": 3,
            "status": "Error",
            "description": "Failed to complete Property DNA analysis.",
            "differences": [str(e)]
        }
