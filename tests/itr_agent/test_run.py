import json
import cv2
import numpy as np
import os
import sys

# Ensure Python can find our app package
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(root_dir)

from app.services.agents.itr_agent.main import process_verification

def create_dummy_image(filepath):
    dummy_image = np.ones((400, 800, 3), dtype=np.uint8) * 255
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(dummy_image, "INCOME TAX DEPARTMENT - ITR-V", (150, 50), font, 1, (0, 0, 0), 2)
    cv2.putText(dummy_image, "Name: John Doe", (50, 120), font, 0.7, (0, 0, 0), 1)
    cv2.putText(dummy_image, "PAN: ABCDE1234F", (50, 160), font, 0.7, (0, 0, 0), 1)
    cv2.putText(dummy_image, "Acknowledgment Number: 123456789012345", (50, 220), font, 0.8, (0, 0, 0), 2)
    # Give it a fake income so it routes to Human Review
    cv2.putText(dummy_image, "Gross Total Income: 999999", (50, 260), font, 0.7, (0, 0, 0), 1) 
    cv2.imwrite(filepath, dummy_image)
    return filepath

if __name__ == "__main__":
    print("Generating dummy ITR document...")
    img_filename = os.path.join(os.path.dirname(__file__), "dummy_test_itr.jpg")
    img_path = create_dummy_image(img_filename)
    
    print("\nProcessing document using Verification Agent (Image Input)...")
    result = process_verification(img_path, is_image=True, project_root=root_dir, show_heatmap=True)
    
    print("\n--- JSON OUTPUT RECEIVED BY OTHER AGENT ---")
    print(json.dumps(result, indent=2))
    
    print("\n---------------------------------------------------------")
    print("\nProcessing document using Verification Agent (Direct Number Input)...")
    result2 = process_verification("123456789012345", is_image=False, project_root=root_dir)
    print("\n--- JSON OUTPUT (Number Input) ---")
    print(json.dumps(result2, indent=2))
