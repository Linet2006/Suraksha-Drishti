import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import cv2
import sys
import os

def highlight_paradox(image_path="../../data/debug/salaryslip/new_slip.jpg"):
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not load {image_path}")
        return
        
    h, w, _ = img.shape
    
    # The paradox is the physical signature on the bottom right 
    # combined with the text at the very bottom.
    # Coordinates for the bottom right quadrant
    x1, y1 = int(w * 0.6), int(h * 0.82)
    x2, y2 = int(w * 0.98), int(h * 0.98)
    
    # Draw a thick red rectangle around the paradox area
    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 0, 255), 4)
    
    # Also draw a line pointing to the footer text
    footer_y = int(h * 0.96)
    cv2.arrowedLine(img, (int(w * 0.75), y2), (int(w * 0.5), footer_y), (0, 0, 255), 3)
    
    # Add the aggressive label pointing it out
    label1 = "AI HALLUCINATION DETECTED:"
    label2 = "PHYSICAL SIGNATURE ON A"
    label3 = "COMPUTER-GENERATED SLIP!"
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.7
    thickness = 2
    
    # Draw the labels
    text_y = y1 - 70
    for i, text in enumerate([label1, label2, label3]):
        # Black background for readability
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = x1 - 50
        current_y = text_y + (i * 30)
        cv2.rectangle(img, (text_x - 5, current_y - text_size[1] - 5), (text_x + text_size[0] + 5, current_y + 5), (0, 0, 255), -1)
        cv2.putText(img, text, (text_x, current_y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
        
    output_path = "new_slip_highlighted.jpg"
    cv2.imwrite(output_path, img)
    print(f"[SUCCESS] Highlighted the logical paradox and saved to: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        highlight_paradox(sys.argv[1])
    else:
        highlight_paradox()
