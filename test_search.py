"""
Test vector search functionality
"""

import sys
sys.path.append('src')

from src.services.vector_store import VectorStore
from src.services.query_parser import QueryParser

def main():
    print("Testing vector search...")
    
    # Initialize services
    vs = VectorStore()
    parser = QueryParser()
    
    # Test query
    query = "46-year-old male, knee surgery in Pune"
    print(f"Query: {query}")
    
    # Parse query
    structured_query = parser.parse_query(query)
    print(f"Query type: {structured_query.query_type}")
    print(f"Entities: {[(e.entity_type.value, e.value) for e in structured_query.entities]}")
    
    # Search for similar chunks
    results = vs.search_similar(structured_query)
    print(f"Found {len(results)} relevant clauses")
    
    for i, result in enumerate(results):
        print(f"\nClause {i+1}:")
        print(f"  Similarity: {result.similarity_score:.3f}")
        print(f"  Content: {result.content[:100]}...")
        print(f"  Section: {result.metadata.get('section', 'Unknown')}")

if __name__ == "__main__":
    main()
