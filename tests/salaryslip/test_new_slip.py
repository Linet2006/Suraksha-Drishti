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

from app.services.agents.salary_slip_agent.main import process_verification

new_slip_data = {
    "raw_text": "NEXORA TECHNOLOGIES PVT. LTD. SALARY SLIP May 2026 This is a computer-generated salary slip and does not require a physical signature.",
    "company_name": "NEXORA TECHNOLOGIES PVT. LTD.",
    "city": "Mumbai",
    "extracted_data": {
        "basic": 30000,
        "hra": 12000,
        "pf": 1800,
        "pt": 200,
        "esic": 0,
        "tds": 1500,
        "gross_pay": 50000,
        "total_deductions": 3500,
        "net_pay": 46500
    }
}

if __name__ == "__main__":
    print(f"\nProcessing Nexora Slip from Chat Image...\n")
    # For now, pass is_image=False to use our mock OCR, 
    # but we will also run test_real_photo on it for the L1 visual forensics.
    result = process_verification(new_slip_data, is_image=False)
    
    print("="*50)
    print(f"DECISION: {result['routing']['decision']} (Score: {result['routing']['score']})")
    print("="*50)
    
    if result['explainability']['issues']:
        print("ISSUES FOUND:")
        for issue in result['explainability']['issues']:
            print(f" - {issue}")
    else:
        print("ISSUES: None (Clean Document)")
