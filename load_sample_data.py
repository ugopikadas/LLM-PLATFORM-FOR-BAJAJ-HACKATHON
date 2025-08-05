"""
Script to load sample data into the vector database
"""

import sys
import asyncio
sys.path.append('src')

from src.utils.startup import create_minimal_sample_data
from src.services.vector_store import VectorStore

async def main():
    print("Loading sample data...")
    vs = VectorStore()
    
    # Check current stats
    stats = vs.get_collection_stats()
    print(f"Current chunks: {stats.get('total_chunks', 0)}")
    
    # Add sample data
    await create_minimal_sample_data(vs)
    
    # Check new stats
    stats = vs.get_collection_stats()
    print(f"Total chunks after loading: {stats.get('total_chunks', 0)}")

if __name__ == "__main__":
    asyncio.run(main())
