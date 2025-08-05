"""
API routes for viewing and managing document chunks
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.services.vector_store import VectorStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chunks", tags=["Document Chunks"])

# Initialize services
vector_store = VectorStore()


@router.get("/")
async def list_chunks(
    limit: int = Query(default=50, description="Maximum number of chunks to return"),
    offset: int = Query(default=0, description="Number of chunks to skip"),
    source: Optional[str] = Query(default=None, description="Filter by source")
):
    """
    Get list of all document chunks with metadata
    """
    try:
        # Get all documents
        docs = vector_store.collection.get(include=['documents', 'metadatas'])
        
        if 'documents' not in docs:
            return {
                "total_chunks": 0,
                "chunks": [],
                "sources": []
            }
        
        documents = docs['documents']
        metadatas = docs.get('metadatas', [])
        ids = docs.get('ids', [])
        
        # Filter by source if specified
        filtered_indices = []
        if source:
            for i, metadata in enumerate(metadatas):
                if metadata.get('source') == source:
                    filtered_indices.append(i)
        else:
            filtered_indices = list(range(len(documents)))
        
        # Apply pagination
        start_idx = offset
        end_idx = min(offset + limit, len(filtered_indices))
        paginated_indices = filtered_indices[start_idx:end_idx]
        
        # Build response
        chunks = []
        for i in paginated_indices:
            chunk_data = {
                "chunk_id": ids[i] if i < len(ids) else f"chunk_{i}",
                "content": documents[i],
                "content_preview": documents[i][:200] + ("..." if len(documents[i]) > 200 else ""),
                "content_length": len(documents[i]),
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "index": i
            }
            chunks.append(chunk_data)
        
        # Get unique sources
        sources = list(set(metadata.get('source', 'unknown') for metadata in metadatas))
        
        return {
            "total_chunks": len(filtered_indices),
            "chunks": chunks,
            "sources": sources,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "has_more": end_idx < len(filtered_indices)
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error listing chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing chunks: {str(e)}")


@router.get("/{chunk_index}")
async def get_chunk(chunk_index: int):
    """
    Get a specific chunk by its index
    """
    try:
        # Get all documents
        docs = vector_store.collection.get(include=['documents', 'metadatas'])
        
        if 'documents' not in docs:
            raise HTTPException(status_code=404, detail="No chunks found")
        
        documents = docs['documents']
        metadatas = docs.get('metadatas', [])
        ids = docs.get('ids', [])
        
        if chunk_index < 0 or chunk_index >= len(documents):
            raise HTTPException(status_code=404, detail="Chunk not found")
        
        return {
            "chunk_id": ids[chunk_index] if chunk_index < len(ids) else f"chunk_{chunk_index}",
            "content": documents[chunk_index],
            "content_length": len(documents[chunk_index]),
            "metadata": metadatas[chunk_index] if chunk_index < len(metadatas) else {},
            "index": chunk_index
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting chunk {chunk_index}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting chunk: {str(e)}")


@router.get("/search/content")
async def search_chunks(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, description="Maximum number of results")
):
    """
    Search chunks by content
    """
    try:
        # Get all documents
        docs = vector_store.collection.get(include=['documents', 'metadatas'])
        
        if 'documents' not in docs:
            return {"results": []}
        
        documents = docs['documents']
        metadatas = docs.get('metadatas', [])
        ids = docs.get('ids', [])
        
        # Simple text search
        query_lower = query.lower()
        results = []
        
        for i, content in enumerate(documents):
            if query_lower in content.lower():
                # Calculate simple relevance score
                score = content.lower().count(query_lower) / len(content.split())
                
                results.append({
                    "chunk_id": ids[i] if i < len(ids) else f"chunk_{i}",
                    "content": content,
                    "content_preview": content[:200] + ("..." if len(content) > 200 else ""),
                    "metadata": metadatas[i] if i < len(metadatas) else {},
                    "index": i,
                    "relevance_score": score
                })
        
        # Sort by relevance score
        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        
        return {
            "query": query,
            "total_results": len(results),
            "results": results[:limit]
        }
        
    except Exception as e:
        logger.error(f"❌ Error searching chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching chunks: {str(e)}")


@router.get("/viewer", response_class=HTMLResponse)
async def chunk_viewer():
    """
    Web-based chunk viewer interface
    """
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Document Chunks Viewer</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 15px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                color: white;
                padding: 30px;
                text-align: center;
            }
            .content {
                padding: 30px;
            }
            .search-box {
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
            }
            .search-box input {
                flex: 1;
                padding: 12px;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                font-size: 16px;
            }
            .search-box button {
                padding: 12px 24px;
                background: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }
            .filters {
                margin-bottom: 20px;
                display: flex;
                gap: 10px;
                align-items: center;
            }
            .filters select {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .chunk {
                border: 1px solid #e9ecef;
                border-radius: 10px;
                margin-bottom: 20px;
                overflow: hidden;
            }
            .chunk-header {
                background: #f8f9fa;
                padding: 15px;
                border-bottom: 1px solid #e9ecef;
                display: flex;
                justify-content: between;
                align-items: center;
            }
            .chunk-title {
                font-weight: bold;
                color: #495057;
            }
            .chunk-meta {
                font-size: 0.9em;
                color: #6c757d;
                margin-top: 5px;
            }
            .chunk-content {
                padding: 20px;
                background: white;
                white-space: pre-wrap;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.5;
                max-height: 300px;
                overflow-y: auto;
            }
            .chunk-content.collapsed {
                max-height: 100px;
            }
            .expand-btn {
                background: #28a745;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                font-size: 12px;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
            }
            .stat-value {
                font-size: 2em;
                font-weight: bold;
                color: #007bff;
            }
            .stat-label {
                color: #6c757d;
                margin-top: 5px;
            }
            .loading {
                text-align: center;
                padding: 40px;
            }
            .spinner {
                border: 4px solid #f3f3f3;
                border-top: 4px solid #007bff;
                border-radius: 50%;
                width: 40px;
                height: 40px;
                animation: spin 1s linear infinite;
                margin: 0 auto 20px;
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📄 Document Chunks Viewer</h1>
                <p>View and search through all document chunks in the vector database</p>
            </div>
            
            <div class="content">
                <div class="stats" id="stats">
                    <!-- Stats will be loaded here -->
                </div>
                
                <div class="search-box">
                    <input type="text" id="searchInput" placeholder="Search chunks by content...">
                    <button onclick="searchChunks()">🔍 Search</button>
                    <button onclick="loadAllChunks()">📋 Show All</button>
                </div>
                
                <div class="filters">
                    <label>Filter by source:</label>
                    <select id="sourceFilter" onchange="filterBySource()">
                        <option value="">All Sources</option>
                    </select>
                </div>
                
                <div id="chunks">
                    <div class="loading">
                        <div class="spinner"></div>
                        <p>Loading chunks...</p>
                    </div>
                </div>
            </div>
        </div>

        <script>
            let allChunks = [];
            let currentChunks = [];

            async function loadAllChunks() {
                try {
                    document.getElementById('chunks').innerHTML = '<div class="loading"><div class="spinner"></div><p>Loading chunks...</p></div>';
                    
                    const response = await fetch('/api/v1/chunks/?limit=1000');
                    const data = await response.json();
                    
                    allChunks = data.chunks;
                    currentChunks = allChunks;
                    
                    updateStats(data);
                    updateSourceFilter(data.sources);
                    displayChunks(currentChunks);
                    
                } catch (error) {
                    document.getElementById('chunks').innerHTML = '<div class="error">Error loading chunks: ' + error.message + '</div>';
                }
            }

            function updateStats(data) {
                const statsHtml = `
                    <div class="stat-card">
                        <div class="stat-value">${data.total_chunks}</div>
                        <div class="stat-label">Total Chunks</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${data.sources.length}</div>
                        <div class="stat-label">Sources</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${Math.round(data.chunks.reduce((sum, chunk) => sum + chunk.content_length, 0) / data.chunks.length)}</div>
                        <div class="stat-label">Avg Chunk Size</div>
                    </div>
                `;
                document.getElementById('stats').innerHTML = statsHtml;
            }

            function updateSourceFilter(sources) {
                const select = document.getElementById('sourceFilter');
                select.innerHTML = '<option value="">All Sources</option>';
                sources.forEach(source => {
                    select.innerHTML += `<option value="${source}">${source}</option>`;
                });
            }

            function displayChunks(chunks) {
                if (chunks.length === 0) {
                    document.getElementById('chunks').innerHTML = '<div class="no-results">No chunks found</div>';
                    return;
                }

                let html = '';
                chunks.forEach((chunk, index) => {
                    const isLong = chunk.content.length > 500;
                    html += `
                        <div class="chunk">
                            <div class="chunk-header">
                                <div>
                                    <div class="chunk-title">Chunk ${chunk.index + 1}: ${chunk.metadata.filename || 'Unknown'}</div>
                                    <div class="chunk-meta">
                                        Source: ${chunk.metadata.source || 'unknown'} | 
                                        Section: ${chunk.metadata.section || 'N/A'} | 
                                        Length: ${chunk.content_length} chars
                                        ${chunk.relevance_score ? ` | Relevance: ${(chunk.relevance_score * 100).toFixed(1)}%` : ''}
                                    </div>
                                </div>
                                ${isLong ? `<button class="expand-btn" onclick="toggleChunk(${index})">Expand</button>` : ''}
                            </div>
                            <div class="chunk-content ${isLong ? 'collapsed' : ''}" id="content-${index}">
${chunk.content}
                            </div>
                        </div>
                    `;
                });
                document.getElementById('chunks').innerHTML = html;
            }

            function toggleChunk(index) {
                const content = document.getElementById(`content-${index}`);
                const btn = content.parentElement.querySelector('.expand-btn');
                
                if (content.classList.contains('collapsed')) {
                    content.classList.remove('collapsed');
                    btn.textContent = 'Collapse';
                } else {
                    content.classList.add('collapsed');
                    btn.textContent = 'Expand';
                }
            }

            async function searchChunks() {
                const query = document.getElementById('searchInput').value.trim();
                if (!query) {
                    loadAllChunks();
                    return;
                }

                try {
                    document.getElementById('chunks').innerHTML = '<div class="loading"><div class="spinner"></div><p>Searching...</p></div>';
                    
                    const response = await fetch(`/api/v1/chunks/search/content?query=${encodeURIComponent(query)}&limit=50`);
                    const data = await response.json();
                    
                    currentChunks = data.results;
                    displayChunks(currentChunks);
                    
                } catch (error) {
                    document.getElementById('chunks').innerHTML = '<div class="error">Error searching: ' + error.message + '</div>';
                }
            }

            function filterBySource() {
                const selectedSource = document.getElementById('sourceFilter').value;
                if (!selectedSource) {
                    currentChunks = allChunks;
                } else {
                    currentChunks = allChunks.filter(chunk => chunk.metadata.source === selectedSource);
                }
                displayChunks(currentChunks);
            }

            // Handle Enter key in search box
            document.getElementById('searchInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchChunks();
                }
            });

            // Load chunks on page load
            loadAllChunks();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
