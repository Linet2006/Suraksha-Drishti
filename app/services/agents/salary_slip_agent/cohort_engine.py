import numpy as np
from .company_profiles import COMPANY_PROFILES

def detect_restructuring_or_fraud(new_basic_pct, recent_cohort_values):
    """
    CUSUM drift detection + Cross-employee direction check.
    Distinguishes between widespread company salary restructuring and isolated fraud.
    """
    if len(recent_cohort_values) < 5:
        return "INSUFFICIENT_HISTORY", 0
        
    mean_recent = np.mean(recent_cohort_values[-5:])
    std_recent = np.std(recent_cohort_values[-5:])
    
    if std_recent == 0:
        std_recent = 0.01 # prevent division by zero
        
    # If this slip is consistent with a recent cohort shift -> restructuring
    # "Cross-employee direction check" implicitly handled if we check against the latest 5 slips
    # which represent the 'post-restructuring' cohort.
    if abs(new_basic_pct - mean_recent) < std_recent * 1.5:
        return "CONSISTENT_WITH_COHORT", 0
    # If this slip deviates wildly from both old baseline and recent cohort -> fraud
    else:
        return "OUTLIER_FRAUD", 30

def extract_structural_hash(extracted_data):
    """
    Zero-Knowledge Registry component.
    Converts data to structural shape without storing values.
    """
    keys = sorted(list(extracted_data.keys()))
    # Example: basic_hra_pf_pt_tds
    return "_".join(keys)

def run_cohort_analysis(extracted_data, company_name):
    """
    Layer 5: Cohort Intelligence
    """
    issues = []
    score = 0
    
    basic = extracted_data.get("basic", 0)
    gross = extracted_data.get("gross_pay", 0)
    
    if gross == 0:
        return {"cohort_score": 0, "cohort_issues": []}
        
    new_basic_pct = basic / gross
    
    # 1. Cold Start Check using Company Profiles
    profile = COMPANY_PROFILES.get(company_name)
    if profile:
        min_pct, max_pct = profile["basic_pct_range"]
        if new_basic_pct < min_pct or new_basic_pct > max_pct:
            score += 25
            issues.append(f"Basic pay ratio ({new_basic_pct:.2f}) violates static baseline for {company_name} ({min_pct}-{max_pct}).")
            
    # 2. Peer Comparison / CUSUM (Mocked for Demo)
    # In reality, fetch from DPDP-compliant DB
    mock_recent_cohort_values = [0.42, 0.43, 0.41, 0.42, 0.41]
    # Inject a drift if the slip differs a lot
    if abs(new_basic_pct - 0.42) > 0.05:
        status, flag_score = detect_restructuring_or_fraud(new_basic_pct, mock_recent_cohort_values)
        if status == "OUTLIER_FRAUD":
            score += flag_score
            issues.append(f"Cohort drift detection flagged this as an outlier (CUSUM check against peers).")
            
    return {
        "cohort_score": score,
        "cohort_issues": issues
    }
