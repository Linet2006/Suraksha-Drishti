import numpy as np

def split_salary_check(credits_this_month, expected_net):
    """
    Checks if one or multiple salary credits exactly equal the expected net salary.
    """
    if len(credits_this_month) == 0:
        return False, 0
        
    total = sum(c["amount"] for c in credits_this_month)
    # Give a small tolerance of Rs 5 for rounding differences
    if abs(total - expected_net) <= 5:
        return True, total
    return False, total

def temporal_pattern_check(credits_last_3_months):
    """
    Checks if salary credits arrive consistently on the same day.
    """
    if len(credits_last_3_months) < 2:
        return "INSUFFICIENT_HISTORY", 0
        
    # Extract which day of month each credit arrived
    credit_days = [c["date"].day for c in credits_last_3_months]
    day_std = np.std(credit_days)
    
    # Real salary credits arrive within ±2 days of same date each month
    if day_std > 3:
        return "IRREGULAR_CREDIT_PATTERN", 15  # fraud score
    return "CONSISTENT_PATTERN", 0

def run_cross_verification(extracted_data, mock_aa_data=None):
    """
    Layer 6: Account Aggregator Cross-Verification
    """
    issues = []
    score = 0
    
    if not mock_aa_data:
        # If no AA data is provided, return neutral
        return {"cross_verify_score": None, "cross_verify_issues": []}
        
    expected_net = extracted_data.get("net_pay", 0)
    
    credits_this_month = mock_aa_data.get("credits_this_month", [])
    credits_last_3_months = mock_aa_data.get("credits_last_3_months", [])
    
    # 1. Exact Match Check (Split or Single)
    match, total_credited = split_salary_check(credits_this_month, expected_net)
    if not match:
        score += 60
        issues.append(f"Bank credit ({total_credited}) does NOT exactly match Salary Slip Net Pay ({expected_net}). Critical Mismatch.")
        
    # 2. Temporal Check
    temporal_status, temporal_score = temporal_pattern_check(credits_last_3_months)
    if temporal_status == "IRREGULAR_CREDIT_PATTERN":
        score += temporal_score
        issues.append("Salary credit dates are highly irregular across the last 3 months.")
        
    return {
        "cross_verify_score": score,
        "cross_verify_issues": issues
    }
