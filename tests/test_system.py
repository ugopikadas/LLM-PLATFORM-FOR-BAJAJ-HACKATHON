"""
Test cases for the LLM Document Processing System
"""

import pytest
import asyncio
import os
import sys

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.models.schemas import ProcessingRequest, QueryType
from src.services.processing_service import ProcessingService
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import VectorStore
from src.services.query_parser import QueryParser


class TestDocumentProcessor:
    """Test document processing functionality"""
    
    def setup_method(self):
        self.processor = DocumentProcessor()
    
    def test_supported_formats(self):
        """Test that supported formats are correctly defined"""
        expected_formats = {'.pdf', '.docx', '.doc', '.txt', '.eml', '.html'}
        assert self.processor.supported_formats == expected_formats
    
    def test_process_text_document(self):
        """Test processing of text documents"""
        # Create a temporary text file
        test_content = "This is a test document for processing."
        test_file = "test_document.txt"
        
        with open(test_file, 'w') as f:
            f.write(test_content)
        
        try:
            chunks = self.processor.process_document(test_file)
            assert len(chunks) > 0
            assert chunks[0].content.strip() == test_content
            assert chunks[0].document_id is not None
        finally:
            os.remove(test_file)
    
    def test_unsupported_format(self):
        """Test handling of unsupported file formats"""
        with pytest.raises(ValueError):
            self.processor._extract_text("test.xyz", ".xyz")


class TestQueryParser:
    """Test query parsing and entity extraction"""
    
    def setup_method(self):
        self.parser = QueryParser()
    
    def test_age_extraction(self):
        """Test extraction of age entities"""
        query = "46-year-old male needs treatment"
        structured_query = self.parser.parse_query(query)
        
        age_entities = [e for e in structured_query.entities if e.entity_type.value == "age"]
        assert len(age_entities) > 0
        assert "46" in [e.value for e in age_entities]
    
    def test_gender_extraction(self):
        """Test extraction of gender entities"""
        query = "46-year-old male needs treatment"
        structured_query = self.parser.parse_query(query)
        
        gender_entities = [e for e in structured_query.entities if e.entity_type.value == "gender"]
        assert len(gender_entities) > 0
        assert any("male" in e.value.lower() for e in gender_entities)
    
    def test_procedure_extraction(self):
        """Test extraction of medical procedures"""
        query = "knee surgery required for patient"
        structured_query = self.parser.parse_query(query)
        
        procedure_entities = [e for e in structured_query.entities if e.entity_type.value == "procedure"]
        assert len(procedure_entities) > 0
    
    def test_location_extraction(self):
        """Test extraction of location entities"""
        query = "treatment in Pune hospital"
        structured_query = self.parser.parse_query(query)
        
        location_entities = [e for e in structured_query.entities if e.entity_type.value == "location"]
        assert len(location_entities) > 0
        assert any("pune" in e.value.lower() for e in location_entities)


class TestVectorStore:
    """Test vector storage and search functionality"""
    
    def setup_method(self):
        self.vector_store = VectorStore()
    
    def test_collection_initialization(self):
        """Test that vector store initializes correctly"""
        assert self.vector_store.collection is not None
        assert self.vector_store.chroma_client is not None
    
    def test_collection_stats(self):
        """Test getting collection statistics"""
        stats = self.vector_store.get_collection_stats()
        assert "total_chunks" in stats
        assert "collection_name" in stats
        assert "status" in stats


class TestIntegration:
    """Integration tests for the complete system"""
    
    def setup_method(self):
        self.processing_service = ProcessingService()
    
    @pytest.mark.asyncio
    async def test_insurance_query_processing(self):
        """Test processing of insurance-related queries"""
        request = ProcessingRequest(
            query="46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
            query_type=QueryType.INSURANCE_CLAIM
        )
        
        response = await self.processing_service.process_query(request)
        
        assert response is not None
        assert response.decision is not None
        assert response.justification is not None
        assert response.confidence >= 0.0
        assert response.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_hr_policy_query(self):
        """Test processing of HR policy queries"""
        request = ProcessingRequest(
            query="What is the maternity leave policy for employees?",
            query_type=QueryType.HR_POLICY
        )
        
        response = await self.processing_service.process_query(request)
        
        assert response is not None
        assert response.decision is not None
        assert response.query_analysis.query_type == QueryType.HR_POLICY
    
    @pytest.mark.asyncio
    async def test_general_query(self):
        """Test processing of general queries"""
        request = ProcessingRequest(
            query="What are the working hours?",
            query_type=QueryType.GENERAL
        )
        
        response = await self.processing_service.process_query(request)
        
        assert response is not None
        assert response.decision is not None
    
    def test_system_status(self):
        """Test system health check"""
        status = self.processing_service.get_system_status()
        
        assert "status" in status
        assert "components" in status


# Sample test queries for manual testing
SAMPLE_QUERIES = [
    {
        "query": "46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
        "expected_entities": ["age", "gender", "procedure", "location", "policy_duration"],
        "query_type": "insurance_claim"
    },
    {
        "query": "Female employee, 28 years old, requesting maternity leave",
        "expected_entities": ["gender", "age"],
        "query_type": "hr_policy"
    },
    {
        "query": "Heart surgery coverage for 55-year-old patient in Mumbai",
        "expected_entities": ["procedure", "age", "location"],
        "query_type": "insurance_claim"
    },
    {
        "query": "What is the notice period for senior employees?",
        "expected_entities": [],
        "query_type": "hr_policy"
    },
    {
        "query": "Dental treatment coverage under health insurance",
        "expected_entities": ["procedure"],
        "query_type": "insurance_claim"
    }
]


if __name__ == "__main__":
    # Run basic tests
    print("Running basic system tests...")
    
    # Test query parser
    parser = QueryParser()
    for sample in SAMPLE_QUERIES:
        print(f"\nTesting query: {sample['query']}")
        result = parser.parse_query(sample['query'])
        print(f"Entities found: {[e.entity_type.value for e in result.entities]}")
        print(f"Query type: {result.query_type}")
        print(f"Intent: {result.intent}")
    
    print("\nBasic tests completed. Run 'pytest tests/test_system.py' for full test suite.")
