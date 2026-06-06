import pytesseract
from pytesseract import Output
import cv2
import re

# IMPORTANT FOR WINDOWS: Point pytesseract to the Winget installation
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_data_from_image(image_path):
    image_cv = cv2.imread(image_path)
    if image_cv is None:
        raise ValueError(f"Could not load image at {image_path}")
        
    extracted_text = pytesseract.image_to_string(image_cv)
    ocr_data = pytesseract.image_to_data(image_cv, output_type=Output.DICT)
    
    ack_match = re.search(r"(?i)Acknowledgment Number[\s:]*(\d{15})", extracted_text)
    income_match = re.search(r"(?i)Gross Total Income[\s:]*(\d+)", extracted_text)
    pan_match = re.search(r"(?i)PAN[\s:]*([A-Z0-9]{10})", extracted_text)
    name_match = re.search(r"(?i)Name[\s:]*([^\n]+)", extracted_text) 
    
    ack_number = ack_match.group(1) if ack_match else None
    income = int(income_match.group(1)) if income_match else None
    pan = pan_match.group(1) if pan_match else None
    name = name_match.group(1).strip() if name_match else None
    
    return {
        "image_cv": image_cv,
        "ocr_data": ocr_data,
        "extracted_data": {
            "ack_number": ack_number,
            "income": income,
            "pan": pan,
            "name": name
        }
    }
