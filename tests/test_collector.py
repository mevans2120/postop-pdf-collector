"""Tests for the PostOp PDF Collector."""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from postop_collector.config.settings import Settings
from postop_collector.core.collector import PostOpPDFCollector
from postop_collector.core.models import CollectionResult, PDFMetadata


@pytest.fixture
def settings(tmp_path):
    """Create test settings."""
    return Settings(
        output_directory=str(tmp_path / "output"),
        max_pdfs_per_source=5,
        max_pages_per_site=10,
        max_requests_per_second=10.0,
    )


@pytest.fixture
async def collector(settings):
    """Create test collector instance."""
    collector = PostOpPDFCollector(settings)
    async with collector:
        yield collector


class TestPostOpPDFCollector:
    """Test suite for PostOpPDFCollector."""
    
    def test_initialization(self, settings):
        """Test collector initialization."""
        collector = PostOpPDFCollector(settings)
        
        assert collector.settings == settings
        assert collector.collected_urls == set()
        assert collector.output_dir.exists()
        assert collector.metadata_file == collector.output_dir / "metadata.json"
    
    def test_load_existing_metadata(self, settings, tmp_path):
        """Test loading existing metadata."""
        # Create metadata file
        metadata_file = Path(settings.output_directory) / "metadata.json"
        metadata_file.parent.mkdir(parents=True, exist_ok=True)
        
        existing_data = {
            "collected_urls": ["http://example.com/test.pdf"],
            "total_pdfs": 1
        }
        with open(metadata_file, "w") as f:
            json.dump(existing_data, f)
        
        # Initialize collector
        collector = PostOpPDFCollector(settings)
        
        assert "http://example.com/test.pdf" in collector.collected_urls
        assert len(collector.collected_urls) == 1
    
    @pytest.mark.asyncio
    async def test_search_google_no_credentials(self, collector):
        """Test Google search without credentials."""
        collector.settings.google_api_key = None
        collector.settings.google_search_engine_id = None
        
        results = await collector.search_google("test query")
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_google_with_mock(self, collector):
        """Test Google search with mocked response."""
        collector.settings.google_api_key = "test_key"
        collector.settings.google_search_engine_id = "test_id"
        
        mock_response = {
            "items": [
                {"link": "http://example.com/doc1.pdf"},
                {"link": "http://example.com/doc2.pdf"},
            ]
        }
        
        with patch.object(collector.session, "get") as mock_get:
            mock_context = AsyncMock()
            mock_context.status = 200
            mock_context.json = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aenter__.return_value = mock_context
            
            results = await collector.search_google("test query", num_results=2)
            
            assert len(results) == 2
            assert "http://example.com/doc1.pdf" in results
            assert "http://example.com/doc2.pdf" in results
    
    @pytest.mark.asyncio
    async def test_download_pdf_success(self, collector):
        """Test successful PDF download."""
        test_pdf_content = b"%PDF-1.4\ntest content"
        
        with patch.object(collector.session, "get") as mock_get:
            mock_context = AsyncMock()
            mock_context.status = 200
            mock_context.read = AsyncMock(return_value=test_pdf_content)
            mock_get.return_value.__aenter__.return_value = mock_context
            
            content = await collector.download_pdf("http://example.com/test.pdf")
            
            assert content == test_pdf_content
    
    @pytest.mark.asyncio
    async def test_download_pdf_already_collected(self, collector):
        """Test skipping already collected PDFs."""
        collector.collected_urls.add("http://example.com/test.pdf")
        
        content = await collector.download_pdf("http://example.com/test.pdf")
        
        assert content is None
    
    @pytest.mark.asyncio
    async def test_download_pdf_not_pdf(self, collector):
        """Test handling non-PDF content."""
        test_content = b"<html>Not a PDF</html>"
        
        with patch.object(collector.session, "get") as mock_get:
            mock_context = AsyncMock()
            mock_context.status = 200
            mock_context.read = AsyncMock(return_value=test_content)
            mock_get.return_value.__aenter__.return_value = mock_context
            
            content = await collector.download_pdf("http://example.com/test.html")
            
            assert content is None
    
    @pytest.mark.asyncio
    async def test_analyze_pdf(self, collector):
        """Test PDF analysis."""
        test_pdf_content = b"%PDF-1.4\ntest content"
        test_url = "http://example.com/test.pdf"
        
        metadata = await collector.analyze_pdf(test_pdf_content, test_url)
        
        assert metadata.url == test_url
        assert metadata.filename == "test.pdf"
        assert metadata.file_size == len(test_pdf_content)
        assert metadata.source_domain == "example.com"
        assert Path(metadata.file_path).exists()
    
    @pytest.mark.asyncio
    async def test_discover_pdfs_from_website(self, collector):
        """Test PDF discovery from website."""
        test_html = """
        <html>
            <body>
                <a href="doc1.pdf">Document 1</a>
                <a href="/path/doc2.pdf">Document 2</a>
                <a href="http://example.com/doc3.pdf">Document 3</a>
                <a href="page2.html">Another page</a>
            </body>
        </html>
        """
        
        with patch.object(collector.session, "get") as mock_get:
            mock_context = AsyncMock()
            mock_context.status = 200
            mock_context.headers = {"content-type": "text/html"}
            mock_context.text = AsyncMock(return_value=test_html)
            mock_get.return_value.__aenter__.return_value = mock_context
            
            pdfs = await collector.discover_pdfs_from_website("http://example.com")
            
            assert len(pdfs) == 3
            assert any("doc1.pdf" in url for url in pdfs)
            assert any("doc2.pdf" in url for url in pdfs)
            assert any("doc3.pdf" in url for url in pdfs)
    
    def test_save_metadata(self, collector):
        """Test metadata saving."""
        metadata = PDFMetadata(
            url="http://example.com/test.pdf",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size=1000,
            source_domain="example.com",
            download_timestamp="2024-01-01T00:00:00",
        )
        
        collector._save_metadata([metadata])
        
        assert collector.metadata_file.exists()
        
        with open(collector.metadata_file, "r") as f:
            data = json.load(f)
            
        assert len(data["pdfs"]) == 1
        assert data["pdfs"][0]["filename"] == "test.pdf"
        assert data["total_pdfs"] == 0  # No URLs in collected_urls yet


