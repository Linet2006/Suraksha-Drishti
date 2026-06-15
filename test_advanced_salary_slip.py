import json
from datetime import date, datetime, timedelta
import cv2
import numpy as np
import os
import sys

# Fix for printing unicode characters like ₹ on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Ensure Python can find our package
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.agents.salary_slip_agent.main import process_verification

def run_test(name, input_data, mock_aa_data=None, is_image=False):
    print(f"\n{'='*50}\nTEST: {name}\n{'='*50}")
    result = process_verification(input_data, mock_aa_data=mock_aa_data, is_image=is_image)
    
    print(f"DECISION: {result['routing']['decision']} (Score: {result['routing']['score']})")
    if result['explainability']['issues']:
        print("ISSUES FOUND:")
        for issue in result['explainability']['issues']:
            print(f" - {issue}")
    else:
        print("ISSUES: None")
    return result

# ---------------------------------------------------------
# Test 1: Perfect genuine slip
# ---------------------------------------------------------
perfect_slip = {
    "raw_text": "Salary Slip Employee ID: EMP123 Name: John Doe",
    "company_name": "TCS",
    "city": "Bengaluru",
    "extracted_data": {
        "basic": 40000,
        "hra": 20000,
        "special_allowance": 40000,
        "pf": 1800,  # 12% of capped 15k
        "pt": 200,
        "esic": 0,
        "tds": 5000,
        "gross_pay": 100000,
        "net_pay": 93000,
        "slip_date": date(2024, 6, 1)
    }
}
perfect_aa = {
    "credits_this_month": [{"amount": 93000, "date": date(2024, 6, 1)}],
    "credits_last_3_months": [
        {"amount": 93000, "date": date(2024, 5, 1)},
        {"amount": 93000, "date": date(2024, 4, 1)}
    ]
}
run_test("1. Perfect genuine slip", perfect_slip, perfect_aa)

# ---------------------------------------------------------
# Test 2: Consultant slip (no PF/PT)
# ---------------------------------------------------------
consultant_slip = {
    "raw_text": "Consultancy Fees Retainer ID: C123",
    "company_name": "TCS",
    "extracted_data": {
        "gross_pay": 100000,
        "pf": 0,
        "pt": 0,
        "esic": 0,
        "tds": 10000, # 194J 10%
        "net_pay": 90000
    }
}
consultant_aa = {
    "credits_this_month": [{"amount": 90000, "date": date(2024, 6, 1)}],
    "credits_last_3_months": []
}
run_test("2. Consultant slip (no PF/PT)", consultant_slip, consultant_aa)

# ---------------------------------------------------------
# Test 3: ESIC charged on ₹50,000 gross
# ---------------------------------------------------------
esic_fraud_slip = {
    "raw_text": "Salary Slip",
    "company_name": "Infosys",
    "extracted_data": {
        "basic": 20000,
        "gross_pay": 50000,
        "esic": 500,  # FRAUD: gross > 21k
        "pf": 1800,
        "pt": 200,
        "tds": 0,
        "net_pay": 47500
    }
}
run_test("3. ESIC charged on 50k gross", esic_fraud_slip, consultant_aa)

# ---------------------------------------------------------
# Test 4: TCS slip with Basic at 55%
# ---------------------------------------------------------
tcs_fraud_slip = {
    "raw_text": "Salary Slip",
    "company_name": "TCS",
    "extracted_data": {
        "basic": 55000, # FRAUD: TCS baseline is 38-44%
        "gross_pay": 100000,
        "net_pay": 93000
    }
}
run_test("4. TCS slip with Basic at 55% (Cohort violation)", tcs_fraud_slip, perfect_aa)

# ---------------------------------------------------------
# Test 5: Split salary
# ---------------------------------------------------------
split_salary_aa = {
    "credits_this_month": [
        {"amount": 50000, "date": date(2024, 6, 1)},
        {"amount": 43000, "date": date(2024, 6, 15)}
    ],
    "credits_last_3_months": []
}
run_test("5. Split salary — two credits summing correctly", perfect_slip, split_salary_aa)

# ---------------------------------------------------------
# Test 6: April slip with shifted HRA ratio
# ---------------------------------------------------------
april_slip = {
    "raw_text": "Salary Slip",
    "company_name": "TCS",
    "city": "Bengaluru",
    "extracted_data": {
        "basic": 40000,
        "hra": 23000, # 57.5% - normally fails (50% max), but April restructuring band allows 8%
        "gross_pay": 100000,
        "net_pay": 93000,
        "slip_date": date(2024, 4, 15) # Within 60 days of April 1st trigger
    }
}
run_test("6. April slip with slightly shifted HRA ratio", april_slip, perfect_aa)

# ---------------------------------------------------------
# Test 7: Stripped EXIF (requires image)
# ---------------------------------------------------------
def create_stripped_exif_image(filepath):
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.putText(img, "FAKE", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.imwrite(filepath, img)
    # The default imwrite has no EXIF
    return filepath

img_path = create_stripped_exif_image("test_no_exif.jpg")
run_test("7. Stripped EXIF / no metadata", img_path, is_image=True)
