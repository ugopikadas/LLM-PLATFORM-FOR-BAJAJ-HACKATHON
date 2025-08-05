"""
Main processing service that orchestrates the entire pipeline
"""

import time
import logging
from typing import Dict, Any

from src.models.schemas import (
    ProcessingRequest, ProcessingResponse, StructuredQuery, 
    RetrievedClause, DecisionType
)
from src.services.query_parser import QueryParser
from src.services.vector_store import VectorStore
from src.services.decision_engine import DecisionEngine

logger = logging.getLogger(__name__)


class ProcessingService:
    """Main service that orchestrates the document processing pipeline"""
    
    def __init__(self):
        self.query_parser = QueryParser()
        self.vector_store = VectorStore()
        self.decision_engine = DecisionEngine()
    
    async def process_query(self, request: ProcessingRequest) -> ProcessingResponse:
        """
        Process a natural language query through the complete pipeline
        
        Args:
            request: ProcessingRequest containing the query and context
            
        Returns:
            ProcessingResponse with decision and justification
        """
        start_time = time.time()
        
        try:
            logger.info(f"Processing query: {request.query}")
            
            # Step 1: Parse and structure the query
            structured_query = self.query_parser.parse_query(request.query)
            
            # Step 2: Search for relevant clauses
            relevant_clauses = self.vector_store.search_similar(structured_query)
            
            # Step 3: Make decision based on clauses
            decision, amount, justification, confidence = self.decision_engine.make_decision(
                structured_query, relevant_clauses
            )
            
            # Step 4: Calculate processing time
            processing_time = time.time() - start_time
            
            # Step 5: Create response
            response = ProcessingResponse(
                decision=decision,
                amount=amount,
                justification=justification,
                confidence=confidence,
                clauses_used=relevant_clauses,
                processing_time=processing_time,
                query_analysis=structured_query
            )
            
            logger.info(f"Query processed successfully in {processing_time:.2f}s: {decision}")
            return response
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Error processing query: {str(e)}")
            
            # Return error response
            return ProcessingResponse(
                decision=DecisionType.PENDING,
                amount=None,
                justification=f"Error processing query: {str(e)}",
                confidence=0.0,
                clauses_used=[],
                processing_time=processing_time,
                query_analysis=StructuredQuery(
                    original_query=request.query,
                    query_type=request.query_type,
                    entities=[],
                    intent="Error processing query",
                    confidence=0.0
                )
            )
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get the status of all system components"""
        try:
            vector_stats = self.vector_store.get_collection_stats()
            
            return {
                "status": "healthy",
                "components": {
                    "query_parser": "healthy",
                    "vector_store": vector_stats.get("status", "unknown"),
                    "decision_engine": "healthy"
                },
                "vector_store_stats": vector_stats
            }
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "components": {
                    "query_parser": "unknown",
                    "vector_store": "unknown", 
                    "decision_engine": "unknown"
                }
            }
