import time

MOCK_GOVT_DB = {
    "123456789012345": {
        "status": "Filed",
        "gross_income": 500000,
        "pan_number": "ABCDE1234F",
        "name": "John Doe"
    },
    "987654321098765": {
        "status": "Filed",
        "gross_income": 1200000,
        "pan_number": "FGHIJ5678K",
        "name": "Jane Smith"
    }
}

def verify_with_government_api(ack_number):
    """
    Simulates calling the Income Tax Department API.
    """
    time.sleep(0.5) 
    return MOCK_GOVT_DB.get(ack_number)
