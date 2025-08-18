"""Tests for database operations."""

import os
import tempfile
import uuid
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from postop_collector.core.models import (
    CollectionResult,
    ContentQuality,
    PDFMetadata,
    ProcedureType,
)
from postop_collector.storage.database import (
    Base,
    PDFDocument,
    init_database,
)
from postop_collector.storage.metadata_db import MetadataDB


@pytest.fixture
def test_db():
    """Create a test database."""
    # Use in-memory database for tests
    with MetadataDB(database_url="sqlite:///:memory:", environment="testing") as db:
        yield db


@pytest.fixture
def sample_pdf_metadata():
    """Create sample PDF metadata."""
    return PDFMetadata(
        url="https://example.com/surgery-guide.pdf",
        filename="surgery-guide.pdf",
        file_path="/tmp/surgery-guide.pdf",
        file_hash="abc123def456",
        file_size=1024000,
        source_domain="example.com",
        download_timestamp=datetime.utcnow(),
        text_content="Post-operative care instructions for knee replacement surgery.",
        confidence_score=0.85,
        procedure_type=ProcedureType.ORTHOPEDIC,
        content_quality=ContentQuality.HIGH,
        timeline_elements=["Day 1-3: Rest", "Week 1-2: Light walking"],
        medication_instructions=["Take pain medication as needed"],
        warning_signs=["Fever above 101F", "Excessive bleeding"],
        follow_up_instructions=["Follow up in 2 weeks"],
        language="en",
        page_count=5,
        has_images=True,
        has_tables=False,
    )


class TestPDFDocumentOperations:
    """Test PDF document database operations."""
    
    def test_save_pdf_metadata(self, test_db, sample_pdf_metadata):
        """Test saving PDF metadata."""
        pdf_id = test_db.save_pdf_metadata(sample_pdf_metadata)
        assert pdf_id is not None
        assert isinstance(pdf_id, int)
    
    def test_get_pdf_by_hash(self, test_db, sample_pdf_metadata):
        """Test retrieving PDF by hash."""
        # Save PDF
        test_db.save_pdf_metadata(sample_pdf_metadata)
        
        # Retrieve by hash
        retrieved = test_db.get_pdf_by_hash(sample_pdf_metadata.file_hash)
        assert retrieved is not None
        assert retrieved.file_hash == sample_pdf_metadata.file_hash
        assert retrieved.filename == sample_pdf_metadata.filename
        assert retrieved.procedure_type == sample_pdf_metadata.procedure_type
    
    def test_duplicate_pdf_hash(self, test_db, sample_pdf_metadata):
        """Test handling duplicate PDF hashes."""
        # Save PDF twice
        pdf_id1 = test_db.save_pdf_metadata(sample_pdf_metadata)
        
        # Modify and save again with same hash
        sample_pdf_metadata.confidence_score = 0.95
        pdf_id2 = test_db.save_pdf_metadata(sample_pdf_metadata)
        
        # Should update the same record
        assert pdf_id1 == pdf_id2
        
        # Check updated value
        retrieved = test_db.get_pdf_by_hash(sample_pdf_metadata.file_hash)
        assert retrieved.confidence_score == 0.95
    
    def test_get_pdfs_by_procedure_type(self, test_db):
        """Test retrieving PDFs by procedure type."""
        # Create multiple PDFs with different procedure types
        for i, proc_type in enumerate([
            ProcedureType.ORTHOPEDIC,
            ProcedureType.ORTHOPEDIC,
            ProcedureType.CARDIAC,
            ProcedureType.DENTAL,
        ]):
            metadata = PDFMetadata(
                url=f"https://example.com/pdf-{i}.pdf",
                filename=f"pdf-{i}.pdf",
                file_path=f"/tmp/pdf-{i}.pdf",
                file_hash=f"hash-{i}",
                file_size=1024 * (i + 1),
                source_domain="example.com",
                download_timestamp=datetime.utcnow(),
                procedure_type=proc_type,
                confidence_score=0.5 + (i * 0.1),
            )
            test_db.save_pdf_metadata(metadata)
        
        # Get orthopedic PDFs
        ortho_pdfs = test_db.get_pdfs_by_procedure_type(
            ProcedureType.ORTHOPEDIC,
            min_confidence=0.5
        )
        assert len(ortho_pdfs) == 2
        
        # Get cardiac PDFs
        cardiac_pdfs = test_db.get_pdfs_by_procedure_type(
            ProcedureType.CARDIAC,
            min_confidence=0.0
        )
        assert len(cardiac_pdfs) == 1
    
    def test_search_pdfs(self, test_db):
        """Test searching PDFs by content."""
        # Create PDFs with different content
        pdfs_data = [
            ("knee replacement surgery", ProcedureType.ORTHOPEDIC, 0.9),
            ("cardiac bypass recovery", ProcedureType.CARDIAC, 0.85),
            ("knee arthroscopy care", ProcedureType.ORTHOPEDIC, 0.7),
            ("dental extraction aftercare", ProcedureType.DENTAL, 0.8),
        ]
        
        for i, (content, proc_type, confidence) in enumerate(pdfs_data):
            metadata = PDFMetadata(
                url=f"https://example.com/pdf-{i}.pdf",
                filename=f"pdf-{i}.pdf",
                file_path=f"/tmp/pdf-{i}.pdf",
                file_hash=f"search-hash-{i}",
                file_size=1024,
                source_domain="example.com",
                download_timestamp=datetime.utcnow(),
                text_content=content,
                procedure_type=proc_type,
                confidence_score=confidence,
            )
            test_db.save_pdf_metadata(metadata)
        
        # Search for knee-related PDFs
        knee_pdfs = test_db.search_pdfs("knee", min_confidence=0.6)
        assert len(knee_pdfs) == 2
        
        # Search with procedure type filter
        ortho_pdfs = test_db.search_pdfs(
            "surgery",
            procedure_types=[ProcedureType.ORTHOPEDIC],
            min_confidence=0.8
        )
        assert len(ortho_pdfs) == 1


