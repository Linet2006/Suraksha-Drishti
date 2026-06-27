"""Quick diagnostic to test the DNA pipelines directly, bypassing the web server."""
import os
import sys
import glob

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("=" * 60)
print("DIAGNOSTIC: Suraksha Drishti DNA Pipeline Test")
print("=" * 60)

# 1. Check environment
colab_url = os.getenv("COLAB_API_URL", "")
print(f"\n[ENV] COLAB_API_URL = '{colab_url}'")

# 2. Find test images
kyc_dir = os.path.join("data", "outputs", "kyc")
print(f"\n[FILES] Checking {kyc_dir}...")
if os.path.isdir(kyc_dir):
    files = os.listdir(kyc_dir)
    print(f"  Found {len(files)} files: {files}")
else:
    print("  Directory does not exist!")

# 3. Test with a synthetic image to verify pipeline doesn't crash
import numpy as np
import cv2

test_path = os.path.join("data", "outputs", "kyc", "test_diagnostic.jpg")
os.makedirs(os.path.dirname(test_path), exist_ok=True)

# Create a simple white image with Aadhaar-like text
test_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
cv2.putText(test_img, "1234 5678 9012", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 2)
cv2.putText(test_img, "RAJESH KUMAR", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
cv2.putText(test_img, "DOB: 01/01/1990", (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
cv2.imwrite(test_path, test_img)
print(f"\n[TEST] Created diagnostic test image at {test_path}")

verify_img = cv2.imread(test_path)
print(f"[TEST] cv2.imread verification => shape={verify_img.shape if verify_img is not None else 'NONE!'}")

# 4. Run Aadhaar DNA on the test image
print("\n" + "=" * 60)
print("TEST 1: AADHAAR DNA ANALYSIS")
print("=" * 60)
try:
    from app.services.dna_comparison.aadhaar_dna.forensics import run_aadhaar_verification
    result = run_aadhaar_verification(
        aadhaar_image_path=test_path,
        selfie_path=None,
        ocr_extracted_fields={},
        itr_address=None
    )
    print(f"\n[RESULT] verified={result['verified']}")
    print(f"[RESULT] risk_score={result['risk_score']}")
    print(f"[RESULT] aadhaar_number={result.get('aadhaar_number')}")
    print(f"[RESULT] flags:")
    for f in result.get("flags", []):
        if isinstance(f, dict):
            print(f"  - {f.get('flag', 'UNKNOWN')}: {f.get('description', str(f))}")
        else:
            print(f"  - {f}")
except Exception as e:
    print(f"[ERROR] Aadhaar DNA crashed: {e}")
    import traceback
    traceback.print_exc()

# 5. Run PAN DNA on test image
print("\n" + "=" * 60)
print("TEST 2: PAN DNA ANALYSIS")
print("=" * 60)

pan_test_path = os.path.join("data", "outputs", "kyc", "test_pan_diagnostic.jpg")
pan_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
cv2.putText(pan_img, "ABCPK1234F", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
cv2.putText(pan_img, "RAJESH KUMAR", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
cv2.putText(pan_img, "INCOME TAX DEPARTMENT", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
cv2.imwrite(pan_test_path, pan_img)

try:
    from app.services.dna_comparison.pan_dna.forensics import run_pan_verification
    result = run_pan_verification(
        pan_card_image_path=pan_test_path,
        ocr_extracted={},
        aadhaar_qr_name="RAJESH KUMAR",
        all_documents={}
    )
    print(f"\n[RESULT] verified={result['verified']}")
    print(f"[RESULT] risk_score={result['risk_score']}")
    print(f"[RESULT] pan_number={result.get('pan_number')}")
    print(f"[RESULT] flags:")
    for f in result.get("flags", []):
        if isinstance(f, dict):
            print(f"  - {f.get('flag', 'UNKNOWN')}: {f.get('description', str(f))}")
        else:
            print(f"  - {f}")
except Exception as e:
    print(f"[ERROR] PAN DNA crashed: {e}")
    import traceback
    traceback.print_exc()

# Cleanup
for p in [test_path, pan_test_path]:
    if os.path.exists(p):
        os.remove(p)

print("\n" + "=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
