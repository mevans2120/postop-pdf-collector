"""Configuration management for PostOp PDF Collector."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # API Keys
    google_api_key: Optional[str] = Field(
        default=None,
        env="GOOGLE_API_KEY",
        description="Google Custom Search API key"
    )
    google_search_engine_id: Optional[str] = Field(
        default=None,
        env="GOOGLE_SEARCH_ENGINE_ID",
        description="Google Custom Search Engine ID"
    )
    
    # Output configuration
    output_directory: str = Field(
        default="./output",
        env="OUTPUT_DIRECTORY",
        description="Directory to store collected PDFs and metadata"
    )
    
    # Collection limits
    max_pdfs_per_source: int = Field(
        default=10,
        env="MAX_PDFS_PER_SOURCE",
        ge=1,
        le=100,
        description="Maximum PDFs to collect from a single source"
    )
    max_pages_per_site: int = Field(
        default=50,
        env="MAX_PAGES_PER_SITE",
        ge=1,
        le=500,
        description="Maximum pages to crawl on a single website"
    )
    max_file_size_mb: int = Field(
        default=50,
        env="MAX_FILE_SIZE_MB",
        ge=1,
        le=200,
        description="Maximum PDF file size in MB"
    )
    
    # Rate limiting
    max_requests_per_second: float = Field(
        default=2.0,
        env="MAX_REQUESTS_PER_SECOND",
        ge=0.1,
        le=10.0,
        description="Maximum requests per second to a single domain"
    )
    request_timeout: int = Field(
        default=30,
        env="REQUEST_TIMEOUT",
        ge=5,
        le=120,
        description="Request timeout in seconds"
    )
    
    # Processing configuration
    enable_ocr: bool = Field(
        default=False,
        env="ENABLE_OCR",
        description="Enable OCR for scanned PDFs"
    )
    extract_images: bool = Field(
        default=True,
        env="EXTRACT_IMAGES",
        description="Extract images from PDFs"
    )
    extract_tables: bool = Field(
        default=True,
        env="EXTRACT_TABLES",
        description="Extract tables from PDFs"
    )
    
    # Quality control
    min_confidence_score: float = Field(
        default=0.5,
        env="MIN_CONFIDENCE_SCORE",
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to keep a PDF"
    )
    min_text_length: int = Field(
        default=100,
        env="MIN_TEXT_LENGTH",
        ge=0,
        description="Minimum text length in characters"
    )
    
    # Logging
    log_level: str = Field(
        default="INFO",
        env="LOG_LEVEL",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    log_file: Optional[str] = Field(
        default=None,
        env="LOG_FILE",
        description="Path to log file (None for stdout only)"
    )
    
    # Database configuration
    database_url: Optional[str] = Field(
        default=None,
        env="DATABASE_URL",
        description="Database connection URL (e.g., postgresql://user:pass@host/db or sqlite:///path/to/db.db)"
    )
    environment: str = Field(
        default="development",
        env="ENVIRONMENT",
        description="Environment name (development, testing, production)"
    )
    
    # Advanced options
    user_agent: str = Field(
        default="PostOpPDFCollector/1.0",
        env="USER_AGENT",
        description="User agent string for HTTP requests"
    )
    verify_ssl: bool = Field(
        default=True,
        env="VERIFY_SSL",
        description="Verify SSL certificates"
    )
    proxy_url: Optional[str] = Field(
        default=None,
        env="PROXY_URL",
        description="HTTP proxy URL if needed"
    )
    
    @field_validator("output_directory")
    @classmethod
    def validate_output_directory(cls, v):
        """Ensure output directory is absolute path."""
        path = Path(v)
        if not path.is_absolute():
            path = Path.cwd() / path
        return str(path)
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of {valid_levels}")
        return v.upper()
    
    @property
    def max_file_size_bytes(self) -> int:
        """Get max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"  # Allow extra fields for forward compatibility
    }


class DevelopmentSettings(Settings):
    """Development environment settings."""
    
    log_level: str = "DEBUG"
    max_pdfs_per_source: int = 5
    max_pages_per_site: int = 10
    verify_ssl: bool = False


class ProductionSettings(Settings):
    """Production environment settings."""
    
    log_level: str = "INFO"
    verify_ssl: bool = True
    min_confidence_score: float = 0.7


def get_settings() -> Settings:
    """
    Get settings based on environment.
    
    Returns:
        Settings object configured for the current environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "development":
        return DevelopmentSettings()
    else:
        return Settings()


# Singleton settings instance
settings = get_settings()