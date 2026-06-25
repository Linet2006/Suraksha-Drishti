from fastapi import FastAPI
from app.api.routes import verification
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

# Include our routes
app.include_router(verification.router, prefix="/api/v1")

@app.get("/")
def read_root():
    return {"message": "Welcome to Suraksha Drishti Backend API"}

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
