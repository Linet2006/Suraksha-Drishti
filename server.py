from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
import shutil
from app.services.dna_comparison.salary_slip_dna.main import process_verification
from app.services.dna_comparison.main import process_kyc_verification
from app.services.dna_comparison.kyc_explainability import generate_kyc_overlay

app = FastAPI(title="Suraksha-Drishti API", version="1.0")

# Mount the outputs directory so users can view the heatmaps in their browser
os.makedirs("data/outputs", exist_ok=True)
app.mount("/outputs", StaticFiles(directory="data/outputs"), name="outputs")

@app.post("/verify/salary-slip")
async def verify_salary_slip(file: UploadFile = File(...)):
    """
    Upload a salary slip image to be processed by the 6-Layer DNA Engine.
    """
    # Save the uploaded file temporarily to the outputs directory
    temp_file_path = f"data/outputs/salaryslip/temp_{file.filename}"
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Guarantee OpenCV compatibility (convert PDF/AVIF to standard JPEG)
        from app.services.dna_comparison.main import ensure_image_format
        temp_file_path = ensure_image_format(temp_file_path)
        
        # Run the DNA engine pipeline
        result = process_verification(temp_file_path, is_image=True)
        
        # Return the Visual Proof URL just like the KYC engine
        if result['explainability'].get('highlighted_image_path'):
            filename = os.path.basename(result['explainability']['highlighted_image_path'])
            result['explainability']['Visual Proof'] = f"http://localhost:8000/outputs/salaryslip/{filename}"
            
        return result
        
    except Exception as e:
        return {"error": str(e)}
        
    finally:
        import glob
        cleanup_patterns = [
            "data/outputs/salaryslip/temp_*",
            "data/outputs/salaryslip/ela_heatmap_*"
        ]
        for pattern in cleanup_patterns:
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                except:
                    pass

@app.post("/verify/property-paper")
async def verify_property_paper(file: UploadFile = File(...)):
    """
    Upload a Property Paper (Sale Deed) to verify against the local SQLite Registry
    to detect 'Already Sold' or 'Multiple Mortgage' fraud.
    """
    # Save the uploaded file temporarily
    temp_file_path = f"data/outputs/property/temp_{file.filename}"
    os.makedirs(os.path.dirname(temp_file_path), exist_ok=True)
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        from app.services.dna_comparison.main import ensure_image_format
        temp_file_path = ensure_image_format(temp_file_path)
        
        from app.services.dna_comparison.property_dna import process_property_verification
        result = process_property_verification(temp_file_path)
        return result
        
    except Exception as e:
        return {"error": str(e)}
        
    finally:
        import glob
        for filepath in glob.glob("data/outputs/property/temp_*"):
            try:
                os.remove(filepath)
            except:
                pass

@app.post("/verify/kyc")
async def verify_kyc(
    aadhaar_file: UploadFile = File(None),
    pan_file: UploadFile = File(None)
):
    """
    Upload Aadhaar and/or PAN card images for algorithmic DNA validation.
    """
    aadhaar_path = None
    pan_path = None
    
    os.makedirs("data/outputs/kyc", exist_ok=True)
    
    if aadhaar_file:
        aadhaar_path = f"data/outputs/kyc/temp_aadhaar_{aadhaar_file.filename}"
        with open(aadhaar_path, "wb") as buffer:
            shutil.copyfileobj(aadhaar_file.file, buffer)
            
    if pan_file:
        pan_path = f"data/outputs/kyc/temp_pan_{pan_file.filename}"
        with open(pan_path, "wb") as buffer:
            shutil.copyfileobj(pan_file.file, buffer)
            
    try:
        from app.services.dna_comparison.main import ensure_image_format
        aadhaar_path = ensure_image_format(aadhaar_path)
        pan_path = ensure_image_format(pan_path)
        
        raw_result = process_kyc_verification(aadhaar_path=aadhaar_path, pan_path=pan_path)
        
        # Build a highly simplified summary for the user
        simple_summary = {}
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        
        if "aadhaar_engine" in raw_result:
            a_res = raw_result["aadhaar_engine"]
            
            flags = a_res.get("flags", [])
            flags.sort(key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 2))
            
            # Generate the bounding-box explainability overlay!
            a_proof = generate_kyc_overlay(aadhaar_path, flags, document_type="AADHAAR")
            
            explanation = "Document is genuine and untampered."
            if not a_res.get("verified") and flags:
                explanation = " | ".join([f.get("description", f.get("flag", "Unknown Error")) for f in flags[:2]])
                
            simple_summary["Aadhaar"] = {
                "Status": "✅ VERIFIED (Genuine)" if a_res.get("verified") else "❌ FAILED",
                "Trust Score": f"{100 - a_res.get('risk_score', 100)}%",
                "Explanation": explanation,
                "Visual Proof": f"http://localhost:8000/outputs/kyc/{a_proof}" if a_proof else "N/A"
            }
            
        if "pan_engine" in raw_result:
            p_res = raw_result["pan_engine"]
            
            flags = p_res.get("flags", [])
            flags.sort(key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 2))
            
            # Generate the bounding-box explainability overlay!
            p_proof = generate_kyc_overlay(pan_path, flags, document_type="PAN")
            
            explanation = "Document is genuine and untampered."
            if not p_res.get("verified") and flags:
                explanation = " | ".join([f.get("description", f.get("flag", "Unknown Error")) for f in flags[:2]])
                
            simple_summary["PAN"] = {
                "Status": "✅ VERIFIED (Genuine)" if p_res.get("verified") else "❌ FAILED",
                "Trust Score": f"{100 - p_res.get('risk_score', 100)}%",
                "Explanation": explanation,
                "Visual Proof": f"http://localhost:8000/outputs/kyc/{p_proof}" if p_proof else "N/A"
            }
            
        if "cross_verification" in raw_result:
            c_res = raw_result["cross_verification"]
            
            cross_flags = c_res.get("all_flags", [])
            cross_flags.sort(key=lambda x: severity_order.get(x.get("severity", "MEDIUM"), 2))
            overall_explanation = "Identity successfully verified across all sources."
            if not c_res.get("identity_verified") and cross_flags:
                overall_explanation = "FRAUD DETECTED: " + " | ".join([f.get("description", f.get("flag", "Unknown Error")) for f in cross_flags[:3]])
                
            simple_summary["Final Decision"] = c_res.get("decision", "UNKNOWN")
            simple_summary["Overall Explanation"] = overall_explanation
            
        # Return ONLY the simple summary as requested by the user
        return simple_summary
        
    except Exception as e:
        return {"error": str(e)}
        
    finally:
        # CLEANUP: Delete all temporary files, converted images, and unused ELA heatmaps
        # We only want to keep the final 'proof_' visual overlays for the user!
        import glob
        cleanup_patterns = [
            "data/outputs/kyc/temp_*",
            "data/outputs/kyc/ela_heatmap_*"
        ]
        for pattern in cleanup_patterns:
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                except:
                    pass

if __name__ == "__main__":
    print("Starting Suraksha-Drishti API Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
