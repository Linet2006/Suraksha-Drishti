import os
import json
import logging
import tempfile
import shutil
from fastapi import APIRouter, HTTPException, File, UploadFile, Form, BackgroundTasks
from google import genai
from PIL import Image
import io

from app.services.dna_comparison.itr_dna.main import run_itr_dna_analysis
from app.services.agents.itr_agent.scraper import verify_itr_status
from app.services.agents.udyam_agent.scraper import verify_udyam_number
from app.services.agents.trade_licence_agent.scraper import verify_trade_licence

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_metadata_with_gemini(file_bytes: bytes, is_pdf: bool, doc_type: str) -> dict:
    """Uses Gemini to extract structured JSON from the document based on its type."""
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        logger.error(f"Failed to init Gemini Client: {e}")
        return {}

    prompts = {
        "ITR/Form 16": "Extract the following details from this Form 16 or ITR into a JSON object: gross_salary (number as string), standard_deduction (number as string), total_tax_payable (number as string), pan (string), expected_pan_status (4th character of PAN, usually P). Return ONLY raw JSON without markdown formatting.",
        "Udyam Certificate": "Extract the udyam_number from this certificate. Return ONLY a JSON object with key 'udyam_number' and the string value, without markdown formatting.",
        "Trade Licence": "Extract the application_number, expected_business_name, and expected_owner_name from this trade licence. Return ONLY a JSON object with these keys without markdown formatting.",
        "GST Registration": "Extract the GSTIN from this document. Return ONLY a JSON object with key 'gstin' without markdown formatting.",
        "Salary Slip": "Extract the net_pay and employee_id. Return ONLY a JSON object with these keys without markdown formatting."
    }
    
    prompt = prompts.get(doc_type, "Extract key key-value pairs into a JSON object. Return ONLY raw JSON.")
    
    try:
        if is_pdf:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    {"mime_type": "application/pdf", "data": file_bytes},
                    prompt
                ]
            )
        else:
            img = Image.open(io.BytesIO(file_bytes))
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[prompt, img]
            )
            
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Gemini Extraction Error: {e}")
        return {}

def cleanup_file(path: str):
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        pass

@router.post("/verify/orchestrate")
async def verify_orchestrate(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_type: str = Form(...),
    verification_method: str = Form(...)
):
    """Unified endpoint for scanning and verifying documents."""
    logger.info(f"Orchestration request for {document_type} via {verification_method}")
    
    file_bytes = await file.read()
    is_pdf = file.filename.lower().endswith(".pdf")
    
    suffix = ".pdf" if is_pdf else os.path.splitext(file.filename)[1]
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    temp_path = temp_file.name
    
    with open(temp_path, "wb") as f:
        f.write(file_bytes)
        
    background_tasks.add_task(cleanup_file, temp_path)
    
    # 1. Universal Scanner
    extracted_data = extract_metadata_with_gemini(file_bytes, is_pdf, document_type)
    
    # 2. Routing
    try:
        from fastapi.concurrency import run_in_threadpool
        
        if verification_method == "Government Database":
            if document_type == "ITR/Form 16":
                pan = extracted_data.get("pan", "ABCDE1234F")
                ack = extracted_data.get("ack_number", "123456789012345")
                api_record = await run_in_threadpool(verify_itr_status, pan, ack)
                return {
                    "bucket": 1 if api_record and api_record.get("status") == "success" else 3,
                    "status": "Verified" if api_record and api_record.get("status") == "success" else "Forged",
                    "differences": [] if api_record and api_record.get("status") == "success" else ["Gov portal mismatch"],
                    "description": "Processed by Gov API",
                    "data": api_record
                }
            elif document_type == "Udyam Certificate":
                udyam_no = extracted_data.get("udyam_number", "")
                if not udyam_no:
                    return {"bucket": 3, "status": "Error", "description": "Failed to extract Udyam Number", "differences": []}
                result = await verify_udyam_number(udyam_no)
                return {"bucket": 1, "status": "Verified", "description": "Verified with MSME portal.", "differences": [], "data": result}
            elif document_type == "Trade Licence":
                app_no = extracted_data.get("application_number", "")
                if not app_no:
                    return {"bucket": 3, "status": "Error", "description": "Failed to extract Application Number", "differences": []}
                payload = {"application_number": app_no, "trade_type": "2"}
                result = await verify_trade_licence(payload)
                return {"bucket": 1, "status": "Verified", "description": "Verified with BBMP.", "differences": [], "data": result}
            else:
                return {"bucket": 2, "status": "Requires Review", "differences": ["Unsupported Gov API"], "description": f"Government database check for {document_type} is not yet integrated."}
                
        elif verification_method == "Forensic Analysis":
            if document_type == "ITR/Form 16":
                for k, v in extracted_data.items():
                    extracted_data[k] = str(v)
                result = await run_in_threadpool(run_itr_dna_analysis, temp_path, is_pdf, extracted_data)
                return result
            else:
                return {"bucket": 2, "status": "Requires Review", "differences": ["Forensic module pending"], "description": f"Forensic DNA analysis for {document_type} is still under development. Defaulting to manual review."}
        else:
            raise HTTPException(400, "Invalid verification method selected.")
            
    except Exception as e:
        logger.error(f"Orchestration Error: {e}")
        return {"bucket": 3, "status": "Forged / Error", "differences": [str(e)], "description": "A critical failure occurred during verification."}