@pytest.mark.asyncio
class TestCollectionIntegration:
    """Integration tests for collection operations."""
    
    async def test_collect_from_urls(self, collector):
        """Test collection from direct URLs."""
        test_pdf_content = b"%PDF-1.4\ntest content"
        test_urls = [
            "http://example.com/doc1.pdf",
            "http://example.com/doc2.pdf",
        ]
        
        with patch.object(collector, "download_pdf") as mock_download:
            mock_download.return_value = test_pdf_content
            
            with patch.object(collector, "analyze_pdf") as mock_analyze:
                mock_metadata = PDFMetadata(
                    url="http://example.com/test.pdf",
                    filename="test.pdf",
                    file_path="/path/to/test.pdf",
                    file_hash="abc123",
                    file_size=1000,
                    source_domain="example.com",
                    download_timestamp="2024-01-01T00:00:00",
                )
                mock_analyze.return_value = mock_metadata
                
                result = await collector.collect_from_urls(test_urls)
                
                assert isinstance(result, CollectionResult)
                assert result.total_pdfs_collected == 2
                assert len(result.metadata_list) == 2
    
    async def test_run_collection(self, collector):
        """Test full collection run."""
        search_queries = ["post operative instructions"]
        direct_urls = ["http://example.com/manual.pdf"]
        
        with patch.object(collector, "collect_from_search_queries") as mock_search:
            mock_search.return_value = CollectionResult(
                total_pdfs_collected=3,
                total_urls_discovered=5,
                metadata_list=[],
                collection_timestamp="2024-01-01T00:00:00",
            )
            
            with patch.object(collector, "collect_from_urls") as mock_urls:
                mock_urls.return_value = CollectionResult(
                    total_pdfs_collected=1,
                    total_urls_discovered=1,
                    metadata_list=[],
                    collection_timestamp="2024-01-01T00:00:00",
                )
                
                result = await collector.run_collection(
                    search_queries=search_queries,
                    direct_urls=direct_urls
                )
                
                assert result.total_pdfs_collected == 0  # Empty metadata lists
                assert result.total_urls_discovered == 6