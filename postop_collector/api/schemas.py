"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl

from postop_collector.core.models import ContentQuality, ProcedureType


# Request schemas
class CollectionRequest(BaseModel):
    """Request schema for starting a collection."""
    
    search_queries: Optional[List[str]] = Field(
        default=None,
        description="List of search queries to use"
    )
    direct_urls: Optional[List[str]] = Field(
        default=None,
        description="List of direct URLs to collect from"
    )
    max_pdfs: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of PDFs to collect"
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score"
    )


class SearchRequest(BaseModel):
    """Request schema for searching PDFs."""
    
    query: str = Field(..., description="Search query")
    procedure_types: Optional[List[ProcedureType]] = Field(
        default=None,
        description="Filter by procedure types"
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score"
    )
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum results to return"
    )


class PDFFilterRequest(BaseModel):
    """Request schema for filtering PDFs."""
    
    procedure_type: Optional[ProcedureType] = Field(
        default=None,
        description="Filter by procedure type"
    )
    min_confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score"
    )
    source_domain: Optional[str] = Field(
        default=None,
        description="Filter by source domain"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum results to return"
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Offset for pagination"
    )


# Response schemas
class PDFResponse(BaseModel):
    """Response schema for PDF metadata."""
    
    id: Optional[int] = None
    url: str
    filename: str
    file_path: str
    file_hash: str
    file_size: int
    source_domain: str
    download_timestamp: datetime
    confidence_score: float
    procedure_type: str
    content_quality: str
    timeline_elements: List[str]
    medication_instructions: List[str]
    warning_signs: List[str]
    page_count: int
    has_images: bool
    has_tables: bool
    
    class Config:
        from_attributes = True


class CollectionRunResponse(BaseModel):
    """Response schema for collection run details."""
    
    run_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_pdfs_collected: int
    total_urls_discovered: int
    success_rate: float
    average_confidence: float
    errors: List[str]
    
    class Config:
        from_attributes = True


class CollectionStartResponse(BaseModel):
    """Response when starting a new collection."""
    
    run_id: str
    message: str
    status: str


class AnalysisResultResponse(BaseModel):
    """Response schema for analysis results."""
    
    id: int
    analysis_type: str
    analysis_version: str
    results: Dict
    confidence: float
    processing_time_ms: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class StatisticsResponse(BaseModel):
    """Response schema for database statistics."""
    
    total_pdfs: int
    total_collection_runs: int
    total_analysis_results: int
    pdfs_by_procedure: Dict[str, int]
    pdfs_by_quality: Dict[str, int]
    average_confidence: float
    total_storage_mb: float


class HealthResponse(BaseModel):
    """Response schema for health check."""
    
    status: str
    version: str
    database_connected: bool
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Response schema for errors."""
    
    error: str
    detail: Optional[str] = None
    status_code: int


class PaginatedResponse(BaseModel):
    """Base schema for paginated responses."""
    
    total: int
    limit: int
    offset: int
    has_more: bool


class PDFListResponse(PaginatedResponse):
    """Response schema for paginated PDF list."""
    
    items: List[PDFResponse]


class SearchResultResponse(BaseModel):
    """Response schema for search results."""
    
    query: str
    total_results: int
    results: List[PDFResponse]
    search_time_ms: int