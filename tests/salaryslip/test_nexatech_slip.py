import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import sys
import os
import json

# Fix for printing unicode characters on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure Python can find our package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.dna_comparison.salary_slip_dna.main import process_verification

# Extracted exactly from your image
nexatech_slip = {
    "raw_text": "NEXATECH SOLUTIONS PRIVATE LIMITED SALARY SLIP MAY 2026 Employee ID: NXT-EMP-20214",
    "company_name": "NEXATECH SOLUTIONS PRIVATE LIMITED",
    "city": "Bengaluru",
    "extracted_data": {
        "basic": 45000,
        "hra": 18000,
        "pf": 5400,
        "pt": 200,
        "esic": 662,  # Notice this! ESI shouldn't apply if Gross > 21k
        "tds": 3500,
        "gross_pay": 80950,
        "total_deductions": 9762,
        "net_pay": 71188
    }
}

if __name__ == "__main__":
    print(f"\nProcessing Nexatech Slip from Chat Image...\n")
    
    result = process_verification(nexatech_slip, is_image=False)
    
    print("="*50)
    print(f"DECISION: {result['routing']['decision']} (Score: {result['routing']['score']})")
    print("="*50)
    
    if result['explainability']['issues']:
        print("ISSUES FOUND:")
        for issue in result['explainability']['issues']:
            print(f" - {issue}")
    else:
        print("ISSUES: None (Clean Document)")
