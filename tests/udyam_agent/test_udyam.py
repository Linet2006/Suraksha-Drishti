import requests
import time
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(root_dir)

def test_udyam_verification():
    url = "http://localhost:8000/api/v1/verify/udyam"
    
    # Replace this with a real Udyam number for actual testing
    payload = {
        "udyam_number": "UDYAM-MH-01-0000021"
    }
    
    print(f"Sending Udyam Verification Request for: {payload['udyam_number']}")
    print("Waiting for Playwright agent to navigate and solve CAPTCHA...")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        print(f"\nResponse Code: {response.status_code}")
        print("Response Body:")
        import json
        print(json.dumps(response.json(), indent=4))
        
    except requests.exceptions.Timeout:
        print("\nThe request timed out. The portal might be slow or CAPTCHA solving failed.")
    except Exception as e:
        print(f"\nError: {e}")
        
    end_time = time.time()
    print(f"\nTime taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    test_udyam_verification()
