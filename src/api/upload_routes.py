"""
File upload API routes for dynamic document processing
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import JSONResponse

from src.services.universal_document_processor import UniversalDocumentProcessor
from src.services.vector_store import VectorStore
from src.models.schemas import DocumentChunk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["Document Upload"])

# Initialize services
document_processor = UniversalDocumentProcessor()
vector_store = VectorStore()


@router.post("/document")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process any document type
    
    Supports: PDF, Word, Excel, PowerPoint, Text, HTML, JSON, CSV, etc.
    """
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (limit to 50MB)
        max_size = 50 * 1024 * 1024  # 50MB
        file_content = await file.read()
        
        if len(file_content) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        
        logger.info(f"📄 Processing uploaded file: {file.filename} ({len(file_content)} bytes)")
        
        # Process the document
        chunks = document_processor.process_file(file.filename, file_content)
        
        if not chunks:
            raise HTTPException(status_code=422, detail="Failed to extract text from document")
        
        # Add chunks to vector database
        added_chunks = []
        for chunk in chunks:
            try:
                vector_store.add_document(chunk)
                added_chunks.append({
                    'chunk_id': chunk.chunk_id,
                    'content_preview': chunk.content[:100] + "..." if len(chunk.content) > 100 else chunk.content,
                    'metadata': chunk.metadata
                })
            except Exception as e:
                logger.warning(f"Failed to add chunk {chunk.chunk_id}: {e}")
        
        logger.info(f"✅ Successfully processed {file.filename}: {len(added_chunks)} chunks added")
        
        return {
            "status": "success",
            "message": f"Document '{file.filename}' processed successfully",
            "filename": file.filename,
            "file_size": len(file_content),
            "mime_type": document_processor._detect_file_type(file.filename, file_content),
            "chunks_created": len(chunks),
            "chunks_added": len(added_chunks),
            "chunks": added_chunks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error processing {file.filename}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


@router.post("/multiple")
async def upload_multiple_documents(files: List[UploadFile] = File(...)):
    """
    Upload and process multiple documents at once
    """
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 files allowed per upload")
    
    results = []
    total_chunks = 0
    
    for file in files:
        try:
            # Process each file
            file_content = await file.read()
            
            if len(file_content) > 50 * 1024 * 1024:  # 50MB limit
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": "File too large (max 50MB)"
                })
                continue
            
            chunks = document_processor.process_file(file.filename, file_content)
            
            if not chunks:
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "error": "Failed to extract text from document"
                })
                continue
            
            # Add to vector database
            added_count = 0
            for chunk in chunks:
                try:
                    vector_store.add_document(chunk)
                    added_count += 1
                except Exception as e:
                    logger.warning(f"Failed to add chunk from {file.filename}: {e}")
            
            results.append({
                "filename": file.filename,
                "status": "success",
                "file_size": len(file_content),
                "chunks_created": len(chunks),
                "chunks_added": added_count
            })
            
            total_chunks += added_count
            
        except Exception as e:
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e)
            })
    
    successful_files = [r for r in results if r["status"] == "success"]
    
    return {
        "status": "completed",
        "message": f"Processed {len(successful_files)}/{len(files)} files successfully",
        "total_chunks_added": total_chunks,
        "results": results
    }


@router.get("/supported-types")
async def get_supported_file_types():
    """
    Get list of supported file types
    """
    return {
        "supported_types": document_processor.get_supported_types(),
        "common_extensions": [
            ".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt",
            ".txt", ".md", ".html", ".htm", ".json", ".csv"
        ],
        "description": "Upload any document type for automatic text extraction and indexing"
    }


@router.delete("/clear")
async def clear_uploaded_documents():
    """
    Clear all uploaded documents from the vector database
    (keeps sample documents)
    """
    try:
        # Get all documents
        collection = vector_store.collection
        all_docs = collection.get(include=['metadatas'])
        
        # Find uploaded documents
        uploaded_ids = []
        for i, metadata in enumerate(all_docs['metadatas']):
            if metadata.get('source') == 'uploaded_document':
                uploaded_ids.append(all_docs['ids'][i])
        
        if uploaded_ids:
            collection.delete(ids=uploaded_ids)
            logger.info(f"🗑️ Cleared {len(uploaded_ids)} uploaded document chunks")
        
        return {
            "status": "success",
            "message": f"Cleared {len(uploaded_ids)} uploaded document chunks",
            "cleared_count": len(uploaded_ids)
        }
        
    except Exception as e:
        logger.error(f"❌ Error clearing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing documents: {str(e)}")


@router.get("/stats")
async def get_upload_stats():
    """
    Get statistics about uploaded documents
    """
    try:
        collection = vector_store.collection
        all_docs = collection.get(include=['metadatas'])
        
        # Count documents by source
        sample_count = 0
        uploaded_count = 0
        uploaded_files = set()
        
        for metadata in all_docs['metadatas']:
            if metadata.get('source') == 'uploaded_document':
                uploaded_count += 1
                uploaded_files.add(metadata.get('filename', 'unknown'))
            else:
                sample_count += 1
        
        return {
            "total_chunks": len(all_docs['ids']),
            "sample_documents": sample_count,
            "uploaded_documents": uploaded_count,
            "unique_uploaded_files": len(uploaded_files),
            "uploaded_filenames": list(uploaded_files)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting stats: {str(e)}")
