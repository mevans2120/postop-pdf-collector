"""Tests for Pydantic models."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from postop_collector.core.models import (
    CollectionConfig,
    CollectionResult,
    ContentQuality,
    PDFMetadata,
    ProcedureType,
    SearchQuery,
)


class TestPDFMetadata:
    """Tests for PDFMetadata model."""
    
    def test_valid_metadata(self):
        """Test creating valid metadata."""
        metadata = PDFMetadata(
            url="http://example.com/test.pdf",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size=1000,
            source_domain="example.com",
            download_timestamp=datetime.now(),
        )
        
        assert metadata.filename == "test.pdf"
        assert metadata.file_size == 1000
        assert metadata.confidence_score == 0.0
        assert metadata.procedure_type == ProcedureType.UNKNOWN
    
    def test_confidence_score_validation(self):
        """Test confidence score validation."""
        # Valid scores
        metadata = PDFMetadata(
            url="http://example.com/test.pdf",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size=1000,
            source_domain="example.com",
            download_timestamp=datetime.now(),
            confidence_score=0.75,
        )
        assert metadata.confidence_score == 0.75
        
        # Invalid score (too high)
        with pytest.raises(ValidationError):
            PDFMetadata(
                url="http://example.com/test.pdf",
                filename="test.pdf",
                file_path="/path/to/test.pdf",
                file_hash="abc123",
                file_size=1000,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                confidence_score=1.5,
            )
    
    def test_json_serialization(self):
        """Test JSON serialization."""
        metadata = PDFMetadata(
            url="http://example.com/test.pdf",
            filename="test.pdf",
            file_path="/path/to/test.pdf",
            file_hash="abc123",
            file_size=1000,
            source_domain="example.com",
            download_timestamp=datetime.now(),
            timeline_elements=["Day 1", "Week 1"],
            medication_instructions=["Take with food"],
        )
        
        json_data = metadata.dict()
        
        assert json_data["filename"] == "test.pdf"
        assert len(json_data["timeline_elements"]) == 2
        assert len(json_data["medication_instructions"]) == 1


class TestCollectionResult:
    """Tests for CollectionResult model."""
    
    def test_success_rate_calculation(self):
        """Test success rate calculation."""
        result = CollectionResult(
            total_pdfs_collected=8,
            total_urls_discovered=10,
            metadata_list=[],
            collection_timestamp=datetime.now(),
        )
        
        assert result.success_rate == 0.8
    
    def test_success_rate_zero_urls(self):
        """Test success rate with zero URLs."""
        result = CollectionResult(
            total_pdfs_collected=0,
            total_urls_discovered=0,
            metadata_list=[],
            collection_timestamp=datetime.now(),
        )
        
        assert result.success_rate == 0.0
    
    def test_grouping_by_procedure_type(self):
        """Test grouping PDFs by procedure type."""
        metadata_list = [
            PDFMetadata(
                url="http://example.com/1.pdf",
                filename="1.pdf",
                file_path="/1.pdf",
                file_hash="1",
                file_size=100,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                procedure_type=ProcedureType.CARDIAC,
            ),
            PDFMetadata(
                url="http://example.com/2.pdf",
                filename="2.pdf",
                file_path="/2.pdf",
                file_hash="2",
                file_size=100,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                procedure_type=ProcedureType.CARDIAC,
            ),
            PDFMetadata(
                url="http://example.com/3.pdf",
                filename="3.pdf",
                file_path="/3.pdf",
                file_hash="3",
                file_size=100,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                procedure_type=ProcedureType.ORTHOPEDIC,
            ),
        ]
        
        result = CollectionResult(
            total_pdfs_collected=3,
            total_urls_discovered=3,
            metadata_list=metadata_list,
            collection_timestamp=datetime.now(),
        )
        
        by_type = result.by_procedure_type
        assert by_type[ProcedureType.CARDIAC] == 2
        assert by_type[ProcedureType.ORTHOPEDIC] == 1
    
    def test_grouping_by_domain(self):
        """Test grouping PDFs by source domain."""
        metadata_list = [
            PDFMetadata(
                url="http://hospital1.com/1.pdf",
                filename="1.pdf",
                file_path="/1.pdf",
                file_hash="1",
                file_size=100,
                source_domain="hospital1.com",
                download_timestamp=datetime.now(),
            ),
            PDFMetadata(
                url="http://hospital1.com/2.pdf",
                filename="2.pdf",
                file_path="/2.pdf",
                file_hash="2",
                file_size=100,
                source_domain="hospital1.com",
                download_timestamp=datetime.now(),
            ),
            PDFMetadata(
                url="http://hospital2.com/3.pdf",
                filename="3.pdf",
                file_path="/3.pdf",
                file_hash="3",
                file_size=100,
                source_domain="hospital2.com",
                download_timestamp=datetime.now(),
            ),
        ]
        
        result = CollectionResult(
            total_pdfs_collected=3,
            total_urls_discovered=3,
            metadata_list=metadata_list,
            collection_timestamp=datetime.now(),
        )
        
        by_domain = result.by_source_domain
        assert by_domain["hospital1.com"] == 2
        assert by_domain["hospital2.com"] == 1
    
    def test_average_confidence(self):
        """Test average confidence calculation."""
        metadata_list = [
            PDFMetadata(
                url="http://example.com/1.pdf",
                filename="1.pdf",
                file_path="/1.pdf",
                file_hash="1",
                file_size=100,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                confidence_score=0.8,
            ),
            PDFMetadata(
                url="http://example.com/2.pdf",
                filename="2.pdf",
                file_path="/2.pdf",
                file_hash="2",
                file_size=100,
                source_domain="example.com",
                download_timestamp=datetime.now(),
                confidence_score=0.6,
            ),
        ]
        
        result = CollectionResult(
            total_pdfs_collected=2,
            total_urls_discovered=2,
            metadata_list=metadata_list,
            collection_timestamp=datetime.now(),
        )
        
        assert result.average_confidence == 0.7


class TestSearchQuery:
    """Tests for SearchQuery model."""
    
    def test_valid_query(self):
        """Test creating valid search query."""
        query = SearchQuery(
            query="post operative care",
            max_results=20,
            procedure_types=[ProcedureType.CARDIAC, ProcedureType.ORTHOPEDIC],
            required_keywords=["recovery", "instructions"],
            excluded_keywords=["advertisement"],
        )
        
        assert query.query == "post operative care"
        assert query.max_results == 20
        assert len(query.procedure_types) == 2
    
    def test_max_results_validation(self):
        """Test max_results validation."""
        # Valid range
        query = SearchQuery(query="test", max_results=50)
        assert query.max_results == 50
        
        # Too high
        with pytest.raises(ValidationError):
            SearchQuery(query="test", max_results=101)
        
        # Too low
        with pytest.raises(ValidationError):
            SearchQuery(query="test", max_results=0)


class TestCollectionConfig:
    """Tests for CollectionConfig model."""
    
    def test_valid_config(self):
        """Test creating valid collection config."""
        config = CollectionConfig(
            search_queries=[
                SearchQuery(query="post op care"),
                SearchQuery(query="surgery recovery"),
            ],
            direct_urls=["http://example.com/manual.pdf"],
            target_domains=["hospital.com", "clinic.org"],
            excluded_domains=["spam.com"],
            max_pdfs_total=50,
            quality_threshold=0.7,
        )
        
        assert len(config.search_queries) == 2
        assert len(config.direct_urls) == 1
        assert config.max_pdfs_total == 50
        assert config.quality_threshold == 0.7
    
    def test_quality_threshold_validation(self):
        """Test quality threshold validation."""
        # Valid threshold
        config = CollectionConfig(quality_threshold=0.8)
        assert config.quality_threshold == 0.8
        
        # Too high
        with pytest.raises(ValidationError):
            CollectionConfig(quality_threshold=1.1)
        
        # Too low
        with pytest.raises(ValidationError):
            CollectionConfig(quality_threshold=-0.1)