#!/usr/bin/env python3
"""Example API client demonstrating how to use the REST API."""

import time
import requests
import json
from typing import Optional


class PostOpAPIClient:
    """Client for interacting with the PostOp PDF Collector API."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """Initialize the API client.
        
        Args:
            base_url: Base URL of the API server
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
    
    def health_check(self) -> dict:
        """Check API health status."""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()
    
    def start_collection(
        self,
        search_queries: Optional[list] = None,
        direct_urls: Optional[list] = None,
        max_pdfs: int = 10,
        min_confidence: float = 0.5
    ) -> str:
        """Start a new collection run.
        
        Returns:
            Collection run ID
        """
        data = {
            "search_queries": search_queries,
            "direct_urls": direct_urls,
            "max_pdfs": max_pdfs,
            "min_confidence": min_confidence
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/collection/start",
            json=data
        )
        response.raise_for_status()
        return response.json()["run_id"]
    
    def get_collection_status(self, run_id: str) -> dict:
        """Get status of a collection run."""
        response = self.session.get(
            f"{self.base_url}/api/v1/collection/runs/{run_id}"
        )
        response.raise_for_status()
        return response.json()
    
    def search_pdfs(
        self,
        query: str,
        procedure_types: Optional[list] = None,
        min_confidence: float = 0.0,
        limit: int = 20
    ) -> dict:
        """Search for PDFs."""
        data = {
            "query": query,
            "procedure_types": procedure_types,
            "min_confidence": min_confidence,
            "limit": limit
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/search/",
            json=data
        )
        response.raise_for_status()
        return response.json()
    
    def list_pdfs(
        self,
        procedure_type: Optional[str] = None,
        min_confidence: float = 0.5,
        limit: int = 50,
        offset: int = 0
    ) -> dict:
        """List PDFs with filters."""
        params = {
            "min_confidence": min_confidence,
            "limit": limit,
            "offset": offset
        }
        
        if procedure_type:
            params["procedure_type"] = procedure_type
        
        response = self.session.get(
            f"{self.base_url}/api/v1/pdfs/",
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_pdf(self, pdf_id: int) -> dict:
        """Get PDF metadata by ID."""
        response = self.session.get(f"{self.base_url}/api/v1/pdfs/{pdf_id}")
        response.raise_for_status()
        return response.json()
    
    def download_pdf(self, pdf_id: int, output_path: str) -> None:
        """Download PDF file."""
        response = self.session.get(
            f"{self.base_url}/api/v1/pdfs/{pdf_id}/download",
            stream=True
        )
        response.raise_for_status()
        
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
    
    def get_statistics(self) -> dict:
        """Get database statistics."""
        response = self.session.get(f"{self.base_url}/api/v1/statistics/")
        response.raise_for_status()
        return response.json()
    
    def get_summary(self) -> dict:
        """Get system summary."""
        response = self.session.get(f"{self.base_url}/api/v1/statistics/summary")
        response.raise_for_status()
        return response.json()


def main():
    """Demonstrate API usage."""
    print("=" * 60)
    print("PostOp PDF Collector API Client Example")
    print("=" * 60)
    
    # Create client
    client = PostOpAPIClient("http://localhost:8000")
    
    print("\n1. CHECKING API HEALTH")
    print("-" * 40)
    try:
        health = client.health_check()
        print(f"✓ API Status: {health['status']}")
        print(f"✓ Version: {health['version']}")
        print(f"✓ Database: {'Connected' if health['database_connected'] else 'Disconnected'}")
    except Exception as e:
        print(f"❌ API is not accessible. Make sure it's running: python run_api.py")
        print(f"   Error: {e}")
        return
    
    print("\n2. GETTING STATISTICS")
    print("-" * 40)
    stats = client.get_statistics()
    print(f"Total PDFs: {stats['total_pdfs']}")
    print(f"Collection Runs: {stats['total_collection_runs']}")
    print(f"Average Confidence: {stats['average_confidence']:.2%}")
    print(f"Storage Used: {stats['total_storage_mb']:.2f} MB")
    
    print("\n3. STARTING A COLLECTION")
    print("-" * 40)
    print("Starting collection with search query...")
    run_id = client.start_collection(
        search_queries=["post operative care instructions"],
        max_pdfs=5,
        min_confidence=0.5
    )
    print(f"✓ Collection started with ID: {run_id}")
    
    # Monitor collection progress
    print("\nMonitoring collection progress...")
    for i in range(5):
        time.sleep(2)
        status = client.get_collection_status(run_id)
        print(f"  Status: {status['status']} - PDFs: {status['total_pdfs_collected']}/{status['total_urls_discovered']}")
        if status['status'] in ['completed', 'failed']:
            break
    
    print("\n4. SEARCHING PDFS")
    print("-" * 40)
    search_results = client.search_pdfs(
        query="knee surgery",
        min_confidence=0.5,
        limit=5
    )
    print(f"Found {search_results['total_results']} PDFs matching 'knee surgery'")
    print(f"Search time: {search_results['search_time_ms']}ms")
    
    if search_results['results']:
        print("\nTop results:")
        for i, pdf in enumerate(search_results['results'][:3], 1):
            print(f"  {i}. {pdf['filename']} (confidence: {pdf['confidence_score']:.2%})")
    
    print("\n5. LISTING PDFS BY PROCEDURE TYPE")
    print("-" * 40)
    ortho_pdfs = client.list_pdfs(
        procedure_type="orthopedic",
        min_confidence=0.6,
        limit=10
    )
    print(f"Found {ortho_pdfs['total']} orthopedic PDFs")
    
    if ortho_pdfs['items']:
        print("\nTop orthopedic PDFs:")
        for i, pdf in enumerate(ortho_pdfs['items'][:3], 1):
            print(f"  {i}. {pdf['filename']} - {pdf['source_domain']}")
    
    print("\n6. GETTING SYSTEM SUMMARY")
    print("-" * 40)
    summary = client.get_summary()
    print(f"Overview:")
    print(f"  Total PDFs: {summary['overview']['total_pdfs']}")
    print(f"  Average Confidence: {summary['overview']['average_confidence']}")
    print(f"  Storage: {summary['overview']['storage_mb']} MB")
    
    if summary['top_sources']:
        print(f"\nTop Sources:")
        for source in summary['top_sources']:
            print(f"  - {source['domain']}: {source['count']} PDFs")
    
    print("\n" + "=" * 60)
    print("✅ API client example completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()