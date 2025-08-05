"""
Demo script for the LLM Document Processing System
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.models.schemas import ProcessingRequest, QueryType
from src.services.processing_service import ProcessingService
from src.services.document_processor import DocumentProcessor
from src.services.vector_store import VectorStore


async def demo_query_processing():
    """Demonstrate query processing capabilities"""
    print("🔍 Demo: Query Processing")
    print("=" * 50)
    
    processing_service = ProcessingService()
    
    # Sample queries to test
    test_queries = [
        {
            "query": "46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
            "query_type": QueryType.INSURANCE_CLAIM,
            "description": "Insurance claim for knee surgery"
        },
        {
            "query": "What is the maternity leave policy for employees?",
            "query_type": QueryType.HR_POLICY,
            "description": "HR policy inquiry about maternity leave"
        },
        {
            "query": "Heart surgery coverage for 55-year-old patient in Mumbai",
            "query_type": QueryType.INSURANCE_CLAIM,
            "description": "Insurance claim for heart surgery"
        },
        {
            "query": "What is the notice period for senior employees?",
            "query_type": QueryType.HR_POLICY,
            "description": "HR policy inquiry about notice period"
        }
    ]
    
    for i, test_case in enumerate(test_queries, 1):
        print(f"\n📝 Test Case {i}: {test_case['description']}")
        print(f"Query: \"{test_case['query']}\"")
        print(f"Type: {test_case['query_type'].value}")
        
        try:
            request = ProcessingRequest(
                query=test_case['query'],
                query_type=test_case['query_type']
            )
            
            response = await processing_service.process_query(request)
            
            print(f"\n✅ Result:")
            print(f"   Decision: {response.decision.value}")
            print(f"   Confidence: {response.confidence:.2f}")
            print(f"   Processing Time: {response.processing_time:.2f}s")
            print(f"   Justification: {response.justification[:100]}...")
            print(f"   Entities Found: {len(response.query_analysis.entities)}")
            print(f"   Clauses Used: {len(response.clauses_used)}")
            
            if response.amount:
                print(f"   Amount: ₹{response.amount:,.2f}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
        
        print("-" * 30)


def demo_document_processing():
    """Demonstrate document processing capabilities"""
    print("\n📄 Demo: Document Processing")
    print("=" * 50)
    
    processor = DocumentProcessor()
    vector_store = VectorStore()
    
    # Sample documents to process
    sample_docs = [
        "data/sample_policies/health_insurance_policy.txt",
        "data/sample_policies/corporate_policy.txt"
    ]
    
    for doc_path in sample_docs:
        if os.path.exists(doc_path):
            print(f"\n📁 Processing: {doc_path}")
            
            try:
                # Process document
                chunks = processor.process_document(doc_path)
                print(f"   ✅ Created {len(chunks)} chunks")
                
                # Add to vector store
                success = vector_store.add_documents(chunks)
                if success:
                    print(f"   ✅ Added to vector database")
                else:
                    print(f"   ❌ Failed to add to vector database")
                
                # Show sample chunk
                if chunks:
                    sample_chunk = chunks[0]
                    print(f"   📝 Sample chunk: {sample_chunk.content[:100]}...")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        else:
            print(f"   ⚠️  File not found: {doc_path}")


def demo_system_status():
    """Demonstrate system status checking"""
    print("\n🏥 Demo: System Health Check")
    print("=" * 50)
    
    processing_service = ProcessingService()
    
    try:
        status = processing_service.get_system_status()
        
        print(f"Overall Status: {status['status']}")
        print(f"Components:")
        for component, health in status.get('components', {}).items():
            print(f"   {component}: {health}")
        
        if 'vector_store_stats' in status:
            stats = status['vector_store_stats']
            print(f"Vector Store:")
            print(f"   Total Chunks: {stats.get('total_chunks', 0)}")
            print(f"   Collection: {stats.get('collection_name', 'unknown')}")
        
    except Exception as e:
        print(f"❌ Error checking system status: {str(e)}")


def demo_entity_extraction():
    """Demonstrate entity extraction capabilities"""
    print("\n🏷️  Demo: Entity Extraction")
    print("=" * 50)
    
    from src.services.query_parser import QueryParser
    
    parser = QueryParser()
    
    test_queries = [
        "46-year-old male, knee surgery in Pune, 3-month-old insurance policy",
        "Female employee, 28 years old, requesting maternity leave",
        "Heart surgery coverage for 55-year-old patient in Mumbai",
        "₹50,000 claim for dental treatment in Delhi"
    ]
    
    for query in test_queries:
        print(f"\n📝 Query: \"{query}\"")
        
        try:
            result = parser.parse_query(query)
            
            print(f"   Query Type: {result.query_type.value}")
            print(f"   Intent: {result.intent}")
            print(f"   Confidence: {result.confidence:.2f}")
            print(f"   Entities:")
            
            for entity in result.entities:
                print(f"      {entity.entity_type.value}: {entity.value} (confidence: {entity.confidence:.2f})")
            
            if not result.entities:
                print("      No entities extracted")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")


async def main():
    """Main demo function"""
    print("🚀 LLM Document Processing System Demo")
    print("=" * 60)
    
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not found in environment variables")
        print("   Some features may not work properly")
        print("   Please set your API key in the .env file")
        print()
    
    try:
        # Demo 1: Entity Extraction (doesn't require API key for regex-based extraction)
        demo_entity_extraction()
        
        # Demo 2: Document Processing
        demo_document_processing()
        
        # Demo 3: System Status
        demo_system_status()
        
        # Demo 4: Query Processing (requires API key)
        if os.getenv('OPENAI_API_KEY'):
            await demo_query_processing()
        else:
            print("\n🔍 Demo: Query Processing")
            print("=" * 50)
            print("⚠️  Skipped - requires OPENAI_API_KEY")
        
        print("\n✅ Demo completed successfully!")
        print("\nNext steps:")
        print("1. Set up your OpenAI API key in .env file")
        print("2. Run the web application: python main.py")
        print("3. Open http://localhost:8000 in your browser")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {str(e)}")
        print("Please check your setup and try again")


if __name__ == "__main__":
    asyncio.run(main())
