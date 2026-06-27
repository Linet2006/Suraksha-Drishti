import os

def extract_aadhaar_data(image_path: str) -> dict:
    """
    MOCK OFFLINE OCR FOR AADHAAR
    In production, this would use PaddleOCR / Tesseract to read the printed text.
    For this demo, we simulate the OCR extraction so it runs 100% offline without Docker.
    """
    basename = os.path.basename(image_path).lower()
    
    if "fake" in basename or "tamper" in basename:
        return {
            "name": "Rajesh Kumar Sharma", # Surname mismatch with QR (Verma)
            "aadhaar_number": "9012 5678 1230", # Fails Verhoeff checksum
            "dob": "15/08/1985",
            "gender": "M"
        }
        
    return {
        "name": "Rajesh Kumar Verma",
        "aadhaar_number": "901256781234", # Valid UID (mock)
        "dob": "15/08/1985",
        "gender": "M"
    }

def extract_pan_data(image_path: str) -> dict:
    """
    MOCK OFFLINE OCR FOR PAN
    """
    basename = os.path.basename(image_path).lower()
    
    if "fake" in basename or "tamper" in basename:
        return {
            "name": "Rajesh Kumar Verma",
            "pan_number": "ABCDE1234F" # 4th char 'E' (invalid), 5th char 'E' (doesn't match 'V')
        }
        
    return {
        "name": "Rajesh Kumar Verma",
        "pan_number": "ABC PV 1234 F" # Spaces to test regex stripping. P=Person, V=Verma
    }
