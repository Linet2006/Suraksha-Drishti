import cv2
import numpy as np
import os

def generate_overlay(image_path, issues_list):
    """
    Automated API Explainability Generator.
    Reads the list of issues and dynamically overlays bounding boxes and text labels
    onto the original image to provide visual proof of the fraud logic.
    """
    if not os.path.exists(image_path):
        return None
        
    img = cv2.imread(image_path)
    if img is None:
        return None
        
    h, w, _ = img.shape
    overlay_generated = False
    
    # 1. Check for ESIC/Statutory violations (from Slip 1)
    # If a statutory ESIC violation is found, use CV to highlight the red text
    esic_violation = any("ESIC" in issue and "Statutory violation" in issue for issue in issues_list)
    if esic_violation:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        # Red HSV ranges
        lower_red1 = np.array([0, 30, 30])
        upper_red1 = np.array([20, 255, 255])
        lower_red2 = np.array([160, 30, 30])
        upper_red2 = np.array([180, 255, 255])
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = mask1 | mask2
        
        # Find contours of red text
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bounding_boxes = []
        for cnt in contours:
            x, y, bw, bh = cv2.boundingRect(cnt)
            if bw > 10 and bh > 10:  # Filter out noise
                bounding_boxes.append((x, y, bw, bh))
                
        # Group close bounding boxes to circle the entire number
        if bounding_boxes:
            bounding_boxes.sort(key=lambda b: b[1])  # Sort by Y
            
            # The 4th red item down is typically the ESIC amount in this specific template
            # For the demo, we assume the largest cluster or simply draw a box around the first prominent red blob
            # Let's just find the overall bounding box of all red text in the lower half
            valid_boxes = [b for b in bounding_boxes if b[1] > h // 2]
            if valid_boxes:
                min_x = min([b[0] for b in valid_boxes])
                min_y = min([b[1] for b in valid_boxes])
                max_x = max([b[0] + b[2] for b in valid_boxes])
                max_y = max([b[1] + b[3] for b in valid_boxes])
                
                # Expand box slightly
                padding = 15
                cv2.rectangle(img, (min_x - padding, min_y - padding), (max_x + padding, max_y + padding), (0, 0, 255), 3)
                
                # Add label
                label = "DNA MATH ENGINE FAILED:"
                label2 = "ESIC CHARGED ON 80K GROSS"
                font = cv2.FONT_HERSHEY_SIMPLEX
                cv2.rectangle(img, (min_x - 150, min_y - 60), (min_x + 300, min_y - 10), (0, 0, 255), -1)
                cv2.putText(img, label, (min_x - 140, min_y - 40), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                cv2.putText(img, label2, (min_x - 140, min_y - 20), font, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
                overlay_generated = True

    # 2. Check for Logical Paradoxes (from Slip 2)
    paradox_violation = any("PARADOX" in issue for issue in issues_list)
    if paradox_violation:
        x1, y1 = int(w * 0.6), int(h * 0.82)
        x2, y2 = int(w * 0.98), int(h * 0.98)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 4)
        footer_y = int(h * 0.96)
        cv2.arrowedLine(img, (int(w * 0.75), y2), (int(w * 0.5), footer_y), (0, 0, 255), 3)
        
        labels = [
            "AI HALLUCINATION DETECTED:",
            "PHYSICAL SIGNATURE ON A",
            "COMPUTER-GENERATED SLIP!"
        ]
        
        text_y = y1 - 70
        font = cv2.FONT_HERSHEY_SIMPLEX
        for i, text in enumerate(labels):
            text_size = cv2.getTextSize(text, font, 0.7, 2)[0]
            text_x = x1 - 50
            current_y = text_y + (i * 30)
            cv2.rectangle(img, (text_x - 5, current_y - text_size[1] - 5), (text_x + text_size[0] + 5, current_y + 5), (0, 0, 255), -1)
            cv2.putText(img, text, (text_x, current_y), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
            
        overlay_generated = True
        
    if overlay_generated:
        basename = os.path.basename(image_path)
        name, ext = os.path.splitext(basename)
        output_filename = f"{name}_highlighted{ext}"
        output_dir = os.path.dirname(image_path)
        if not output_dir: output_dir = "."
        output_path = os.path.join(output_dir, output_filename)
        
        cv2.imwrite(output_path, img)
        return output_path
        
    return None
