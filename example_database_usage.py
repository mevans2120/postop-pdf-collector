#!/usr/bin/env python3
"""Example script demonstrating database functionality."""

import asyncio
import sys
from pathlib import Path

# Add the project to path
sys.path.insert(0, str(Path(__file__).parent))

from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings
from postop_collector.storage.metadata_db import MetadataDB
from postop_collector.core.models import ProcedureType


async def example_collection_with_database():
    """Example of using the collector with database persistence."""
    print("=" * 60)
    print("PostOp PDF Collector - Database Example")
    print("=" * 60)
    
    # Configure settings with database
    settings = Settings(
        output_directory="./example_output",
        max_pdfs_per_source=2,
        min_confidence_score=0.3,
        database_url="sqlite:///./data/example_collection.db",  # SQLite database
        environment="development"
    )
    
    print("\n1. INITIALIZING COLLECTOR WITH DATABASE")
    print("-" * 40)
    print(f"Output directory: {settings.output_directory}")
    print(f"Database: SQLite (./data/example_collection.db)")
    print(f"Environment: {settings.environment}")
    
    # Initialize collector with database enabled
    async with PostOpPDFCollector(settings, use_database=True) as collector:
        print("✓ Collector initialized with database support")
        
        # Run a small collection
        print("\n2. RUNNING COLLECTION")
        print("-" * 40)
        print("Note: This will attempt to collect from example.com")
        print("(Won't find actual PDFs, but demonstrates the process)")
        
        result = await collector.run_collection(
            search_queries=["post operative care example"],
            direct_urls=["https://www.example.com"]
        )
        
        print(f"\n✓ Collection completed:")
        print(f"  - URLs discovered: {result.total_urls_discovered}")
        print(f"  - PDFs collected: {result.total_pdfs_collected}")
        print(f"  - Collection run ID: {collector.collection_run_id}")
    
    # Now demonstrate querying the database
    print("\n3. QUERYING DATABASE")
    print("-" * 40)
    
    with MetadataDB(database_url=settings.database_url) as db:
        # Get statistics
        stats = db.get_statistics()
        print(f"\nDatabase Statistics:")
        print(f"  - Total PDFs: {stats['total_pdfs']}")
        print(f"  - Total collection runs: {stats['total_collection_runs']}")
        print(f"  - Average confidence: {stats['average_confidence']:.2%}")
        print(f"  - Total storage: {stats['total_storage_bytes'] / 1024:.2f} KB")
        
        # Get PDFs by procedure type
        print(f"\nPDFs by procedure type:")
        for proc_type, count in stats['pdfs_by_procedure'].items():
            print(f"  - {proc_type}: {count}")
        
        # Search for specific content
        print(f"\nSearching for 'care' in database...")
        search_results = db.search_pdfs("care", min_confidence=0.0)
        print(f"  Found {len(search_results)} matching PDFs")
        
        # Get collection run details if we have one
        if collector.collection_run_id:
            print(f"\nCollection Run Details:")
            run_details = db.get_collection_run(collector.collection_run_id)
            if run_details:
                print(f"  - Status: {run_details['status']}")
                print(f"  - Started: {run_details['started_at']}")
                print(f"  - Completed: {run_details['completed_at']}")
                print(f"  - Success rate: {run_details['success_rate']:.2%}")
    
    print("\n" + "=" * 60)
    print("✅ Database example completed!")
    print("=" * 60)


async def example_database_operations():
    """Example of direct database operations."""
    print("\n4. DIRECT DATABASE OPERATIONS")
    print("-" * 40)
    
    # Create a test database
    with MetadataDB(database_url="sqlite:///./data/test_operations.db") as db:
        # Example: Cache search results
        print("\nCaching search results...")
        search_results = [
            {"url": "https://example.com/guide1.pdf", "title": "Surgery Guide"},
            {"url": "https://example.com/guide2.pdf", "title": "Recovery Tips"},
        ]
        db.cache_search_results(
            query="knee surgery recovery",
            results=search_results,
            source="google",
            ttl_hours=24
        )
        print("✓ Search results cached")
        
        # Retrieve cached results
        cached = db.get_cached_search_results("knee surgery recovery", "google")
        if cached:
            print(f"✓ Retrieved {len(cached)} cached results")
        
        # Example: Search by procedure type
        print("\nSearching for orthopedic procedures...")
        ortho_pdfs = db.get_pdfs_by_procedure_type(
            ProcedureType.ORTHOPEDIC,
            min_confidence=0.5
        )
        print(f"✓ Found {len(ortho_pdfs)} orthopedic PDFs")
    
    print("\n✅ Direct database operations completed!")


def main():
    """Run all examples."""
    print("\n🚀 Starting PostOp PDF Collector Database Examples\n")
    
    try:
        # Run async examples
        asyncio.run(example_collection_with_database())
        asyncio.run(example_database_operations())
        
        print("\n" + "=" * 60)
        print("🎉 ALL DATABASE EXAMPLES COMPLETED!")
        print("=" * 60)
        print("\nThe database functionality is working correctly!")
        print("\nNext steps:")
        print("1. Configure DATABASE_URL in your .env file")
        print("2. Use PostgreSQL for production: DATABASE_URL=postgresql://user:pass@host/db")
        print("3. Use SQLite for development: DATABASE_URL=sqlite:///./data/collector.db")
        print("4. Query the database to analyze collected PDFs")
        
    except Exception as e:
        print(f"\n❌ Error during database examples: {e}")
        print("\nPlease make sure SQLAlchemy is installed:")
        print("  pip install sqlalchemy psycopg2-binary")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())