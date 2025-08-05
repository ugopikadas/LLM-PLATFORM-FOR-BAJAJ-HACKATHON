"""
Vector database and semantic search service
"""

import os
import logging
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings as ChromaSettings
import numpy as np

from src.models.schemas import DocumentChunk, RetrievedClause, StructuredQuery
from src.core.config import settings
from src.services.llm_client import LLMClientFactory

logger = logging.getLogger(__name__)


class VectorStore:
    """Handles vector storage and semantic search operations"""
    
    def __init__(self):
        self.llm_client = LLMClientFactory.create_client()
        self.chroma_client = None
        self.collection = None
        self._initialize_chroma()
    
    def _initialize_chroma(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create vector database directory if it doesn't exist
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=settings.VECTOR_DB_PATH,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name="document_chunks",
                metadata={"description": "Document chunks for semantic search"}
            )
            
            logger.info("ChromaDB initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ChromaDB: {str(e)}")
            raise
    
    def add_documents(self, chunks: List[DocumentChunk]) -> bool:
        """
        Add document chunks to the vector store
        
        Args:
            chunks: List of DocumentChunk objects to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not chunks:
                return True
            
            # Generate embeddings for chunks
            texts = [chunk.content for chunk in chunks]
            embeddings = self._generate_embeddings(texts)
            
            # Prepare data for ChromaDB
            ids = [chunk.chunk_id for chunk in chunks]
            metadatas = []
            
            for chunk in chunks:
                metadata = {
                    "document_id": chunk.document_id,
                    **chunk.metadata
                }
                metadatas.append(metadata)
            
            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Added {len(chunks)} chunks to vector store")
            return True
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {str(e)}")
            return False
    
    def search_similar(self, query: StructuredQuery, max_results: int = None) -> List[RetrievedClause]:
        """
        Search for similar document chunks based on query

        Args:
            query: Structured query object
            max_results: Maximum number of results to return

        Returns:
            List of RetrievedClause objects
        """
        try:
            max_results = max_results or settings.MAX_RESULTS

            # Check if LLM client is available for embeddings
            try:
                # Try to generate embeddings
                query_embedding = self._generate_embeddings([query.original_query])[0]

                # If embeddings are all zeros or very small, use keyword search
                if all(abs(x) < 0.001 for x in query_embedding):
                    logger.info("🔄 Embeddings too small, using keyword-based search...")
                    return self._keyword_search(query, max_results)

            except Exception as e:
                logger.warning(f"LLM embeddings not available: {str(e)}")
                logger.info("🔄 Using keyword-based search fallback...")
                return self._keyword_search(query, max_results)

            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=max_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Convert results to RetrievedClause objects
            clauses = []
            if results['documents'] and results['documents'][0]:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Convert distance to similarity score (ChromaDB uses cosine distance)
                    similarity_score = 1.0 - distance

                    # Filter by similarity threshold
                    if similarity_score >= settings.SIMILARITY_THRESHOLD:
                        clause = RetrievedClause(
                            clause_id=results['ids'][0][i],
                            document_id=metadata.get('document_id', ''),
                            content=doc,
                            similarity_score=similarity_score,
                            metadata=metadata,
                            section=metadata.get('section', None)
                        )
                        clauses.append(clause)

            # If vector search found no results, try keyword search as fallback
            if not clauses:
                logger.info("🔄 Vector search found no results, trying keyword search...")
                return self._keyword_search(query, max_results)

            logger.info(f"Found {len(clauses)} relevant clauses for query")
            return clauses
            
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts using LLM client or fallback"""
        try:
            embeddings = self.llm_client.generate_embeddings(texts)
            logger.info(f"✅ Generated {len(embeddings)} LLM embeddings")
            return embeddings

        except Exception as e:
            logger.warning(f"LLM embeddings failed: {str(e)}")
            logger.info("🔄 Using fallback embeddings...")
            return self._generate_fallback_embeddings(texts)

    def _generate_fallback_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate simple hash-based embeddings as fallback"""
        import hashlib
        import random

        embeddings = []
        for text in texts:
            # Create consistent embedding based on text content
            text_hash = hashlib.md5(text.encode()).hexdigest()
            seed = int(text_hash[:8], 16)  # Use first 8 chars as seed
            random.seed(seed)

            # Generate consistent pseudo-random embedding
            embedding = [random.uniform(-1, 1) for _ in range(1536)]
            embeddings.append(embedding)

        logger.info(f"✅ Generated {len(embeddings)} fallback embeddings")
        return embeddings

    def _keyword_search(self, query: StructuredQuery, max_results: int) -> List[RetrievedClause]:
        """Fallback keyword-based search when embeddings fail"""
        try:
            # Extract keywords from query and entities
            keywords = []

            # Add entity values as keywords
            for entity in query.entities:
                keywords.append(entity.value.lower())

            # Add words from the original query
            query_words = [word.lower() for word in query.original_query.split() if len(word) > 2]
            keywords.extend(query_words)

            # Add query type specific keywords
            if query.query_type.value == 'insurance_claim':
                keywords.extend(['surgery', 'coverage', 'covered', 'procedure', 'medical'])
            elif query.query_type.value == 'hr_policy':
                keywords.extend(['leave', 'policy', 'employee', 'benefits'])

            # Remove duplicates
            keywords = list(set(keywords))

            # Get all documents from collection
            all_results = self.collection.get(
                include=['documents', 'metadatas']
            )

            if not all_results['documents']:
                return []

            # Score documents based on keyword matches
            scored_docs = []
            for i, doc in enumerate(all_results['documents']):
                doc_lower = doc.lower()
                score = 0

                # Count keyword matches
                for keyword in keywords:
                    if keyword in doc_lower:
                        score += 1

                # Boost score for exact phrase matches
                query_words = query.original_query.lower().split()
                for word in query_words:
                    if len(word) > 2 and word in doc_lower:
                        score += 0.5

                if score > 0:
                    scored_docs.append({
                        'index': i,
                        'score': score,
                        'doc': doc,
                        'metadata': all_results['metadatas'][i],
                        'id': f"chunk_{i}"  # Generate ID since we can't get it from ChromaDB
                    })

            # Sort by score and take top results
            scored_docs.sort(key=lambda x: x['score'], reverse=True)
            top_docs = scored_docs[:max_results]

            # Convert to RetrievedClause objects
            clauses = []
            for doc_info in top_docs:
                # Normalize score to similarity (0-1 range)
                similarity_score = min(1.0, doc_info['score'] / 5.0)  # Max score of 5 = 1.0 similarity

                # Use lower threshold for keyword search (0.2 instead of 0.7)
                keyword_threshold = 0.2
                if similarity_score >= keyword_threshold:
                    clause = RetrievedClause(
                        clause_id=doc_info['id'],
                        document_id=doc_info['metadata'].get('document_id', ''),
                        content=doc_info['doc'],
                        similarity_score=similarity_score,
                        metadata=doc_info['metadata'],
                        section=doc_info['metadata'].get('section', None)
                    )
                    clauses.append(clause)

            logger.info(f"✅ Keyword search found {len(clauses)} relevant clauses")
            return clauses

        except Exception as e:
            logger.error(f"❌ Keyword search failed: {str(e)}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store collection"""
        try:
            count = self.collection.count()
            return {
                "total_chunks": count,
                "collection_name": self.collection.name,
                "status": "healthy"
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "total_chunks": 0,
                "collection_name": "unknown",
                "status": "error"
            }
    
    def delete_document(self, document_id: str) -> bool:
        """Delete all chunks for a specific document"""
        try:
            # Query for chunks with the document_id
            results = self.collection.get(
                where={"document_id": document_id},
                include=['ids']
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            else:
                logger.info(f"No chunks found for document {document_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {str(e)}")
            return False
    
    def reset_collection(self) -> bool:
        """Reset the entire collection (use with caution)"""
        try:
            self.chroma_client.delete_collection("document_chunks")
            self.collection = self.chroma_client.create_collection(
                name="document_chunks",
                metadata={"description": "Document chunks for semantic search"}
            )
            logger.info("Collection reset successfully")
            return True
        except Exception as e:
            logger.error(f"Error resetting collection: {str(e)}")
            return False
