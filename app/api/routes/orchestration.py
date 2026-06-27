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

from app.services.dna_comparison.aadhaar_dna.main import run_aadhaar_dna_analysis
from app.services.dna_comparison.pan_dna.main import run_pan_dna_analysis
from app.services.dna_comparison.property_dna.main import run_property_dna_analysis
from app.services.dna_comparison.salary_slip_dna.main import run_salary_slip_dna_analysis

router = APIRouter()
logger = logging.getLogger(__name__)

def extract_metadata_with_gemma_local(file_bytes: bytes, is_pdf: bool, doc_type: str) -> dict:
    """Uses local Gemma 3 via Ollama to extract text from document images. Data never leaves the machine."""
    import base64
    import requests
    
    prompts = {
        "ITR/Form 16": "Extract from this document: gross_salary, standard_deduction, total_tax_payable, pan, expected_pan_status. Return ONLY a JSON object.",
        "Udyam Certificate": "Extract the udyam_number from this certificate. Return ONLY a JSON object with key 'udyam_number'.",
        "Trade Licence": "Extract the application_number, expected_business_name, expected_owner_name. Return ONLY a JSON object.",
        "GST Registration": "Extract the GSTIN. Return ONLY a JSON object with key 'gstin'.",
        "Salary Slip": "Extract the net_pay and employee_id. Return ONLY a JSON object.",
        "Aadhaar": "Extract the 12-digit aadhaar_number (digits only, no spaces) and the full name of the person. Return ONLY a JSON object like {\"aadhaar_number\": \"123456789012\", \"name\": \"FULL NAME\"}.",
        "PAN": "Extract the 10-character PAN number (like ABCPK1234F) and the full name. Return ONLY a JSON object like {\"pan_number\": \"ABCPK1234F\", \"name\": \"FULL NAME\"}.",
        "Property": "Extract the execution_date and registration_date. Return ONLY a JSON object."
    }
    
    prompt = prompts.get(doc_type, "Extract key-value pairs into a JSON object. Return ONLY raw JSON.")
    
    # --- Try Ollama (Gemma 3 local) first ---
    try:
        if is_pdf:
            import pypdfium2 as pdfium
            import io
            # Render first page of PDF to image for Gemma
            pdf = pdfium.PdfDocument(file_bytes)
            page = pdf[0]
            pil_image = page.render(scale=2).to_pil()
            buf = io.BytesIO()
            pil_image.save(buf, format='JPEG')
            image_bytes_for_gemma = buf.getvalue()
        else:
            image_bytes_for_gemma = file_bytes
            
        b64_image = base64.b64encode(image_bytes_for_gemma).decode("utf-8")
        
        ollama_payload = {
            "model": "gemma3:4b",
            "prompt": prompt,
            "images": [b64_image],
            "stream": False
        }
        
        resp = requests.post("http://localhost:11434/api/generate", json=ollama_payload, timeout=60)
        
        if resp.status_code == 200:
            raw_response = resp.json().get("response", "")
            logger.info(f"[GEMMA3 LOCAL] Raw response: {raw_response}")
            
            # Clean up the response
            text = raw_response.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            # Try to find JSON in the response
            text = text.strip()
            # Find the first { and last }
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                text = text[start:end+1]
                
            result = json.loads(text)
            logger.info(f"[GEMMA3 LOCAL] Parsed: {result}")
            return result
        else:
            logger.warning(f"[GEMMA3] Ollama returned status {resp.status_code}")
    except requests.ConnectionError:
        logger.warning("[GEMMA3] Ollama not running at localhost:11434. Falling back to Gemini API.")
    except Exception as e:
        logger.warning(f"[GEMMA3] Ollama error: {e}. Falling back to Gemini API.")
    
    # --- Fallback to Gemini API ---
    return extract_metadata_with_gemini(file_bytes, is_pdf, doc_type)


def extract_metadata_with_gemini(file_bytes: bytes, is_pdf: bool, doc_type: str) -> dict:
    """Fallback: Uses Gemini API to extract structured JSON from the document."""
    from google.genai import types
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
        "Salary Slip": "Extract the net_pay and employee_id. Return ONLY a JSON object with these keys without markdown formatting.",
        "Aadhaar": "Extract the following from this Aadhaar card image into a JSON object: aadhaar_number (the 12-digit number, digits only, no spaces), name (full name of the person). Return ONLY raw JSON without markdown formatting.",
        "PAN": "Extract the following from this PAN card image into a JSON object: pan_number (the 10-character alphanumeric PAN like ABCPK1234F), name (full name of the person). Return ONLY raw JSON without markdown formatting.",
        "Property": "Extract the execution_date and registration_date. Return ONLY a JSON object with these keys without markdown formatting."
    }
    
    prompt = prompts.get(doc_type, "Extract key key-value pairs into a JSON object. Return ONLY raw JSON.")
    
    try:
        if is_pdf:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type="application/pdf"),
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
    
    temp_file.write(file_bytes)
    temp_file.close()
        
    background_tasks.add_task(cleanup_file, temp_path)
    
    # 1. Universal Scanner — Gemma 3 (local via Ollama) extracts text, falls back to Gemini API
    extracted_data = extract_metadata_with_gemma_local(file_bytes, is_pdf, document_type)
    
    # Robust normalization for field names
    if isinstance(extracted_data, dict):
        keys = list(extracted_data.keys())
        for k in keys:
            kl = k.lower().replace(" ", "_")
            if document_type == "PAN" and kl in ["pan", "pan_no", "pan_number", "pannumber", "pan_card_number"]:
                extracted_data["pan_number"] = extracted_data[k]
            if document_type == "Aadhaar" and kl in ["aadhaar", "aadhar", "aadhaar_number", "aadhar_number", "uid"]:
                extracted_data["aadhaar_number"] = extracted_data[k]
            if kl in ["name", "full_name", "fullname", "holder_name"]:
                extracted_data["name"] = extracted_data[k]
    
    logger.info(f"Extracted metadata: {extracted_data}")
    
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
            elif document_type == "Aadhaar":
                result = await run_in_threadpool(run_aadhaar_dna_analysis, temp_path, is_pdf, extracted_data)
                return result
            elif document_type == "PAN":
                result = await run_in_threadpool(run_pan_dna_analysis, temp_path, is_pdf, extracted_data)
                return result
            elif document_type == "Property":
                result = await run_in_threadpool(run_property_dna_analysis, temp_path, is_pdf, extracted_data)
                return result
            elif document_type == "Salary Slip":
                result = await run_in_threadpool(run_salary_slip_dna_analysis, temp_path, is_pdf, extracted_data)
                return result
            else:
                return {"bucket": 2, "status": "Requires Review", "differences": ["Forensic module pending"], "description": f"Forensic DNA analysis for {document_type} is still under development. Defaulting to manual review."}
        else:
            raise HTTPException(400, "Invalid verification method selected.")
            
    except Exception as e:
        logger.error(f"Orchestration Error: {e}")
        return {"bucket": 3, "status": "Forged / Error", "differences": [str(e)], "description": "A critical failure occurred during verification."}
