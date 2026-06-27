import re
from datetime import datetime
from .restructuring_calendar import get_tolerance_band

def classify_entity_type(company_name):
    """
    Classifies the company type to apply appropriate structural rules.
    """
    name_lower = company_name.lower()
    
    if any(kw in name_lower for kw in ["pvt", "private", "llp"]):
        return "PVT_LTD"
    elif "ltd" in name_lower or "limited" in name_lower:
        return "LTD"
    elif any(kw in name_lower for kw in ["govt", "government", "ministry", "department", "bank"]):
        return "GOVT_PSU"
    elif any(kw in name_lower for kw in ["army", "navy", "air force", "defence"]):
        return "DEFENCE"
    else:
        return "UNKNOWN"

def verify_hra_ratio(basic, hra, city, entity_type, slip_date):
    """
    Verifies HRA is within 40% (non-metro) or 50% (metro) of basic.
    Applies dynamic tolerances based on entity type and restructuring calendar.
    """
    if basic == 0:
        return "NO_BASIC", 0, 0
        
    metro_cities = ["mumbai", "delhi", "bengaluru", "chennai", "kolkata", "hyderabad"]
    is_metro = any(metro in city.lower() for metro in metro_cities)
    
    expected_ratio = 0.50 if is_metro else 0.40
    actual_ratio = hra / basic
    
    # Get dynamic tolerance based on restructuring calendar
    # We map our entity_types to the calendar keys broadly
    calendar_key = "all"
    if entity_type == "LTD": calendar_key = "MNC"
    elif entity_type == "GOVT_PSU": calendar_key = "PSU"
    
    tolerance = get_tolerance_band(calendar_key, slip_date)
    
    # Startups/Pvt Ltd might have completely unoptimized structures, allow massive tolerance
    if entity_type == "PVT_LTD":
        tolerance = 0.25 # Allow 25% drift for small startups
        
    lower_bound = expected_ratio - tolerance
    upper_bound = expected_ratio + tolerance
    
    if actual_ratio < lower_bound or actual_ratio > upper_bound:
        return "HRA_RATIO_VIOLATION", expected_ratio, actual_ratio
        
    return "HRA_OK", expected_ratio, actual_ratio

def verify_logo_hash(image_path, expected_company):
    """
    Mock function to represent the 'UV Light' logo hashing.
    In a real system, this would extract the ROI of the logo,
    compute a pHash, and compare to a database of known authentic hashes.
    """
    # For hackathon prototype, we assume the logo hash matches unless it's a known 'fake generator' hash
    fake_generator_hashes = ["0xdeadbeef", "0xbadc0de"]
    extracted_hash = "0xgenuine123" # Mock extraction
    
    if extracted_hash in fake_generator_hashes:
        return False, "Logo hash matches known fake PDF generator template."
    return True, "Logo hash is authentic."

def run_structure_analysis(extracted_data, company_name, city, image_path):
    issues = []
    score = 0
    
    entity_type = classify_entity_type(company_name)
    
    if entity_type == "GOVT_PSU" and extracted_data.get("hra", 0) > 0 and extracted_data.get("da", 0) == 0:
        score += 30
        issues.append("Government/PSU entity but has HRA instead of DA. Possible template mismatch.")
        
    slip_date = extracted_data.get("slip_date", datetime.now().date())
    basic = extracted_data.get("basic", 0)
    hra = extracted_data.get("hra", 0)
    
    hra_status, exp_ratio, act_ratio = verify_hra_ratio(basic, hra, city, entity_type, slip_date)
    if hra_status == "HRA_RATIO_VIOLATION":
        score += 25
        issues.append(f"HRA ratio ({act_ratio:.2f}) violates expected {exp_ratio:.2f} bounds for {entity_type} in {city}.")
        
    logo_valid, logo_msg = verify_logo_hash(image_path, company_name)
    if not logo_valid:
        score += 50
        issues.append(logo_msg)
        
    return {
        "structure_score": score,
        "structure_issues": issues,
        "entity_type": entity_type
    }
