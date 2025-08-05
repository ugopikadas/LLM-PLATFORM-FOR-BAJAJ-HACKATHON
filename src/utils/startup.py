"""
System initialization and startup utilities
"""

import os
import logging
import asyncio
from typing import List, Dict, Any

from src.services.universal_document_processor import UniversalDocumentProcessor
from src.services.vector_store import VectorStore
from src.core.config import settings

logger = logging.getLogger(__name__)


async def initialize_system():
    """Initialize the system with sample data and configurations"""
    logger.info("🚀 Initializing LLM Document Processing System...")
    
    try:
        # Initialize services
        document_processor = UniversalDocumentProcessor()
        vector_store = VectorStore()
        
        # Check if vector database already has data
        stats = vector_store.get_collection_stats()
        if stats.get("total_chunks", 0) > 0:
            logger.info(f"✅ Vector database already contains {stats['total_chunks']} chunks")
            return
        
        # Load sample documents
        await load_sample_documents(document_processor, vector_store)
        
        # Create mock embeddings if OpenAI API is not available
        await ensure_sample_data(vector_store)
        
        logger.info("✅ System initialization completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ System initialization failed: {str(e)}")
        # Continue startup even if initialization fails
        logger.info("⚠️ Continuing startup without sample data...")


async def load_sample_documents(processor: UniversalDocumentProcessor, vector_store: VectorStore):
    """Load sample policy documents into the system"""
    
    sample_files = [
        "data/sample_policies/health_insurance_policy.txt",
        "data/sample_policies/corporate_policy.txt"
    ]
    
    total_chunks = 0
    
    for file_path in sample_files:
        if os.path.exists(file_path):
            try:
                logger.info(f"📄 Processing {file_path}...")
                
                # Process document into chunks
                chunks = processor.process_file(file_path)
                
                # Try to add to vector store (this will attempt to generate embeddings)
                success = vector_store.add_documents(chunks)
                
                if success:
                    total_chunks += len(chunks)
                    logger.info(f"✅ Added {len(chunks)} chunks from {os.path.basename(file_path)}")
                else:
                    logger.warning(f"⚠️ Failed to add embeddings for {os.path.basename(file_path)}")
                    # Add chunks with mock embeddings as fallback
                    await add_chunks_with_mock_embeddings(chunks, vector_store)
                    total_chunks += len(chunks)
                    
            except Exception as e:
                logger.error(f"❌ Error processing {file_path}: {str(e)}")
        else:
            logger.warning(f"⚠️ Sample file not found: {file_path}")
    
    if total_chunks > 0:
        logger.info(f"📊 Total chunks loaded: {total_chunks}")
    else:
        logger.warning("⚠️ No sample documents were loaded")


