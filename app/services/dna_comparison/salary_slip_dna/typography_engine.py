import re

def analyze_number_formatting(ocr_text):
    """
    Layer 4: Number Format Micro Typography (OCR-based)
    Checks consistency in Indian vs Western comma placement, zero styles, and currency symbols.
    """
    issues = []
    score = 0
    
    # 1. Comma Style Consistency
    # Indian: 1,00,000. Western: 100,000.
    indian_comma_pattern = re.compile(r'\d{1,2}(?:,\d{2})+(?:,\d{3})')
    western_comma_pattern = re.compile(r'\b\d{1,3}(?:,\d{3})+\b')
    
    has_indian = bool(indian_comma_pattern.search(ocr_text))
    # We must be careful not to flag 1,000 as western if it's the only one, 
    # but 100,000 vs 1,00,000 is a direct conflict.
    has_strict_western = bool(re.search(r'\b\d{3},\d{3}\b', ocr_text))
    
    if has_indian and has_strict_western:
        score += 25
        issues.append("Inconsistent comma formatting: Mix of Indian (1,00,000) and Western (100,000) styles found.")
        
    # 2. Zero Representation Consistency
    has_nil = bool(re.search(r'\b(?:Nil|NIL|nil)\b', ocr_text))
    has_zero_dec = bool(re.search(r'\b0\.00\b', ocr_text))
    has_dash = bool(re.search(r'\b-\b', ocr_text)) # Need to be careful with hyphens
    
    # Count how many different styles of "zero" are used for empty fields
    zero_styles = sum([1 for x in [has_nil, has_zero_dec] if x])
    if zero_styles > 1:
        score += 15
        issues.append("Inconsistent zero representation: Mix of 'Nil' and '0.00' found.")
        
    # 3. Currency Symbol Consistency
    has_rupee_symbol = "₹" in ocr_text
    has_rs = bool(re.search(r'\bRs\.?\b', ocr_text, re.IGNORECASE))
    has_inr = bool(re.search(r'\bINR\b', ocr_text, re.IGNORECASE))
    
    currency_styles = sum([1 for x in [has_rupee_symbol, has_rs, has_inr] if x])
    if currency_styles > 1:
        score += 10
        issues.append("Inconsistent currency symbols: Mix of ₹, Rs., or INR found.")
        
    return {
        "typography_score": score,
        "typography_issues": issues
    }
