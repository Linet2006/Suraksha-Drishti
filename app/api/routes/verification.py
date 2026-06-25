from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from app.services.agents.itr_agent.main import process_verification
from app.services.agents.udyam_agent.scraper import verify_udyam_number, UdyamVerificationError
from app.services.agents.trade_licence_agent.scraper import verify_trade_licence, TradeLicenceVerificationError
import os

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

class TradeLicenseVerifyRequest(BaseModel):
    application_number: str
    trade_type: Optional[str] = "2"  # "1" = Trade & Power, "2" = Trade, "3" = Power
    expected_business_name: Optional[str] = None
    expected_owner_name: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "application_number": "BBMP/TL/001",
                "trade_type": "2",
                "expected_business_name": "My Shop",
                "expected_owner_name": "John Doe"
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
    Uses headless Chromium and Gemini AI to bypass CAPTCHA.
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

def cleanup_pdf(pdf_path: str):
    """Background task to delete the temporary PDF."""
    try:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
            logger.info(f"Cleaned up temporary PDF: {pdf_path}")
    except Exception as e:
        logger.error(f"Failed to clean up PDF {pdf_path}: {e}")

from fastapi import BackgroundTasks

@router.post("/verify/trade_licence")
async def verify_trade_licence_endpoint(request: TradeLicenseVerifyRequest, background_tasks: BackgroundTasks):
    """
    Endpoint to verify a BBMP Trade License.
    Downloads the certificate, parses the PDF, and cross-verifies the user's expected data.
    ALWAYS returns the structured 4-field output: bucket, status, differences, description.
    """
    logger.info(f"Received API request for Trade License: {request.application_number}")
    
    payload = {
        "application_number": request.application_number,
        "trade_type": request.trade_type or "2"
    }
    
    risk_score = 0
    issues = []
    scraped_text = ""
    
    # --- Step 1: Attempt to fetch data from the BBMP portal ---
    try:
        result = await verify_trade_licence(payload)
        scraped_text = result.get("scraped_text", "").lower()
        pdf_path = result.get("pdf_path")
        
        # Schedule cleanup of the temporary PDF
        if pdf_path:
            background_tasks.add_task(cleanup_pdf, pdf_path)
            
    except TradeLicenceVerificationError as e:
        logger.warning(f"Trade Licence verification failed: {e.message}")
        
        # Document not found / invalid application number → Auto-Reject
        if e.status_code in (400, 404):
            risk_score = 100
            issues.append(f"Government Portal Rejection: {e.message}")
        # Portal is down / unreachable → Human Review needed
        elif e.status_code in (503, 504):
            risk_score = 50
            issues.append(f"Portal Unavailable: {e.message}. Manual verification required.")
        # Any other scraper error
        else:
            risk_score = 60
            issues.append(f"Verification Error: {e.message}. Manual verification recommended.")
            
    except Exception as e:
        logger.error(f"Unexpected error in Trade Licence verification: {e}")
        risk_score = 60
        issues.append(f"System Error: {str(e)}. Manual verification recommended.")
    
    # --- Step 2: Cross-verify user-provided data against scraped PDF text ---
    if scraped_text:
        if request.expected_business_name:
            expected_biz = request.expected_business_name.lower()
            if expected_biz not in scraped_text:
                risk_score += 50
                issues.append(f"Business Name Mismatch: '{request.expected_business_name}' not found in official certificate.")
                
        if request.expected_owner_name:
            expected_owner = request.expected_owner_name.lower()
            if expected_owner not in scraped_text:
                risk_score += 50
                issues.append(f"Owner Name Mismatch: '{request.expected_owner_name}' not found in official certificate.")
    
    # --- Step 3: Bucket Routing (0-100 score) ---
    if risk_score <= 30: 
        bucket = "Bucket 1 (Auto-Approve)"
        decision = "Auto-Approve"
        status = "Verified"
        description = "Verification complete. All checks passed. The trade license is valid and matches the provided details."
    elif risk_score <= 65: 
        bucket = "Bucket 2 (Human Review)"
        decision = "Human Review Required"
        status = "Requires Manual Review"
        description = "Verification incomplete or partial mismatch detected. A human underwriter should review the flagged issues before approval."
    else: 
        bucket = "Bucket 3 (Auto-Reject)"
        decision = "Auto-Reject"
        status = "Rejected / Not Verified"
        description = "Verification failed. The trade license could not be validated against the BBMP government portal. The document may be forged, expired, or the application number is invalid."
    
    # --- Step 4: Build the structured output ---
    output = {
        "routing": {
            "score": risk_score,
            "bucket": bucket,
            "decision": decision
        },
        "status": status,
        "differences": issues,
        "description": description,
        "extracted_data": {
            "application_number": request.application_number,
            "trade_type": request.trade_type,
            "expected_business_name": request.expected_business_name,
            "expected_owner_name": request.expected_owner_name
        }
    }
    
    return output
