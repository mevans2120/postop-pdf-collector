"""Pydantic data models for the PostOp PDF Collector."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class ProcedureType(str, Enum):
    """Types of surgical procedures."""
    
    GENERAL = "general_surgery"
    ORTHOPEDIC = "orthopedic"
    CARDIAC = "cardiac"
    NEUROLOGICAL = "neurological"
    PLASTIC = "plastic_surgery"
    DENTAL = "dental"
    OPHTHALMIC = "ophthalmic"
    GASTROINTESTINAL = "gastrointestinal"
    UROLOGICAL = "urological"
    GYNECOLOGICAL = "gynecological"
    ENT = "ent"
    VASCULAR = "vascular"
    UNKNOWN = "unknown"


class ContentQuality(str, Enum):
    """Quality assessment of PDF content."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNASSESSED = "unassessed"


class PDFMetadata(BaseModel):
    """Metadata for a collected PDF document."""
    
    # Basic information
    url: HttpUrl = Field(..., description="Source URL of the PDF")
    filename: str = Field(..., description="Filename of the saved PDF")
    file_path: str = Field(..., description="Local file path where PDF is stored")
    file_hash: str = Field(..., description="SHA256 hash of the PDF content")
    file_size: int = Field(..., description="Size of the PDF in bytes")
    
    # Source information
    source_domain: str = Field(..., description="Domain where PDF was found")
    download_timestamp: datetime = Field(..., description="When the PDF was downloaded")
    
    # Content analysis (to be filled by analysis module)
    text_content: str = Field(default="", description="Extracted text from PDF")
    confidence_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score of content relevance"
    )
    procedure_type: ProcedureType = Field(
        default=ProcedureType.UNKNOWN,
        description="Type of surgical procedure"
    )
    content_quality: ContentQuality = Field(
        default=ContentQuality.UNASSESSED,
        description="Quality assessment of content"
    )
    
    # Extracted information
    timeline_elements: List[str] = Field(
        default_factory=list,
        description="Timeline elements found in the document"
    )
    medication_instructions: List[str] = Field(
        default_factory=list,
        description="Medication instructions found"
    )
    warning_signs: List[str] = Field(
        default_factory=list,
        description="Warning signs to watch for"
    )
    follow_up_instructions: List[str] = Field(
        default_factory=list,
        description="Follow-up care instructions"
    )
    
    # Metadata
    language: str = Field(default="en", description="Language of the document")
    page_count: int = Field(default=0, description="Number of pages in PDF")
    has_images: bool = Field(default=False, description="Whether PDF contains images")
    has_tables: bool = Field(default=False, description="Whether PDF contains tables")
    
    model_config = {
        "use_enum_values": True,
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            HttpUrl: lambda v: str(v),
        }
    }


class CollectionResult(BaseModel):
    """Result of a PDF collection operation."""
    
    total_pdfs_collected: int = Field(
        ...,
        description="Total number of PDFs successfully collected"
    )
    total_urls_discovered: int = Field(
        ...,
        description="Total number of URLs discovered during collection"
    )
    metadata_list: List[PDFMetadata] = Field(
        ...,
        description="List of metadata for all collected PDFs"
    )
    collection_timestamp: datetime = Field(
        ...,
        description="When the collection was performed"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Any errors encountered during collection"
    )
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate of collection."""
        if self.total_urls_discovered == 0:
            return 0.0
        return self.total_pdfs_collected / self.total_urls_discovered
    
    @property
    def by_procedure_type(self) -> Dict[str, int]:
        """Group collected PDFs by procedure type."""
        counts = {}
        for metadata in self.metadata_list:
            proc_type = metadata.procedure_type
            counts[proc_type] = counts.get(proc_type, 0) + 1
        return counts
    
    @property
    def by_source_domain(self) -> Dict[str, int]:
        """Group collected PDFs by source domain."""
        counts = {}
        for metadata in self.metadata_list:
            domain = metadata.source_domain
            counts[domain] = counts.get(domain, 0) + 1
        return counts
    
    @property
    def average_confidence(self) -> float:
        """Calculate average confidence score."""
        if not self.metadata_list:
            return 0.0
        total = sum(m.confidence_score for m in self.metadata_list)
        return total / len(self.metadata_list)
    
    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
        }
    }


class SearchQuery(BaseModel):
    """Configuration for a search query."""
    
    query: str = Field(..., description="The search query string")
    max_results: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results to retrieve"
    )
    procedure_types: List[ProcedureType] = Field(
        default_factory=list,
        description="Filter for specific procedure types"
    )
    required_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords that must be present"
    )
    excluded_keywords: List[str] = Field(
        default_factory=list,
        description="Keywords to exclude"
    )


class CollectionConfig(BaseModel):
    """Configuration for a collection run."""
    
    search_queries: List[SearchQuery] = Field(
        default_factory=list,
        description="List of search queries to execute"
    )
    direct_urls: List[HttpUrl] = Field(
        default_factory=list,
        description="Direct URLs to collect from"
    )
    target_domains: List[str] = Field(
        default_factory=list,
        description="Specific domains to focus on"
    )
    excluded_domains: List[str] = Field(
        default_factory=list,
        description="Domains to exclude from collection"
    )
    max_pdfs_total: int = Field(
        default=100,
        ge=1,
        description="Maximum total PDFs to collect"
    )
    quality_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum quality score to keep a PDF"
    )
    
    model_config = {
        "json_encoders": {
            HttpUrl: lambda v: str(v),
        }
    }