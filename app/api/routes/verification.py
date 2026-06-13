from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from app.services.agents.itr_agent.main import process_verification

router = APIRouter()
logger = logging.getLogger(__name__)

class VerificationRequest(BaseModel):
    pan: str
    ack_number: str
    income: Optional[int] = None
    name: Optional[str] = None

@router.post("/verify/itr")
async def verify_itr(request: VerificationRequest):
    """
    Endpoint to trigger the ITR Verification Agent directly with data (no image).
    This will spin up the Playwright browser and fetch data from the government portal.
    """
    logger.info(f"Received API request for PAN: {request.pan}, ACK: {request.ack_number}")
    
    # We construct the input data similar to what the OCR would output
    extracted_data = {
        "pan": request.pan,
        "ack_number": request.ack_number,
        "income": request.income,
        "name": request.name
    }
    
    try:
        # We call the process_verification function in "direct data" mode by patching the OCR
        # Since is_image is normally true for the full flow, we can simulate an image pass 
        # or just pass the data directly. Currently `process_verification` expects `input_data` to be an ack_number if `is_image` is False.
        # Let's write a small wrapper or just use the agent logic.
        
        from app.services.agents.itr_agent.scraper import verify_itr_status
        from fastapi.concurrency import run_in_threadpool
        
        # 1. Run Scraper in a threadpool to prevent blocking FastAPI's async event loop
        api_record = await run_in_threadpool(verify_itr_status, request.pan, request.ack_number)
        
        risk_score = 0
        issues = []
        bucket = "Bucket 1"
        decision = "Auto-Approve"
        
        if api_record and api_record.get("status") == "error":
            risk_score += 50
            issues.append(api_record.get("message", "Record NOT FOUND in Government DB."))
        elif api_record and api_record.get("status") == "success":
            govt_income = api_record.get("govt_income")
            
            # Tamper Cross-Check
            if request.income is not None and govt_income is not None:
                try:
                    income_val = int(str(request.income).replace(",", "").strip())
                    govt_income_val = int(str(govt_income).replace(",", "").strip())
                    if income_val != govt_income_val:
                        risk_score += 100
                        issues.append(f"Income Mismatch! Doc: {request.income}, Govt: {govt_income}")
                except ValueError:
                    issues.append("Could not parse income mathematically.")
                    
        # Bucket Routing
        if risk_score <= 30: 
            bucket = "Bucket 1"
            decision = "Auto-Approve"
        elif risk_score <= 65: 
            bucket = "Bucket 2"
            decision = "Human Review Required"
        else: 
            bucket = "Bucket 3"
            decision = "Auto-Reject"
            
        output = {
            "routing": {
                "score": risk_score,
                "bucket": bucket,
                "decision": decision
            },
            "explainability": {
                "issues": issues,
            },
            "extracted_data": extracted_data
        }
        
        return output

    except Exception as e:
        logger.error(f"Error processing verification: {e}")
        raise HTTPException(status_code=500, detail=str(e))
