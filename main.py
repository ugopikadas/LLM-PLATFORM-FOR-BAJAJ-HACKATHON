"""
Main entry point for the LLM Document Processing System
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os
import logging
import asyncio

from src.api.routes import router
from src.core.config import settings
from src.utils.startup import initialize_system

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Create FastAPI app
app = FastAPI(
    title="LLM Document Processing System",
    description="A system for processing natural language queries against unstructured documents",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1")

# Include upload routes
from src.api.upload_routes import router as upload_router
app.include_router(upload_router)

# Include chunk viewer routes
from src.api.chunk_routes import router as chunk_router
app.include_router(chunk_router)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Serve the main web interface"""
    from fastapi.responses import FileResponse
    return FileResponse('static/index.html')

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    """Initialize system with sample data on startup"""
    await initialize_system()

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.DEBUG
    )
