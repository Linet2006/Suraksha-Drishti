from .image_forensics import run_image_forensics
from .ocr_engine import extract_data_from_image
from .statutory_engine import check_statutory_invariants, classify_employment_type
from .structure_engine import run_structure_analysis
from .typography_engine import analyze_number_formatting
from .cohort_engine import run_cohort_analysis
from .cross_verification import run_cross_verification

LAYER_WEIGHTS = {
    "image_forensics":   0.20,  # L1
    "statutory":         0.25,  # L2 — highest weight, law-based
    "structure":         0.15,  # L3
    "typography":        0.10,  # L4
    "cohort":            0.20,  # L5
    "cross_verify":      0.10   # L6
}

NEUTRAL_SCORE = 50  # when a layer can't run, contribute neutral

def process_verification(input_data, mock_aa_data=None, is_image=True):
    """
    Main entry point for Salary Slip DNA Engine (6 Layers)
    """
    all_issues = []
    layer_scores = {}
    extracted_data = {}
    ocr_raw_text = ""
    company_name = "Unknown"
    city = "Bengaluru" # Mocked or extracted in real scenario
    
    # --- LAYER 1: Image Forensics & OCR ---
    if is_image:
        forensics_res = run_image_forensics(input_data)
        layer_scores["image_forensics"] = forensics_res.get("forensics_score", 0)
        all_issues.extend(forensics_res.get("forensics_issues", []))
        
        # In a real scenario we'd skip OCR if forensics fails badly, but we continue for demo
        try:
            extraction_result = extract_data_from_image(input_data)
            extracted_data = extraction_result["extracted_data"]
            # We need raw text for typography check
            # For hackathon, just stringify the data values if we don't have raw text handy
            # But ocr_engine could be modified to return raw text. Let's mock it for now
            # if our ocr_engine doesn't return raw_text
            ocr_raw_text = " ".join([str(v) for v in extracted_data.values()])
            company_name = extracted_data.get("name", "TCS") # Mocking extraction of company name
        except Exception as e:
            all_issues.append(f"OCR Extraction failed: {str(e)}")
            layer_scores["image_forensics"] = 100 # Max score for failure
    else:
        # API direct input mode
        extracted_data = input_data.get("extracted_data", input_data)
        ocr_raw_text = input_data.get("raw_text", "")
        company_name = input_data.get("company_name", "TCS")
        city = input_data.get("city", "Bengaluru")
        layer_scores["image_forensics"] = NEUTRAL_SCORE
        
    # --- LAYER 2: Statutory Engine ---
    employment_type = classify_employment_type(ocr_raw_text)
    stat_res = check_statutory_invariants(extracted_data, employment_type)
    layer_scores["statutory"] = stat_res.get("statutory_score", 0)
    all_issues.extend(stat_res.get("statutory_issues", []))
    
    # --- LAYER 3: Structure Engine ---
    struct_res = run_structure_analysis(extracted_data, company_name, city, input_data if is_image else "dummy_path")
    layer_scores["structure"] = struct_res.get("structure_score", 0)
    all_issues.extend(struct_res.get("structure_issues", []))
    
    # --- LAYER 4: Typography Engine ---
    if ocr_raw_text:
        typo_res = analyze_number_formatting(ocr_raw_text)
        layer_scores["typography"] = typo_res.get("typography_score", 0)
        all_issues.extend(typo_res.get("typography_issues", []))
    else:
        layer_scores["typography"] = NEUTRAL_SCORE
        
    # --- LAYER 5: Cohort Engine ---
    cohort_res = run_cohort_analysis(extracted_data, company_name)
    layer_scores["cohort"] = cohort_res.get("cohort_score", 0)
    all_issues.extend(cohort_res.get("cohort_issues", []))
    
    # --- LAYER 6: Cross Verification ---
    cross_res = run_cross_verification(extracted_data, mock_aa_data)
    cross_score = cross_res.get("cross_verify_score")
    if cross_score is not None:
        layer_scores["cross_verify"] = cross_score
        all_issues.extend(cross_res.get("cross_verify_issues", []))
    else:
        layer_scores["cross_verify"] = NEUTRAL_SCORE

    from .explainability_overlay import generate_overlay

    # --- FINAL SCORING ---
    final_score = sum(
        layer_scores.get(k, NEUTRAL_SCORE) * w 
        for k, w in LAYER_WEIGHTS.items()
    )
    
    # Check for Critical Veto (if any layer flagged a 100-point maximum penalty)
    has_critical_veto = any(score >= 100 for score in layer_scores.values())
    
    if has_critical_veto:
        bucket = "Bucket 3"
        decision = "AUTO_REJECT (CRITICAL VETO)"
    elif final_score <= 30:
        bucket = "Bucket 1"
        decision = "AUTO_APPROVE"
    elif final_score <= 65:
        bucket = "Bucket 2"
        decision = "HUMAN_REVIEW"
    else:
        bucket = "Bucket 3"
        decision = "AUTO_REJECT"

    # --- AUTOMATED EXPLAINABILITY OVERLAY ---
    highlighted_image_path = None
    if is_image and all_issues:
        highlighted_image_path = generate_overlay(input_data, all_issues)

    return {
        "routing": {
            "score": round(final_score, 2),
            "bucket": bucket,
            "decision": decision
        },
        "layer_breakdown": layer_scores,
        "explainability": {
            "issues": all_issues,
            "highlighted_image_path": highlighted_image_path
        },
        "extracted_data": extracted_data,
        "metadata": {
            "employment_type": employment_type,
            "company_name": company_name
        }
    }
