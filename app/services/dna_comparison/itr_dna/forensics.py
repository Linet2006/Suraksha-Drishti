import re
import logging
from pypdf import PdfReader
import cv2
import numpy as np

logger = logging.getLogger(__name__)

FORBIDDEN_TOOLS = ["ilovepdf", "canva", "photoshop", "smallpdf", "adobe acrobat premium mobile"]

def verify_math_dna(metadata: dict) -> tuple[int, list[str]]:
    """
    Mathematical DNA Engine: Verify Form 16 Part B Logic.
    Returns: (fraud_score_modifier, list_of_issues)
    """
    score = 0
    issues = []
    
    try:
        gross_salary = float(metadata.get("gross_salary", 0))
        exemptions = float(metadata.get("section_10_exemptions", 0))
        standard_deduction = float(metadata.get("standard_deduction", 50000))
        chapter_vi_a = float(metadata.get("chapter_vi_a_deductions", 0))
        
        reported_tax = float(metadata.get("total_tax_payable", 0))
        
        # Calculate expected values
        expected_net_salary = gross_salary - exemptions
        expected_taxable_income = expected_net_salary - standard_deduction - chapter_vi_a
        
        if expected_taxable_income < 0:
            expected_taxable_income = 0
            
        # Simplified New Regime Tax Calculation (AY 2024-25)
        computed_tax = 0
        income = expected_taxable_income
        
        if income > 1500000:
            computed_tax += (income - 1500000) * 0.30
            income = 1500000
        if income > 1200000:
            computed_tax += (income - 1200000) * 0.20
            income = 1200000
        if income > 900000:
            computed_tax += (income - 900000) * 0.15
            income = 900000
        if income > 600000:
            computed_tax += (income - 600000) * 0.10
            income = 600000
        if income > 300000:
            computed_tax += (income - 300000) * 0.05
            
        # Section 87A Rebate for New Regime (income up to 7L gets full rebate)
        if expected_taxable_income <= 700000:
            computed_tax = 0
            
        # Add 4% Health & Education Cess
        if computed_tax > 0:
            computed_tax += computed_tax * 0.04
            
        # Tolerance of Rs. 10 for rounding errors
        if abs(computed_tax - reported_tax) > 10:
            score += 50
            issues.append(f"Math DNA Mismatch: Computed tax (₹{computed_tax:.2f}) does not match reported tax (₹{reported_tax:.2f}).")
            
    except ValueError as e:
        score += 50
        issues.append(f"Math DNA Error: Could not parse financial fields correctly. ({e})")
        
    return score, issues

def verify_metadata_and_visuals(file_path: str, is_pdf: bool) -> tuple[int, list[str]]:
    """
    Metadata & Visual Structure Forensics.
    Returns: (fraud_score_modifier, list_of_issues)
    """
    score = 0
    issues = []
    
    if is_pdf:
        try:
            reader = PdfReader(file_path)
            metadata = reader.metadata
            if metadata:
                producer = str(metadata.get('/Producer', '')).lower()
                creator = str(metadata.get('/Creator', '')).lower()
                
                for tool in FORBIDDEN_TOOLS:
                    if tool in producer or tool in creator:
                        score += 70
                        issues.append(f"Metadata Alert: PDF generated or modified using unauthorized tool '{tool}'.")
                        break
        except Exception as e:
            logger.error(f"Error reading PDF metadata: {e}")
            issues.append("Metadata Alert: Could not parse PDF metadata structure.")
            
    else:
        # Visual DNA for Images
        try:
            img = cv2.imread(file_path)
            if img is not None:
                # Mock Error Level Analysis (ELA) / Visual checking
                # In a real scenario, this would apply complex CV techniques
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                if laplacian_var < 50:
                    score += 20
                    issues.append("Visual DNA: Image is unusually blurry, potentially concealing alterations.")
                
                # Mock check for font consistency / patching (simulate for demonstration)
                # We assume image noise variance across patches
                # (A very naive check just to have a visual structural check implemented)
                h, w = gray.shape
                if h > 100 and w > 100:
                    patch1 = gray[0:50, 0:50]
                    patch2 = gray[h-50:h, w-50:w]
                    if abs(patch1.var() - patch2.var()) > 1000:
                        score += 30
                        issues.append("Visual DNA: Anomalous noise pattern detected. Possible image patching/insertion.")
            else:
                score += 30
                issues.append("Visual DNA: Could not load image for visual analysis.")
        except Exception as e:
            logger.error(f"Error in visual analysis: {e}")
            issues.append(f"Visual DNA Error: {str(e)}")
            
    return score, issues

def verify_registry_consistency(metadata: dict) -> tuple[int, list[str]]:
    """
    Government Registry Cross-Consistency Check.
    Returns: (fraud_score_modifier, list_of_issues)
    """
    score = 0
    issues = []
    
    pan = metadata.get("pan", "").upper()
    if not pan:
        score += 40
        issues.append("Registry Alert: PAN is missing from payload.")
    else:
        # Check PAN format: 5 Letters, 4 Digits, 1 Letter
        if not re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$", pan):
            score += 40
            issues.append(f"Registry Alert: PAN '{pan}' fails syntax validation.")
        else:
            # Check 4th character status code (P=Individual, C=Company, etc.)
            status_char = pan[3]
            expected_status = metadata.get("expected_pan_status", "P")
            if status_char != expected_status:
                score += 40
                issues.append(f"Registry Alert: PAN status character '{status_char}' does not match expected '{expected_status}'.")
                
    tan = metadata.get("tan", "").upper()
    if tan:
        if not re.match(r"^[A-Z]{4}[0-9]{5}[A-Z]{1}$", tan):
            score += 20
            issues.append(f"Registry Alert: Employer TAN '{tan}' fails syntax validation.")
            
    return score, issues
