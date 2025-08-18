"""Database operations for PDF metadata management."""

import hashlib
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, desc, func, or_
from sqlalchemy.orm import Session

from postop_collector.core.models import (
    CollectionResult,
    ContentQuality,
    PDFMetadata,
    ProcedureType,
)
from postop_collector.storage.database import (
    AnalysisResult,
    CollectionRun,
    CollectionRunPDF,
    PDFDocument,
    SearchCache,
    create_database_engine,
    get_session_factory,
    init_database,
)


class MetadataDB:
    """Database manager for PDF metadata and collection results."""
    
    def __init__(self, database_url: Optional[str] = None, environment: str = "development"):
        """Initialize the database connection.
        
        Args:
            database_url: Optional database URL. If not provided, uses environment default.
            environment: Environment name (development, testing, production)
        """
        self.engine = create_database_engine(database_url, environment)
        self.SessionFactory = get_session_factory(self.engine)
        init_database(self.engine)
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    # PDF Document Operations
    
    def save_pdf_metadata(self, metadata: PDFMetadata, session: Optional[Session] = None) -> int:
        """Save PDF metadata to database.
        
        Args:
            metadata: PDFMetadata object to save
            session: Optional session to use (for transactions)
            
        Returns:
            ID of the saved PDF document
        """
        own_session = session is None
        if own_session:
            session = self.SessionFactory()
        
        try:
            # Check if PDF already exists by file hash
            existing = session.query(PDFDocument).filter_by(
                file_hash=metadata.file_hash
            ).first()
            
            if existing:
                # Update existing record
                pdf_doc = existing
                for field, value in metadata.dict().items():
                    if field == "url":
                        value = str(value)
                    setattr(pdf_doc, field, value)
                pdf_doc.updated_at = datetime.utcnow()
            else:
                # Create new record
                pdf_data = metadata.dict()
                pdf_data["url"] = str(pdf_data["url"])
                pdf_doc = PDFDocument(**pdf_data)
                session.add(pdf_doc)
            
            if own_session:
                session.commit()
            else:
                session.flush()
            
            return pdf_doc.id
            
        except Exception as e:
            if own_session:
                session.rollback()
            raise e
        finally:
            if own_session:
                session.close()
    
    def get_pdf_by_hash(self, file_hash: str) -> Optional[PDFMetadata]:
        """Get PDF metadata by file hash.
        
        Args:
            file_hash: SHA256 hash of the PDF file
            
        Returns:
            PDFMetadata object or None if not found
        """
        session = self.SessionFactory()
        try:
            pdf_doc = session.query(PDFDocument).filter_by(file_hash=file_hash).first()
            if pdf_doc:
                return self._pdf_doc_to_metadata(pdf_doc)
            return None
        finally:
            session.close()
    
    def get_pdfs_by_procedure_type(
        self,
        procedure_type: ProcedureType,
        min_confidence: float = 0.5,
        limit: int = 100
    ) -> List[PDFMetadata]:
        """Get PDFs by procedure type.
        
        Args:
            procedure_type: Type of procedure to filter by
            min_confidence: Minimum confidence score
            limit: Maximum number of results
            
        Returns:
            List of PDFMetadata objects
        """
        session = self.SessionFactory()
        try:
            pdf_docs = session.query(PDFDocument).filter(
                and_(
                    PDFDocument.procedure_type == procedure_type.value,
                    PDFDocument.confidence_score >= min_confidence
                )
            ).order_by(desc(PDFDocument.confidence_score)).limit(limit).all()
            
            return [self._pdf_doc_to_metadata(doc) for doc in pdf_docs]
        finally:
            session.close()
    
    def search_pdfs(
        self,
        query: str,
        procedure_types: Optional[List[ProcedureType]] = None,
        min_confidence: float = 0.0,
        limit: int = 100
    ) -> List[PDFMetadata]:
        """Search PDFs by text content and filters.
        
        Args:
            query: Search query for text content
            procedure_types: Optional list of procedure types to filter
            min_confidence: Minimum confidence score
            limit: Maximum number of results
            
        Returns:
            List of PDFMetadata objects
        """
        session = self.SessionFactory()
        try:
            filters = [
                PDFDocument.text_content.contains(query),
                PDFDocument.confidence_score >= min_confidence
            ]
            
            if procedure_types:
                proc_values = [pt.value for pt in procedure_types]
                filters.append(PDFDocument.procedure_type.in_(proc_values))
            
            pdf_docs = session.query(PDFDocument).filter(
                and_(*filters)
            ).order_by(desc(PDFDocument.confidence_score)).limit(limit).all()
            
            return [self._pdf_doc_to_metadata(doc) for doc in pdf_docs]
        finally:
            session.close()
    
    # Collection Run Operations
    
    def create_collection_run(
        self,
        search_queries: List[str] = None,
        direct_urls: List[str] = None,
        config: Dict = None
    ) -> str:
        """Create a new collection run.
        
        Args:
            search_queries: List of search queries
            direct_urls: List of direct URLs
            config: Additional configuration
            
        Returns:
            Run ID for the collection run
        """
        session = self.SessionFactory()
        try:
            run_id = str(uuid.uuid4())
            
            # Extract only valid CollectionRun fields from config
            valid_fields = {"target_domains", "excluded_domains", "max_pdfs_total", "quality_threshold"}
            filtered_config = {k: v for k, v in (config or {}).items() if k in valid_fields}
            
            collection_run = CollectionRun(
                run_id=run_id,
                search_queries=search_queries or [],
                direct_urls=direct_urls or [],
                status="running",
                **filtered_config
            )
            
            session.add(collection_run)
            session.commit()
            
            return run_id
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def save_collection_result(
        self,
        run_id: str,
        result: CollectionResult
    ) -> None:
        """Save collection result to database.
        
        Args:
            run_id: Run ID for the collection
            result: CollectionResult object
        """
        session = self.SessionFactory()
        try:
            # Get collection run
            collection_run = session.query(CollectionRun).filter_by(run_id=run_id).first()
            if not collection_run:
                raise ValueError(f"Collection run {run_id} not found")
            
            # Update collection run statistics
            collection_run.total_pdfs_collected = result.total_pdfs_collected
            collection_run.total_urls_discovered = result.total_urls_discovered
            collection_run.success_rate = result.success_rate
            collection_run.average_confidence = result.average_confidence
            collection_run.completed_at = datetime.utcnow()
            collection_run.status = "completed"
            collection_run.errors = result.errors
            
            # Save each PDF metadata and link to collection run
            for idx, metadata in enumerate(result.metadata_list):
                # Save PDF metadata
                pdf_id = self.save_pdf_metadata(metadata, session)
                
                # Link to collection run
                collection_pdf = CollectionRunPDF(
                    collection_run_id=collection_run.id,
                    pdf_document_id=pdf_id,
                    collection_order=idx,
                    discovery_method="search"  # TODO: Track actual method
                )
                session.add(collection_pdf)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_collection_run(self, run_id: str) -> Optional[Dict]:
        """Get collection run details.
        
        Args:
            run_id: Run ID to retrieve
            
        Returns:
            Dictionary with collection run details or None
        """
        session = self.SessionFactory()
        try:
            collection_run = session.query(CollectionRun).filter_by(run_id=run_id).first()
            if not collection_run:
                return None
            
            # Get associated PDFs
            pdf_ids = [cp.pdf_document_id for cp in collection_run.pdfs]
            pdfs = session.query(PDFDocument).filter(PDFDocument.id.in_(pdf_ids)).all()
            
            return {
                "run_id": collection_run.run_id,
                "status": collection_run.status,
                "started_at": collection_run.started_at,
                "completed_at": collection_run.completed_at,
                "total_pdfs_collected": collection_run.total_pdfs_collected,
                "total_urls_discovered": collection_run.total_urls_discovered,
                "success_rate": collection_run.success_rate,
                "average_confidence": collection_run.average_confidence,
                "errors": collection_run.errors,
                "pdfs": [self._pdf_doc_to_metadata(pdf) for pdf in pdfs]
            }
        finally:
            session.close()
    
    # Analysis Result Operations
    
    def save_analysis_result(
        self,
        pdf_id: int,
        analysis_type: str,
        results: Dict,
        confidence: float = 0.0,
        processing_time_ms: Optional[int] = None
    ) -> None:
        """Save analysis result for a PDF.
        
        Args:
            pdf_id: ID of the PDF document
            analysis_type: Type of analysis performed
            results: Analysis results dictionary
            confidence: Confidence score
            processing_time_ms: Processing time in milliseconds
        """
        session = self.SessionFactory()
        try:
            analysis = AnalysisResult(
                pdf_document_id=pdf_id,
                analysis_type=analysis_type,
                results=results,
                confidence=confidence,
                processing_time_ms=processing_time_ms
            )
            
            session.add(analysis)
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_analysis_results(
        self,
        pdf_id: int,
        analysis_type: Optional[str] = None
    ) -> List[Dict]:
        """Get analysis results for a PDF.
        
        Args:
            pdf_id: ID of the PDF document
            analysis_type: Optional filter by analysis type
            
        Returns:
            List of analysis result dictionaries
        """
        session = self.SessionFactory()
        try:
            query = session.query(AnalysisResult).filter_by(pdf_document_id=pdf_id)
            
            if analysis_type:
                query = query.filter_by(analysis_type=analysis_type)
            
            results = query.all()
            
            return [
                {
                    "id": r.id,
                    "analysis_type": r.analysis_type,
                    "analysis_version": r.analysis_version,
                    "results": r.results,
                    "confidence": r.confidence,
                    "processing_time_ms": r.processing_time_ms,
                    "created_at": r.created_at
                }
                for r in results
            ]
        finally:
            session.close()
    
    # Cache Operations
    
    def cache_search_results(
        self,
        query: str,
        results: List[Dict],
        source: str,
        ttl_hours: int = 24
    ) -> None:
        """Cache search results.
        
        Args:
            query: Search query
            results: Search results
            source: Source of results (google, bing, etc.)
            ttl_hours: Time to live in hours
        """
        session = self.SessionFactory()
        try:
            # Generate query hash
            query_hash = hashlib.sha256(f"{query}:{source}".encode()).hexdigest()
            
            # Check if cache exists
            existing = session.query(SearchCache).filter_by(query_hash=query_hash).first()
            
            expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)
            
            if existing:
                # Update existing cache
                existing.results = results
                existing.result_count = len(results)
                existing.expires_at = expires_at
            else:
                # Create new cache entry
                cache = SearchCache(
                    query_hash=query_hash,
                    query_text=query,
                    results=results,
                    result_count=len(results),
                    source=source,
                    expires_at=expires_at
                )
                session.add(cache)
            
            session.commit()
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_cached_search_results(
        self,
        query: str,
        source: str
    ) -> Optional[List[Dict]]:
        """Get cached search results.
        
        Args:
            query: Search query
            source: Source of results
            
        Returns:
            Cached results or None if not found/expired
        """
        session = self.SessionFactory()
        try:
            query_hash = hashlib.sha256(f"{query}:{source}".encode()).hexdigest()
            
            cache = session.query(SearchCache).filter(
                and_(
                    SearchCache.query_hash == query_hash,
                    SearchCache.expires_at > datetime.utcnow()
                )
            ).first()
            
            if cache:
                return cache.results
            return None
            
        finally:
            session.close()
    
    # Statistics Operations
    
    def get_statistics(self) -> Dict:
        """Get database statistics.
        
        Returns:
            Dictionary with various statistics
        """
        session = self.SessionFactory()
        try:
            stats = {
                "total_pdfs": session.query(func.count(PDFDocument.id)).scalar(),
                "total_collection_runs": session.query(func.count(CollectionRun.id)).scalar(),
                "total_analysis_results": session.query(func.count(AnalysisResult.id)).scalar(),
                "pdfs_by_procedure": {},
                "pdfs_by_quality": {},
                "average_confidence": session.query(func.avg(PDFDocument.confidence_score)).scalar() or 0.0,
                "total_storage_bytes": session.query(func.sum(PDFDocument.file_size)).scalar() or 0,
            }
            
            # PDFs by procedure type
            proc_counts = session.query(
                PDFDocument.procedure_type,
                func.count(PDFDocument.id)
            ).group_by(PDFDocument.procedure_type).all()
            
            stats["pdfs_by_procedure"] = {proc: count for proc, count in proc_counts}
            
            # PDFs by quality
            quality_counts = session.query(
                PDFDocument.content_quality,
                func.count(PDFDocument.id)
            ).group_by(PDFDocument.content_quality).all()
            
            stats["pdfs_by_quality"] = {quality: count for quality, count in quality_counts}
            
            return stats
            
        finally:
            session.close()
    
    # Helper Methods
    
    def _pdf_doc_to_metadata(self, pdf_doc: PDFDocument) -> PDFMetadata:
        """Convert PDFDocument to PDFMetadata."""
        return PDFMetadata(
            url=pdf_doc.url,
            filename=pdf_doc.filename,
            file_path=pdf_doc.file_path,
            file_hash=pdf_doc.file_hash,
            file_size=pdf_doc.file_size,
            source_domain=pdf_doc.source_domain,
            download_timestamp=pdf_doc.download_timestamp,
            text_content=pdf_doc.text_content,
            confidence_score=pdf_doc.confidence_score,
            procedure_type=ProcedureType(pdf_doc.procedure_type),
            content_quality=ContentQuality(pdf_doc.content_quality),
            timeline_elements=pdf_doc.timeline_elements or [],
            medication_instructions=pdf_doc.medication_instructions or [],
            warning_signs=pdf_doc.warning_signs or [],
            follow_up_instructions=pdf_doc.follow_up_instructions or [],
            language=pdf_doc.language,
            page_count=pdf_doc.page_count,
            has_images=pdf_doc.has_images,
            has_tables=pdf_doc.has_tables,
        )