class TestCollectionRunOperations:
    """Test collection run database operations."""
    
    def test_create_collection_run(self, test_db):
        """Test creating a collection run."""
        run_id = test_db.create_collection_run(
            search_queries=["post op care", "surgery recovery"],
            direct_urls=["https://example.com/guide.pdf"],
            config={"max_pdfs_total": 50}
        )
        
        assert run_id is not None
        assert isinstance(run_id, str)
        
        # Verify run was created
        run_details = test_db.get_collection_run(run_id)
        assert run_details is not None
        assert run_details["status"] == "running"
        assert len(run_details["pdfs"]) == 0
    
    def test_save_collection_result(self, test_db, sample_pdf_metadata):
        """Test saving collection results."""
        # Create collection run
        run_id = test_db.create_collection_run()
        
        # Create collection result
        result = CollectionResult(
            total_pdfs_collected=2,
            total_urls_discovered=10,
            metadata_list=[
                sample_pdf_metadata,
                PDFMetadata(
                    url="https://example.com/another.pdf",
                    filename="another.pdf",
                    file_path="/tmp/another.pdf",
                    file_hash="xyz789",
                    file_size=2048000,
                    source_domain="example.com",
                    download_timestamp=datetime.utcnow(),
                    procedure_type=ProcedureType.CARDIAC,
                    confidence_score=0.75,
                ),
            ],
            collection_timestamp=datetime.utcnow(),
            errors=["Failed to download 1 PDF"],
        )
        
        # Save result
        test_db.save_collection_result(run_id, result)
        
        # Verify saved data
        run_details = test_db.get_collection_run(run_id)
        assert run_details["status"] == "completed"
        assert run_details["total_pdfs_collected"] == 2
        assert run_details["total_urls_discovered"] == 10
        assert len(run_details["pdfs"]) == 2
        assert len(run_details["errors"]) == 1


