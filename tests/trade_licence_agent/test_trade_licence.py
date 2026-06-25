import requests
import time
import json
import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(root_dir)

def test_trade_licence_verification():
    url = "http://localhost:8000/api/v1/verify/trade_licence"
    
    # Generic mock payload
    payload = {
        "application_number": "BBMP/TL/001",
        "expected_business_name": "Mock Business Name",
        "expected_owner_name": "Mock Owner"
    }
    
    print(f"Sending Trade License Verification Request for: {payload['application_number']}")
    print("Waiting for Playwright agent to navigate, download PDF, and parse...")
    
    start_time = time.time()
    
    try:
        response = requests.post(url, json=payload, timeout=90)
        
        print(f"\nResponse Code: {response.status_code}")
        print("Response Body:")
        print(json.dumps(response.json(), indent=4))
        
    except requests.exceptions.Timeout:
        print("\nThe request timed out. The portal might be slow or Playwright navigation failed.")
    except Exception as e:
        print(f"\nError: {e}")
        
    end_time = time.time()
    print(f"\nTime taken: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    test_trade_licence_verification()
