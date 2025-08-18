"""Tests for REST API endpoints."""

import json
import pytest
from fastapi.testclient import TestClient

from postop_collector.api import create_app
from postop_collector.config.settings import Settings
from postop_collector.core.models import PDFMetadata, ProcedureType, ContentQuality
from datetime import datetime


@pytest.fixture
def test_settings():
    """Create test settings."""
    return Settings(
        database_url="sqlite:///:memory:",
        environment="testing",
        log_level="ERROR"
    )


@pytest.fixture
def test_app(test_settings):
    """Create test FastAPI app."""
    return create_app(test_settings)


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def sample_pdf_data():
    """Create sample PDF data for testing."""
    return {
        "url": "https://example.com/test.pdf",
        "filename": "test.pdf",
        "file_path": "/tmp/test.pdf",
        "file_hash": "testhash123",
        "file_size": 1024,
        "source_domain": "example.com",
        "download_timestamp": datetime.utcnow().isoformat(),
        "confidence_score": 0.85,
        "procedure_type": "orthopedic",
        "content_quality": "high"
    }


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    def test_health_check(self, test_client):
        """Test health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database_connected" in data
    
    def test_root_endpoint(self, test_client):
        """Test root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "PostOp PDF Collector API" in data["message"]


class TestPDFEndpoints:
    """Test PDF management endpoints."""
    
    def test_list_pdfs_empty(self, test_client):
        """Test listing PDFs when database is empty."""
        response = test_client.get("/api/v1/pdfs/")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["has_more"] is False
    
    def test_list_pdfs_with_filters(self, test_client):
        """Test listing PDFs with filters."""
        response = test_client.get(
            "/api/v1/pdfs/",
            params={
                "procedure_type": "orthopedic",
                "min_confidence": 0.7,
                "limit": 10,
                "offset": 0
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
    
    def test_get_pdf_not_found(self, test_client):
        """Test getting non-existent PDF."""
        response = test_client.get("/api/v1/pdfs/999")
        assert response.status_code == 404
    
    def test_delete_pdf_not_found(self, test_client):
        """Test deleting non-existent PDF."""
        response = test_client.delete("/api/v1/pdfs/999")
        assert response.status_code == 404


class TestCollectionEndpoints:
    """Test collection management endpoints."""
    
    def test_start_collection_no_params(self, test_client):
        """Test starting collection without parameters."""
        response = test_client.post(
            "/api/v1/collection/start",
            json={}
        )
        assert response.status_code == 400
    
    def test_start_collection_with_search(self, test_client):
        """Test starting collection with search queries."""
        response = test_client.post(
            "/api/v1/collection/start",
            json={
                "search_queries": ["test query"],
                "max_pdfs": 5,
                "min_confidence": 0.5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "running"
    
    def test_list_collection_runs(self, test_client):
        """Test listing collection runs."""
        response = test_client.get("/api/v1/collection/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_get_collection_run_not_found(self, test_client):
        """Test getting non-existent collection run."""
        response = test_client.get("/api/v1/collection/runs/invalid-id")
        assert response.status_code == 404
    
    def test_stop_inactive_collection(self, test_client):
        """Test stopping inactive collection."""
        response = test_client.post("/api/v1/collection/runs/invalid-id/stop")
        assert response.status_code == 404
    
    def test_get_active_collections(self, test_client):
        """Test getting active collections."""
        response = test_client.get("/api/v1/collection/active")
        assert response.status_code == 200
        data = response.json()
        assert "active_collections" in data


class TestSearchEndpoints:
    """Test search endpoints."""
    
    def test_search_pdfs(self, test_client):
        """Test searching PDFs."""
        response = test_client.post(
            "/api/v1/search/",
            json={
                "query": "knee surgery",
                "min_confidence": 0.5,
                "limit": 20
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "query" in data
        assert data["query"] == "knee surgery"
        assert "total_results" in data
        assert "results" in data
        assert "search_time_ms" in data
    
    def test_search_with_procedure_filter(self, test_client):
        """Test searching with procedure type filter."""
        response = test_client.post(
            "/api/v1/search/",
            json={
                "query": "recovery",
                "procedure_types": ["orthopedic", "cardiac"],
                "min_confidence": 0.7,
                "limit": 10
            }
        )
        assert response.status_code == 200
    
    def test_get_cached_searches(self, test_client):
        """Test getting cached searches."""
        response = test_client.get("/api/v1/search/cache")
        assert response.status_code == 200
        data = response.json()
        assert "cached_searches" in data
    
    def test_clear_search_cache(self, test_client):
        """Test clearing search cache."""
        response = test_client.delete("/api/v1/search/cache")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data


class TestStatisticsEndpoints:
    """Test statistics endpoints."""
    
    def test_get_statistics(self, test_client):
        """Test getting statistics."""
        response = test_client.get("/api/v1/statistics/")
        assert response.status_code == 200
        data = response.json()
        assert "total_pdfs" in data
        assert "total_collection_runs" in data
        assert "pdfs_by_procedure" in data
        assert "average_confidence" in data
    
    def test_get_summary(self, test_client):
        """Test getting summary."""
        response = test_client.get("/api/v1/statistics/summary")
        assert response.status_code == 200
        data = response.json()
        assert "overview" in data
        assert "recent_activity" in data
        assert "top_sources" in data
    
    def test_get_procedure_breakdown(self, test_client):
        """Test getting procedure breakdown."""
        response = test_client.get("/api/v1/statistics/procedure-breakdown")
        assert response.status_code == 200
        data = response.json()
        assert "procedure_breakdown" in data
        assert isinstance(data["procedure_breakdown"], list)