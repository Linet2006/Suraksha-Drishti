from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from app.services.agents.itr_agent.main import process_verification
from app.services.agents.udyam_agent.scraper import verify_udyam_number, UdyamVerificationError

router = APIRouter()
logger = logging.getLogger(__name__)

class VerificationRequest(BaseModel):
    pan: str
    ack_number: str
    income: Optional[int] = None
    name: Optional[str] = None

class UdyamVerifyRequest(BaseModel):
    udyam_number: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "udyam_number": "UDYAM-XX-00-0000000"
            }
        }
    }

class UdyamVerifyResponse(BaseModel):
    status: str
    data: dict

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

@router.post("/verify/udyam", response_model=UdyamVerifyResponse)
async def verify_udyam(request: UdyamVerifyRequest):
    """
    Endpoint to verify a Udyam Registration Number.
    Uses headless Chromium and Tesseract OCR to bypass CAPTCHA.
    """
    logger.info(f"Received API request for Udyam Number: {request.udyam_number}")
    try:
        # Call the Playwright automation script
        extracted_data = await verify_udyam_number(request.udyam_number)
        
        # Include the original input number in the response payload
        response_data = {"udyam_number": request.udyam_number}
        response_data.update(extracted_data)
        
        return {
            "status": "success",
            "data": response_data
        }
        
    except UdyamVerificationError as e:
        # Catch our custom domain error and raise an HTTP Exception
        logger.warning(f"Udyam verification failed: {e.message}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in Udyam verification: {e}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
