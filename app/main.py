from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
load_dotenv()

from app.api.routes.verification import router as verification_router
from app.api.routes.orchestration import router as orchestration_router
import uvicorn
import sys
import asyncio

# Required for Playwright to work with FastAPI on Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = FastAPI(
    title="Suraksha Drishti API",
    description="Real-time Document Verification Backend",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev purposes, allow all origins (frontend will be on 5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include our routes
app.include_router(verification_router, prefix="/api/v1")
app.include_router(orchestration_router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Suraksha Drishti Backend API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
