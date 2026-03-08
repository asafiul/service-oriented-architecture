from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import os

PORT = int(os.getenv("PORT", "8001"))

app = FastAPI(title="User Service", version="1.0.0")

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    service: str

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="OK",
        timestamp=datetime.now().isoformat(),
        service="User Service"
    )

@app.get("/")
async def root():
    """Service information"""
    return {
        "service": "User Service",
        "version": "1.0.0",
        "description": "Service for managing users and authentication"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
