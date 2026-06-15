import cv2
import re
import os

def extract_data_from_image(image_path):
    """
    Simulates Pure OCR text extraction for Layer 1.
    """
    image_cv = cv2.imread(image_path)
    if image_cv is None:
        raise ValueError(f"Could not load image at {image_path}")
        
    # In a real scenario, pytesseract.image_to_string(image_cv) would be here.
    # For the hackathon demo, we route the mock data based on the filename passed.
    
    basename = os.path.basename(image_path).lower()
    
    if "new_slip" in basename:
        # Nexora Slip (Passes Math)
        extracted_text = "NEXORA TECHNOLOGIES PVT. LTD. SALARY SLIP May 2026 This is a computer-generated salary slip and does not require a physical signature."
        extracted_data = {
            "basic": 30000,
            "hra": 12000,
            "pf": 1800,
            "pt": 200,
            "esic": 0,
            "tds": 1500,
            "gross_pay": 50000,
            "total_deductions": 3500,
            "net_pay": 46500,
            "name": "Asha Sharma",
            "emp_id": "NEX1025"
        }
        
    elif "slip" in basename:
        # Nexatech Slip (Fails Math due to illegal ESIC)
        extracted_text = "NEXATECH SOLUTIONS PRIVATE LIMITED SALARY SLIP MAY 2026 Employee ID: NXT-EMP-20214"
        extracted_data = {
            "basic": 45000,
            "hra": 18000,
            "pf": 5400,
            "pt": 200,
            "esic": 662,  # Illegal
            "tds": 3500,
            "gross_pay": 80950,
            "total_deductions": 9762,
            "net_pay": 71188,
            "name": "Rajesh Kumar Verma",
            "emp_id": "NXT-EMP-20214"
        }
        
    else:
        # Default John Doe
        extracted_text = "Salary Slip Employee ID: EMP123 Name: John Doe Basic: 40000 HRA: 20000 PF: 1800 Gross Pay: 100000 Net Pay: 93000"
        extracted_data = {
            "basic": 40000,
            "hra": 20000,
            "pf": 1800,
            "pt": 200,
            "gross_pay": 100000,
            "net_pay": 93000,
            "name": "John Doe",
            "emp_id": "EMP123"
        }
    
    return {
        "image_cv": image_cv,
        "ocr_data": {},
        "extracted_data": extracted_data,
        "raw_text": extracted_text
    }
