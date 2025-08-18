"""Database models and schema for PDF metadata persistence."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class PDFDocument(Base):
    """Database model for storing PDF document metadata."""
    
    __tablename__ = "pdf_documents"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Basic information
    url = Column(String(2048), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(1024), nullable=False)
    file_hash = Column(String(64), nullable=False, unique=True, index=True)
    file_size = Column(Integer, nullable=False)
    
    # Source information
    source_domain = Column(String(255), nullable=False, index=True)
    download_timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Content analysis
    text_content = Column(Text, default="")
    confidence_score = Column(Float, default=0.0, index=True)
    procedure_type = Column(String(50), default="unknown", index=True)
    content_quality = Column(String(20), default="unassessed")
    
    # Extracted information (stored as JSON)
    timeline_elements = Column(JSON, default=list)
    medication_instructions = Column(JSON, default=list)
    warning_signs = Column(JSON, default=list)
    follow_up_instructions = Column(JSON, default=list)
    
    # Metadata
    language = Column(String(10), default="en")
    page_count = Column(Integer, default=0)
    has_images = Column(Boolean, default=False)
    has_tables = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    collection_runs = relationship("CollectionRunPDF", back_populates="pdf_document")
    analysis_results = relationship("AnalysisResult", back_populates="pdf_document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PDFDocument(id={self.id}, filename='{self.filename}', procedure_type='{self.procedure_type}')>"


class CollectionRun(Base):
    """Database model for tracking collection runs."""
    
    __tablename__ = "collection_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Run information
    run_id = Column(String(36), nullable=False, unique=True, index=True)
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Configuration
    search_queries = Column(JSON, default=list)
    direct_urls = Column(JSON, default=list)
    target_domains = Column(JSON, default=list)
    excluded_domains = Column(JSON, default=list)
    max_pdfs_total = Column(Integer, default=100)
    quality_threshold = Column(Float, default=0.5)
    
    # Results
    total_pdfs_collected = Column(Integer, default=0)
    total_urls_discovered = Column(Integer, default=0)
    success_rate = Column(Float, default=0.0)
    average_confidence = Column(Float, default=0.0)
    
    # Errors and status
    status = Column(String(20), default="pending")  # pending, running, completed, failed
    errors = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pdfs = relationship("CollectionRunPDF", back_populates="collection_run", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<CollectionRun(id={self.id}, run_id='{self.run_id}', status='{self.status}')>"


class CollectionRunPDF(Base):
    """Association table linking collection runs to PDFs."""
    
    __tablename__ = "collection_run_pdfs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    collection_run_id = Column(Integer, ForeignKey("collection_runs.id"), nullable=False)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    
    # Additional metadata for this specific collection
    collection_order = Column(Integer, nullable=False)
    discovery_method = Column(String(50))  # search, crawl, direct_url
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    collection_run = relationship("CollectionRun", back_populates="pdfs")
    pdf_document = relationship("PDFDocument", back_populates="collection_runs")
    
    def __repr__(self):
        return f"<CollectionRunPDF(run_id={self.collection_run_id}, pdf_id={self.pdf_document_id})>"


class AnalysisResult(Base):
    """Database model for storing detailed analysis results."""
    
    __tablename__ = "analysis_results"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pdf_document_id = Column(Integer, ForeignKey("pdf_documents.id"), nullable=False)
    
    # Analysis type and version
    analysis_type = Column(String(50), nullable=False)  # timeline, medication, procedure, etc.
    analysis_version = Column(String(20), nullable=False, default="1.0.0")
    
    # Results (stored as JSON for flexibility)
    results = Column(JSON, nullable=False)
    
    # Metadata
    confidence = Column(Float, default=0.0)
    processing_time_ms = Column(Integer)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    pdf_document = relationship("PDFDocument", back_populates="analysis_results")
    
    def __repr__(self):
        return f"<AnalysisResult(id={self.id}, type='{self.analysis_type}', pdf_id={self.pdf_document_id})>"


class SearchCache(Base):
    """Database model for caching search results."""
    
    __tablename__ = "search_cache"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Cache key
    query_hash = Column(String(64), nullable=False, unique=True, index=True)
    query_text = Column(Text, nullable=False)
    
    # Results
    results = Column(JSON, nullable=False)
    result_count = Column(Integer, nullable=False)
    
    # Metadata
    source = Column(String(50), nullable=False)  # google, bing, crawl, etc.
    expires_at = Column(DateTime, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SearchCache(id={self.id}, query_hash='{self.query_hash}', source='{self.source}')>"


def get_database_url(environment: str = "development") -> str:
    """Get database URL based on environment."""
    import os
    
    if environment == "production":
        # Use PostgreSQL in production
        return os.getenv(
            "DATABASE_URL",
            "postgresql://user:password@localhost/postop_collector"
        )
    elif environment == "testing":
        # Use in-memory SQLite for tests
        return "sqlite:///:memory:"
    else:
        # Use local SQLite for development
        db_path = os.getenv("SQLITE_PATH", "./data/postop_collector.db")
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return f"sqlite:///{db_path}"


def create_database_engine(database_url: Optional[str] = None, environment: str = "development"):
    """Create database engine with appropriate configuration."""
    if database_url is None:
        database_url = get_database_url(environment)
    
    # Different configurations for different database types
    if database_url.startswith("sqlite"):
        # SQLite specific configurations
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},  # Needed for SQLite
            echo=environment == "development",  # Log SQL in development
        )
    else:
        # PostgreSQL specific configurations
        engine = create_engine(
            database_url,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections before using
            echo=environment == "development",
        )
    
    return engine


def init_database(engine):
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_session_factory(engine):
    """Get SQLAlchemy session factory."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)