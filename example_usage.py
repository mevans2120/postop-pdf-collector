"""Example usage of the PostOp PDF Collector."""

import asyncio
import logging
from pathlib import Path

from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings
from postop_collector.core.models import SearchQuery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def basic_collection():
    """Basic example of collecting PDFs."""
    print("\n=== Basic Collection Example ===\n")
    
    # Create settings with minimal configuration
    settings = Settings(
        output_directory="./output/basic",
        max_pdfs_per_source=5,
        max_requests_per_second=1.0
    )
    
    async with PostOpPDFCollector(settings) as collector:
        # Collect from direct URLs
        result = await collector.collect_from_urls([
            "https://www.hopkinsmedicine.org/health/treatment-tests-and-therapies",
            "https://www.mayoclinic.org/patient-care-and-health-information",
        ])
        
        print(f"Collected {result.total_pdfs_collected} PDFs")
        print(f"From {result.total_urls_discovered} URLs discovered")
        
        # Show collected PDFs by domain
        for domain, count in result.by_source_domain.items():
            print(f"  - {domain}: {count} PDFs")


async def search_based_collection():
    """Example using search queries to find PDFs."""
    print("\n=== Search-Based Collection Example ===\n")
    
    # Note: This requires Google API credentials
    settings = Settings(
        output_directory="./output/search",
        google_api_key="your_api_key_here",  # Replace with actual key
        google_search_engine_id="your_engine_id_here",  # Replace with actual ID
        max_pdfs_per_source=3
    )
    
    async with PostOpPDFCollector(settings) as collector:
        # Define search queries
        queries = [
            "knee replacement post operative instructions pdf",
            "cardiac surgery recovery guide pdf",
            "hip surgery aftercare pdf site:.edu",
            "post surgical wound care instructions filetype:pdf"
        ]
        
        result = await collector.collect_from_search_queries(queries)
        
        print(f"Search Results:")
        print(f"  Total PDFs collected: {result.total_pdfs_collected}")
        print(f"  Success rate: {result.success_rate:.1%}")
        print(f"  Average confidence: {result.average_confidence:.2f}")
        
        # Show breakdown by procedure type (once analysis is implemented)
        if result.by_procedure_type:
            print("\nBy Procedure Type:")
            for proc_type, count in result.by_procedure_type.items():
                print(f"  - {proc_type}: {count} PDFs")


async def comprehensive_collection():
    """Comprehensive example with all features."""
    print("\n=== Comprehensive Collection Example ===\n")
    
    # Full configuration
    settings = Settings(
        output_directory="./output/comprehensive",
        max_pdfs_per_source=10,
        max_pages_per_site=100,
        max_file_size_mb=25,
        max_requests_per_second=2.0,
        request_timeout=45,
        min_confidence_score=0.6,
        log_level="DEBUG"
    )
    
    async with PostOpPDFCollector(settings) as collector:
        # Combine search queries and direct URLs
        result = await collector.run_collection(
            search_queries=[
                "orthopedic surgery post op care pdf",
                "spine surgery recovery instructions pdf",
                "arthroscopy aftercare guide pdf"
            ],
            direct_urls=[
                "https://orthoinfo.aaos.org/en/recovery/",
                "https://www.hss.edu/conditions_post-operative-instructions.asp",
                "https://my.clevelandclinic.org/health/articles"
            ]
        )
        
        # Detailed results
        print(f"Collection Statistics:")
        print(f"  Total PDFs: {result.total_pdfs_collected}")
        print(f"  Total URLs discovered: {result.total_urls_discovered}")
        print(f"  Success rate: {result.success_rate:.1%}")
        print(f"  Collection time: {result.collection_timestamp}")
        
        if result.errors:
            print(f"\nErrors encountered: {len(result.errors)}")
            for error in result.errors[:5]:  # Show first 5 errors
                print(f"  - {error}")
        
        # Top sources
        print("\nTop PDF Sources:")
        sorted_domains = sorted(
            result.by_source_domain.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for domain, count in sorted_domains[:5]:
            print(f"  - {domain}: {count} PDFs")
        
        # Sample metadata
        if result.metadata_list:
            print("\nSample PDF Metadata:")
            sample = result.metadata_list[0]
            print(f"  URL: {sample.url}")
            print(f"  Filename: {sample.filename}")
            print(f"  Size: {sample.file_size:,} bytes")
            print(f"  Domain: {sample.source_domain}")
            print(f"  Downloaded: {sample.download_timestamp}")


async def custom_search_queries():
    """Example with custom search query configuration."""
    print("\n=== Custom Search Queries Example ===\n")
    
    from postop_collector.core.models import (
        CollectionConfig,
        ProcedureType,
        SearchQuery
    )
    
    # Define specific search queries with filters
    search_configs = [
        SearchQuery(
            query="knee replacement recovery",
            max_results=15,
            procedure_types=[ProcedureType.ORTHOPEDIC],
            required_keywords=["recovery", "rehabilitation"],
            excluded_keywords=["advertisement", "promotional"]
        ),
        SearchQuery(
            query="heart surgery post operative care",
            max_results=10,
            procedure_types=[ProcedureType.CARDIAC],
            required_keywords=["post-operative", "care", "instructions"]
        )
    ]
    
    # Create collection configuration
    collection_config = CollectionConfig(
        search_queries=search_configs,
        target_domains=["mayo.edu", "hopkins.edu", "cleveland.org"],
        excluded_domains=["ads.com", "spam.org"],
        max_pdfs_total=50,
        quality_threshold=0.7
    )
    
    print("Configured search queries:")
    for query in collection_config.search_queries:
        print(f"  - '{query.query}' (max {query.max_results} results)")
        if query.required_keywords:
            print(f"    Required: {', '.join(query.required_keywords)}")
        if query.excluded_keywords:
            print(f"    Excluded: {', '.join(query.excluded_keywords)}")
    
    print(f"\nTarget domains: {', '.join(collection_config.target_domains)}")
    print(f"Quality threshold: {collection_config.quality_threshold}")


def check_environment():
    """Check if environment is properly configured."""
    print("\n=== Environment Check ===\n")
    
    settings = Settings()
    
    print("Current Configuration:")
    print(f"  Output directory: {settings.output_directory}")
    print(f"  Max PDFs per source: {settings.max_pdfs_per_source}")
    print(f"  Request timeout: {settings.request_timeout}s")
    print(f"  Log level: {settings.log_level}")
    
    if settings.google_api_key:
        print("  ✓ Google API key configured")
    else:
        print("  ✗ Google API key not configured (search features disabled)")
    
    if settings.google_search_engine_id:
        print("  ✓ Google Search Engine ID configured")
    else:
        print("  ✗ Google Search Engine ID not configured")
    
    # Check output directory
    output_path = Path(settings.output_directory)
    if output_path.exists():
        print(f"  ✓ Output directory exists: {output_path.absolute()}")
    else:
        print(f"  ℹ Output directory will be created: {output_path.absolute()}")


async def main():
    """Run all examples."""
    # Check environment first
    check_environment()
    
    # Run examples (comment out any you don't want to run)
    
    # Basic collection from websites
    await basic_collection()
    
    # Search-based collection (requires API keys)
    # await search_based_collection()
    
    # Comprehensive collection
    # await comprehensive_collection()
    
    # Show custom search configuration
    await custom_search_queries()
    
    print("\n=== Examples Complete ===")


if __name__ == "__main__":
    asyncio.run(main())