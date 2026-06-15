from fastapi import FastAPI, UploadFile, File
import uvicorn
import os
import shutil
from app.services.agents.salary_slip_agent.main import process_verification

app = FastAPI(title="Suraksha-Drishti API", version="1.0")

@app.post("/verify/salary-slip")
async def verify_salary_slip(file: UploadFile = File(...)):
    """
    Upload a salary slip image to be processed by the 6-Layer DNA Engine.
    """
    # Save the uploaded file temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Run the DNA engine pipeline
        result = process_verification(temp_file_path, is_image=True)
        
        # In a real scenario, you might upload the highlighted image to S3 and return the URL.
        # Here we just return the local absolute path for the demo.
        if result['explainability'].get('highlighted_image_path'):
            result['explainability']['highlighted_image_path'] = os.path.abspath(result['explainability']['highlighted_image_path'])
            
        return result
        
    except Exception as e:
        return {"error": str(e)}
        
    finally:
        # We leave the temp image and the highlighted image so the user can see them,
        # but in production, we would clean up the temp file here.
        pass

if __name__ == "__main__":
    print("Starting Suraksha-Drishti API Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
