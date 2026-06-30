import re

def classify_employment_type(ocr_text):
    """
    Identifies if the slip belongs to a regular employee or a consultant.
    """
    consultant_keywords = [
        "consultant", "retainer", "contract", "freelance", 
        "professional fees", "consultancy fees"
    ]
    
    ocr_lower = ocr_text.lower()
    for kw in consultant_keywords:
        if kw in ocr_lower:
            return "CONSULTANT"
    
    return "REGULAR"

def tds_corridor(annual_gross):
    """
    Returns valid monthly minimum and maximum TDS based on annualized gross.
    Assumes standard exemptions to create the corridor.
    """
    # Minimum TDS assuming maximum 80C (₹1.5L) + HRA + 80D
    min_tds_annual = max(0, (annual_gross - 700000) * 0.05)
    # Maximum TDS assuming zero deductions declared
    max_tds_annual = max(0, (annual_gross - 300000) * 0.05)
    return min_tds_annual / 12, max_tds_annual / 12

def check_statutory_invariants(extracted_data, employment_type, state="Karnataka"):
    """
    Runs L2 Statutory math rules.
    """
    issues = []
    score = 0
    
    basic = extracted_data.get("basic", 0)
    pf = extracted_data.get("pf", 0)
    pt = extracted_data.get("pt", 0)
    esic = extracted_data.get("esic", 0)
    tds = extracted_data.get("tds", 0)
    gross = extracted_data.get("gross_pay", 0)
    
    annual_gross = gross * 12
    
    # CRITICAL VETO: If the Gross Pay is missing or zero, the document is fundamentally invalid.
    # This catches completely blurry images or completely fake AI generations that don't have real financial tables.
    if gross <= 0:
        score += 100
        issues.append("CRITICAL VETO: Gross Pay could not be extracted or is zero. Invalid Salary Slip format.")
    
    if employment_type == "CONSULTANT":
        # Consultants shouldn't have PF/PT/ESIC in standard formats
        if pf > 0 or pt > 0 or esic > 0:
            score += 40
            issues.append(f"Consultant profile but has PF/PT/ESIC deductions (PF: {pf}, PT: {pt}, ESIC: {esic}).")
        # TDS for consultants is usually a flat 10% under 194J, but we'll stick to a simpler rule
        if tds == 0 and annual_gross > 300000:
            score += 20
            issues.append("Consultant missing TDS deduction (194J expected).")
            
    elif employment_type == "REGULAR":
        # PF Check (12% of basic, capped or uncapped)
        expected_pf_uncapped = basic * 0.12
        expected_pf_capped = min(basic, 15000) * 0.12
        
        if pf == 0 and basic > 0:
            score += 30
            issues.append("Missing PF deduction for regular employee.")
        elif pf > 0 and abs(pf - expected_pf_uncapped) > 5 and abs(pf - expected_pf_capped) > 5:
            # Could be VPF, requires cohort or historical check, flag lightly
            score += 15
            issues.append(f"PF ({pf}) does not strictly match 12% of basic ({expected_pf_uncapped}) or 12% of cap ({expected_pf_capped}). Possible VPF.")

        # PT Check (State aware)
        if state == "Karnataka":
            expected_pt = 200 if gross > 15000 else 0
            if pt != expected_pt:
                score += 20
                issues.append(f"PT ({pt}) does not match Karnataka state rule ({expected_pt}).")
                
        # ESIC Check
        if gross > 21000 and esic > 0:
            score += 50
            issues.append(f"ESIC charged ({esic}) but gross ({gross}) is above ₹21,000 threshold. Statutory violation.")
            
        # TDS Check
        if gross > 0:
            min_tds, max_tds = tds_corridor(annual_gross)
            # Widen the corridor slightly for monthly variations
            min_tds_adjusted = max(0, min_tds - 500)
            max_tds_adjusted = max_tds + 1000
            
            if tds < min_tds_adjusted or tds > max_tds_adjusted:
                score += 20
                issues.append(f"TDS ({tds}) falls outside the expected monthly corridor ({min_tds_adjusted:.0f} - {max_tds_adjusted:.0f}).")
                
    return {
        "statutory_score": score,
        "statutory_issues": issues
    }
