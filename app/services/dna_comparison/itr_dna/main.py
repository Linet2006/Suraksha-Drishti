import logging
from typing import Dict, Any
from .forensics import verify_math_dna, verify_metadata_and_visuals, verify_registry_consistency

logger = logging.getLogger(__name__)

def run_itr_dna_analysis(file_path: str, is_pdf: bool, metadata: Dict[str, Any]) -> dict:
    """
    Orchestrates the three layers of verification for ITR / Form 16 documents.
    Returns a dictionary conforming to the strict Output Specification.
    """
    total_score = 0
    all_differences = []

    try:
        # Layer 1: Mathematical DNA Engine
        math_score, math_issues = verify_math_dna(metadata)
        total_score += math_score
        all_differences.extend(math_issues)

        # Layer 2: Metadata & Visual Structure Forensics
        meta_score, meta_issues = verify_metadata_and_visuals(file_path, is_pdf)
        total_score += meta_score
        all_differences.extend(meta_issues)

        # Layer 3: Government Registry Cross-Consistency Check
        registry_score, registry_issues = verify_registry_consistency(metadata)
        total_score += registry_score
        all_differences.extend(registry_issues)
        
    except Exception as e:
        logger.error(f"Critical error in ITR DNA Analysis: {e}")
        total_score = 100
        all_differences.append(f"System Error during analysis: {str(e)}")

    # Decision Routing Thresholds
    # Bucket 1 (0-30 Score): Auto-Approve
    # Bucket 2 (31-65 Score): Human Review
    # Bucket 3 (66-100+ Score): Auto-Reject

    if total_score <= 30:
        bucket = 1
        status = "Verified"
        description = "Document appears authentic and mathematically sound. No significant anomalies detected."
    elif total_score <= 65:
        bucket = 2
        status = "Requires Review"
        description = "Anomalies flagged during forensic checks. Human review is required to verify the highlighted issues."
    else:
        bucket = 3
        status = "Forged"
        description = "Severe mismatches or evidence of forgery detected (e.g., unauthorized editing tools, mathematical impossibility). Document is likely fraudulent."

    return {
        "bucket": bucket,
        "status": status,
        "differences": all_differences,
        "description": description
    }
