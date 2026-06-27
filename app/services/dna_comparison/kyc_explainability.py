import cv2
import os
import datetime

def generate_kyc_overlay(image_path: str, flags: list, document_type: str = "AADHAAR") -> str:
    """
    Reads the flags from the DNA Engine and draws explicit bounding boxes 
    and text labels directly on the original uploaded image to provide 
    Visual Proof of the anomalies.
    """
    if not image_path or not os.path.exists(image_path):
        return None
        
    img = cv2.imread(image_path)
    if img is None:
        return None
        
    h, w, _ = img.shape
    overlay_generated = False
    
    flag_ids = [f.get("flag", "") for f in flags]
    
    # 1. QR Decode Failure (Aadhaar specific)
    if "QR_UNREADABLE" in flag_ids and document_type == "AADHAAR":
        # QR is typically on the right side of the card
        x1, y1 = int(w * 0.60), int(h * 0.20)
        x2, y2 = int(w * 0.95), int(h * 0.85)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 4) # Red box
        
        text = "QR DECODE FAILED"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (x1 - 10, y1 - 40), (x1 + 300, y1), (0, 0, 255), -1)
        cv2.putText(img, text, (x1, y1 - 15), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        overlay_generated = True

    # 2. PAN Format Invalid
    if "PAN_FORMAT_INVALID" in flag_ids and document_type == "PAN":
        # PAN number is typically in the lower middle
        x1, y1 = int(w * 0.20), int(h * 0.60)
        x2, y2 = int(w * 0.80), int(h * 0.85)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 4) # Red box
        
        text = "INVALID FORMAT DETECTED"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (x1 - 10, y1 - 40), (x1 + 350, y1), (0, 0, 255), -1)
        cv2.putText(img, text, (x1, y1 - 15), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        overlay_generated = True
        
    # 3. Forensics/Metadata Warnings
    if "FORENSICS_WARNING" in flag_ids:
        # Draw a thick border around the entire image to indicate metadata/global issues
        cv2.rectangle(img, (10, 10), (w - 10, h - 10), (0, 0, 255), 10)
        
        text = "METADATA / FORENSICS ANOMALY"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (w - 20, 60), (0, 0, 255), -1)
        cv2.putText(img, text, (30, 50), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        overlay_generated = True
        
    # 4. If perfectly clean, draw a green VERIFIED stamp!
    if not overlay_generated:
        # Draw a bright green stamp in the top left
        text = "SUCCESS: VERIFIED GENUINE"
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.rectangle(img, (20, 20), (450, 60), (0, 200, 0), -1)
        cv2.putText(img, text, (30, 50), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
        cv2.rectangle(img, (10, 10), (w - 10, h - 10), (0, 200, 0), 10) # Green border
        overlay_generated = True
        
    if overlay_generated:
        basename = os.path.basename(image_path)
        name_only, ext = os.path.splitext(basename)
        filename = f"proof_{name_only}_{int(datetime.datetime.now().timestamp())}.jpg"
        output_dir = os.path.abspath("data/outputs/kyc")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        cv2.imwrite(output_path, img)
        return filename
        
    return None