async def add_chunks_with_mock_embeddings(chunks: List, vector_store: VectorStore):
    """Add chunks with mock embeddings when OpenAI API is not available"""
    
    try:
        # Create mock embeddings (1536 dimensions for OpenAI ada-002 compatibility)
        import random
        
        for chunk in chunks:
            # Generate consistent mock embedding based on content hash
            content_hash = hash(chunk.content) % 1000000
            random.seed(content_hash)  # Consistent embeddings for same content
            
            # Create mock embedding vector
            mock_embedding = [random.uniform(-1, 1) for _ in range(1536)]
            chunk.embedding = mock_embedding
        
        # Add to ChromaDB directly with mock embeddings
        if hasattr(vector_store, 'collection') and vector_store.collection:
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.content for chunk in chunks]
            embeddings = [chunk.embedding for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = {
                    "document_id": chunk.document_id,
                    **chunk.metadata
                }
                metadatas.append(metadata)
            
            vector_store.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Added {len(chunks)} chunks with mock embeddings")
            
    except Exception as e:
        logger.error(f"❌ Error adding mock embeddings: {str(e)}")


async def ensure_sample_data(vector_store: VectorStore):
    """Ensure the system has some sample data for testing"""
    
    try:
        stats = vector_store.get_collection_stats()
        total_chunks = stats.get("total_chunks", 0)
        
        if total_chunks == 0:
            logger.info("📝 Creating minimal sample data for testing...")
            await create_minimal_sample_data(vector_store)
        
    except Exception as e:
        logger.error(f"❌ Error ensuring sample data: {str(e)}")


async def create_minimal_sample_data(vector_store: VectorStore):
    """Create minimal sample data when no documents are available"""
    
    try:
        from src.models.schemas import DocumentChunk
        import uuid
        import random
        
        # Create sample insurance policy chunks
        sample_chunks = [
            {
                "content": "SECTION 3: COVERED PROCEDURES - Orthopedic surgeries including knee surgery, hip replacement, and spine surgery are covered under this policy. Coverage amount: Up to ₹2,00,000 per procedure.",
                "metadata": {"section": "COVERED_PROCEDURES", "document_type": "insurance_policy"}
            },
            {
                "content": "SECTION 2: ELIGIBILITY - Age Requirements: Primary insured 18-65 years at policy inception. Waiting Periods: 12 months waiting period for knee surgery and hip replacement.",
                "metadata": {"section": "ELIGIBILITY", "document_type": "insurance_policy"}
            },
            {
                "content": "SECTION 4: GEOGRAPHICAL COVERAGE - Metropolitan cities (Mumbai, Delhi, Bangalore, Chennai, Pune, Hyderabad): Full coverage. Coverage available at all network hospitals across India.",
                "metadata": {"section": "GEOGRAPHICAL_COVERAGE", "document_type": "insurance_policy"}
            },
            {
                "content": "SECTION 1.2: LEAVE POLICIES - Maternity leave: 26 weeks paid leave as per government regulations. Sick leave: 12 days per year with medical certificate required for 3+ consecutive days.",
                "metadata": {"section": "LEAVE_POLICIES", "document_type": "hr_policy"}
            },
            {
                "content": "SECTION 2.1: SALARY STRUCTURE - Performance bonus: Up to 20% of annual salary for exceptional performance. Annual salary review in April based on performance.",
                "metadata": {"section": "SALARY_STRUCTURE", "document_type": "hr_policy"}
            }
        ]
        
        # Convert to DocumentChunk objects
        document_chunks = []
        document_id = str(uuid.uuid4())
        
        for i, sample in enumerate(sample_chunks):
            chunk = DocumentChunk(
                chunk_id=str(uuid.uuid4()),
                document_id=document_id,
                content=sample["content"],
                metadata={
                    **sample["metadata"],
                    "chunk_index": i,
                    "source": "system_generated"
                }
            )
            
            # Add mock embedding
            content_hash = hash(chunk.content) % 1000000
            random.seed(content_hash)
            chunk.embedding = [random.uniform(-1, 1) for _ in range(1536)]
            
            document_chunks.append(chunk)
        
        # Add to vector store
        if hasattr(vector_store, 'collection') and vector_store.collection:
            ids = [chunk.chunk_id for chunk in document_chunks]
            documents = [chunk.content for chunk in document_chunks]
            embeddings = [chunk.embedding for chunk in document_chunks]
            metadatas = [chunk.metadata for chunk in document_chunks]
            
            vector_store.collection.add(
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✅ Created {len(document_chunks)} sample chunks for testing")
        
    except Exception as e:
        logger.error(f"❌ Error creating minimal sample data: {str(e)}")


def log_system_status():
    """Log current system configuration and status"""
    
    logger.info("📋 System Configuration:")
    logger.info(f"   • OpenAI API Key: {'✅ Configured' if settings.OPENAI_API_KEY else '❌ Missing'}")
    logger.info(f"   • LLM Model: {settings.LLM_MODEL}")
    logger.info(f"   • Embedding Model: {settings.EMBEDDING_MODEL}")
    logger.info(f"   • Vector DB Path: {settings.VECTOR_DB_PATH}")
    logger.info(f"   • Debug Mode: {settings.DEBUG}")
    logger.info(f"   • Server: http://{settings.APP_HOST}:{settings.APP_PORT}")
