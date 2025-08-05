"""
API routes for the LLM Document Processing System
"""

import os
import logging
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.responses import HTMLResponse

from src.models.schemas import (
    ProcessingRequest, ProcessingResponse, DocumentUploadResponse, HealthResponse
)
from src.services.processing_service import ProcessingService
from src.services.universal_document_processor import UniversalDocumentProcessor
from src.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
processing_service = ProcessingService()
document_processor = UniversalDocumentProcessor()
vector_store = VectorStore()


@router.post("/process", response_model=ProcessingResponse)
async def process_query(request: ProcessingRequest):
    """
    Process a natural language query and return structured decision
    
    Example request:
    {
        "query": "46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
        "query_type": "insurance_claim"
    }
    """
    try:
        response = await processing_service.process_query(request)
        return response
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    metadata: str = None
):
    """
    Upload and process a document (PDF, Word, or text file)
    """
    try:
        import json
        import time
        import tempfile
        
        start_time = time.time()
        
        # Validate file type
        allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.eml', '.html'}
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file type: {file_extension}"
            )
        
        # Parse metadata if provided
        doc_metadata = {}
        if metadata:
            try:
                doc_metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid metadata JSON")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Process the document
            chunks = document_processor.process_document(temp_file_path, doc_metadata)
            
            # Add chunks to vector store
            success = vector_store.add_documents(chunks)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to add document to vector store")
            
            processing_time = time.time() - start_time
            
            return DocumentUploadResponse(
                document_id=chunks[0].document_id if chunks else "unknown",
                filename=file.filename,
                status="processed",
                chunks_created=len(chunks),
                processing_time=processing_time
            )
            
        finally:
            # Clean up temporary file
            os.unlink(temp_file_path)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Get system health status"""
    try:
        status = processing_service.get_system_status()
        
        return HealthResponse(
            status=status["status"],
            version="1.0.0",
            components=status.get("components", {})
        )
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats():
    """Get system statistics"""
    try:
        vector_stats = vector_store.get_collection_stats()
        return {
            "vector_store": vector_stats,
            "status": "healthy"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    try:
        success = vector_store.delete_document(document_id)
        
        if success:
            return {"message": f"Document {document_id} deleted successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to delete document")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_class=HTMLResponse)
async def get_interface():
    """Simple web interface for testing the system"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LLM Document Processing System</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .container { max-width: 800px; margin: 0 auto; }
            .form-group { margin: 20px 0; }
            label { display: block; margin-bottom: 5px; font-weight: bold; }
            input, textarea, select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; }
            button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; }
            button:hover { background: #0056b3; }
            .result { margin-top: 20px; padding: 20px; background: #f8f9fa; border-radius: 4px; }
            .error { background: #f8d7da; color: #721c24; }
            .success { background: #d4edda; color: #155724; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>LLM Document Processing System</h1>
            
            <div class="form-group">
                <h2>Process Query</h2>
                <label for="query">Natural Language Query:</label>
                <textarea id="query" rows="3" placeholder="e.g., 46-year-old male, knee surgery in Pune, 3-month-old insurance policy"></textarea>
                
                <label for="queryType">Query Type:</label>
                <select id="queryType">
                    <option value="insurance_claim">Insurance Claim</option>
                    <option value="legal_compliance">Legal Compliance</option>
                    <option value="contract_review">Contract Review</option>
                    <option value="hr_policy">HR Policy</option>
                    <option value="general">General</option>
                </select>
                
                <button onclick="processQuery()">Process Query</button>
            </div>
            
            <div class="form-group">
                <h2>Upload Document</h2>
                <label for="file">Select File (PDF, Word, Text):</label>
                <input type="file" id="file" accept=".pdf,.docx,.doc,.txt,.eml,.html">
                <button onclick="uploadDocument()">Upload Document</button>
            </div>
            
            <div id="result" class="result" style="display: none;"></div>
        </div>
        
        <script>
            async function processQuery() {
                const query = document.getElementById('query').value;
                const queryType = document.getElementById('queryType').value;
                const resultDiv = document.getElementById('result');
                
                if (!query.trim()) {
                    showResult('Please enter a query', 'error');
                    return;
                }
                
                try {
                    const response = await fetch('/api/v1/process', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ query, query_type: queryType })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showResult(JSON.stringify(data, null, 2), 'success');
                    } else {
                        showResult('Error: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showResult('Error: ' + error.message, 'error');
                }
            }
            
            async function uploadDocument() {
                const fileInput = document.getElementById('file');
                const file = fileInput.files[0];
                
                if (!file) {
                    showResult('Please select a file', 'error');
                    return;
                }
                
                const formData = new FormData();
                formData.append('file', file);
                
                try {
                    const response = await fetch('/api/v1/upload', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        showResult(JSON.stringify(data, null, 2), 'success');
                    } else {
                        showResult('Error: ' + data.detail, 'error');
                    }
                } catch (error) {
                    showResult('Error: ' + error.message, 'error');
                }
            }
            
            function showResult(message, type) {
                const resultDiv = document.getElementById('result');
                resultDiv.innerHTML = '<pre>' + message + '</pre>';
                resultDiv.className = 'result ' + type;
                resultDiv.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return html_content
