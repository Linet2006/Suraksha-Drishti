import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import cv2
import numpy as np
import sys
import os

def highlight_esi_mistake(image_path="../../data/debug/salaryslip/slip.jpg"):
    print(f"Analyzing original image ({image_path}) to automatically locate the ESI deduction...")
    
    # Load the original slip to find the red text coordinates
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load {image_path}")
        return
        
    # Convert to HSV to isolate the dark red/brown text used in the Deductions column
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Red/Brown HSV ranges
    lower_red1 = np.array([0, 30, 30])
    upper_red1 = np.array([20, 255, 255])
    lower_red2 = np.array([160, 30, 30])
    upper_red2 = np.array([180, 255, 255])
    
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = mask1 | mask2
    
    # Dilate the mask to group characters of the same number together into single wide blobs
    kernel = np.ones((5, 10), np.uint8)
    dilated = cv2.dilate(mask, kernel, iterations=1)
    
    # Find contours
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter out very small noise and sort top-to-bottom
    valid_boxes = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w > 5 and h > 5:  # Looser filter to catch smaller text like "200" or "662"
            valid_boxes.append((x, y, w, h))
            
    valid_boxes = sorted(valid_boxes, key=lambda b: b[1])
    
    # In the slip, the red deduction numbers appear vertically:
    # 1. 5,400 (PF)
    # 2. 200 (PT)
    # 3. 3,500 (TDS)
    # 4. 662 (ESI) <--- This is the one we want!
    # 5. 9,762 (Total)
    
    if len(valid_boxes) >= 4:
        x, y, w, h = valid_boxes[3]
        
        # We will draw on a copy of the original image instead of the heatmap
        output_img = img.copy()
            
        # Draw a thick red circle around the mistake (Red contrasts well with the white slip)
        center = (x + w//2, y + h//2)
        radius = max(w, h) + 30
        cv2.circle(output_img, center, radius, (0, 0, 255), 6) # Thick Red circle
        
        # Add an aggressive label pointing it out
        label = "AI HALLUCINATION DETECTED: ILLEGAL ESI CALCULATION"
        
        # We will draw the label with a red background for readability
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.8
        thickness = 2
        text_size = cv2.getTextSize(label, font, font_scale, thickness)[0]
        
        text_x = max(10, x - 100)
        text_y = max(40, y - radius - 20)
        
        # Red background rectangle for text
        cv2.rectangle(output_img, (text_x - 5, text_y - text_size[1] - 5), (text_x + text_size[0] + 5, text_y + 5), (0, 0, 255), -1)
        # White text
        cv2.putText(output_img, label, (text_x, text_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
        output_path = "slip_highlighted.jpg"
        cv2.imwrite(output_path, output_img)
        print(f"\n[SUCCESS] Automatically found the ESI mistake and rounded it up!")
        print(f"Saved the highlighted presentation image to: {output_path}")
    else:
        print(f"\n[WARNING] Could not automatically find the 4th red number. Found {len(valid_boxes)} items.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        highlight_esi_mistake(sys.argv[1])
    else:
        highlight_esi_mistake()