class TestAnalysisResultOperations:
    """Test analysis result database operations."""
    
    def test_save_analysis_result(self, test_db, sample_pdf_metadata):
        """Test saving analysis results."""
        # Save PDF first
        pdf_id = test_db.save_pdf_metadata(sample_pdf_metadata)
        
        # Save analysis result
        analysis_results = {
            "timeline": [
                {"day": 1, "instruction": "Rest"},
                {"day": 7, "instruction": "Start walking"},
            ],
            "milestones": ["wound_check", "suture_removal"],
        }
        
        test_db.save_analysis_result(
            pdf_id=pdf_id,
            analysis_type="timeline",
            results=analysis_results,
            confidence=0.9,
            processing_time_ms=150,
        )
        
        # Retrieve analysis results
        results = test_db.get_analysis_results(pdf_id)
        assert len(results) == 1
        assert results[0]["analysis_type"] == "timeline"
        assert results[0]["confidence"] == 0.9
        assert "timeline" in results[0]["results"]
    
    def test_multiple_analysis_results(self, test_db, sample_pdf_metadata):
        """Test saving multiple analysis results for same PDF."""
        pdf_id = test_db.save_pdf_metadata(sample_pdf_metadata)
        
        # Save multiple analysis results
        test_db.save_analysis_result(
            pdf_id=pdf_id,
            analysis_type="timeline",
            results={"events": 10},
            confidence=0.85,
        )
        
        test_db.save_analysis_result(
            pdf_id=pdf_id,
            analysis_type="medication",
            results={"medications": 5},
            confidence=0.92,
        )
        
        # Get all results
        all_results = test_db.get_analysis_results(pdf_id)
        assert len(all_results) == 2
        
        # Get specific type
        timeline_results = test_db.get_analysis_results(pdf_id, "timeline")
        assert len(timeline_results) == 1
        assert timeline_results[0]["analysis_type"] == "timeline"


class TestCacheOperations:
    """Test cache database operations."""
    
    def test_cache_search_results(self, test_db):
        """Test caching search results."""
        query = "post operative care"
        results = [
            {"url": "https://example.com/1.pdf", "title": "Care Guide"},
            {"url": "https://example.com/2.pdf", "title": "Recovery Tips"},
        ]
        
        # Cache results
        test_db.cache_search_results(query, results, "google", ttl_hours=24)
        
        # Retrieve cached results
        cached = test_db.get_cached_search_results(query, "google")
        assert cached is not None
        assert len(cached) == 2
        assert cached[0]["url"] == results[0]["url"]
    
    def test_cache_expiration(self, test_db):
        """Test cache expiration."""
        query = "surgery recovery"
        results = [{"url": "https://example.com/guide.pdf"}]
        
        # Cache with 0 hours TTL (already expired)
        test_db.cache_search_results(query, results, "bing", ttl_hours=0)
        
        # Try to retrieve (should be None due to expiration)
        cached = test_db.get_cached_search_results(query, "bing")
        assert cached is None
    
    def test_cache_update(self, test_db):
        """Test updating cached results."""
        query = "knee surgery"
        
        # Initial cache
        initial_results = [{"url": "https://example.com/old.pdf"}]
        test_db.cache_search_results(query, initial_results, "google", ttl_hours=24)
        
        # Update cache
        updated_results = [
            {"url": "https://example.com/new1.pdf"},
            {"url": "https://example.com/new2.pdf"},
        ]
        test_db.cache_search_results(query, updated_results, "google", ttl_hours=24)
        
        # Retrieve should get updated results
        cached = test_db.get_cached_search_results(query, "google")
        assert len(cached) == 2
        assert cached[0]["url"] == updated_results[0]["url"]


class TestStatistics:
    """Test statistics operations."""
    
    def test_get_statistics(self, test_db):
        """Test getting database statistics."""
        # Add some test data
        for i in range(5):
            metadata = PDFMetadata(
                url=f"https://example.com/pdf-{i}.pdf",
                filename=f"pdf-{i}.pdf",
                file_path=f"/tmp/pdf-{i}.pdf",
                file_hash=f"stats-hash-{i}",
                file_size=1024 * (i + 1),
                source_domain="example.com",
                download_timestamp=datetime.utcnow(),
                procedure_type=ProcedureType.ORTHOPEDIC if i % 2 == 0 else ProcedureType.CARDIAC,
                content_quality=ContentQuality.HIGH if i < 3 else ContentQuality.MEDIUM,
                confidence_score=0.5 + (i * 0.1),
            )
            test_db.save_pdf_metadata(metadata)
        
        # Create a collection run
        run_id = test_db.create_collection_run()
        
        # Get statistics
        stats = test_db.get_statistics()
        
        assert stats["total_pdfs"] == 5
        assert stats["total_collection_runs"] == 1
        assert stats["pdfs_by_procedure"][ProcedureType.ORTHOPEDIC.value] == 3
        assert stats["pdfs_by_procedure"][ProcedureType.CARDIAC.value] == 2
        assert stats["pdfs_by_quality"][ContentQuality.HIGH.value] == 3
        assert stats["pdfs_by_quality"][ContentQuality.MEDIUM.value] == 2
        assert stats["average_confidence"] > 0
        assert stats["total_storage_bytes"] == sum(1024 * (i + 1) for i in range(5))