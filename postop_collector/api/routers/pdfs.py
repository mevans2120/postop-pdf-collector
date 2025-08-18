"""PDF management endpoints."""

import os
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request
from fastapi.responses import FileResponse

from postop_collector.core.models import ProcedureType

from ..schemas import (
    AnalysisResultResponse,
    PDFFilterRequest,
    PDFListResponse,
    PDFResponse,
)

router = APIRouter()


@router.get("/", response_model=PDFListResponse)
async def list_pdfs(
    request: Request,
    procedure_type: Optional[ProcedureType] = Query(None, description="Filter by procedure type"),
    min_confidence: float = Query(0.5, ge=0.0, le=1.0, description="Minimum confidence score"),
    source_domain: Optional[str] = Query(None, description="Filter by source domain"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> PDFListResponse:
    """List all PDFs with optional filters."""
    db = request.app.state.db
    
    # Build filter criteria
    session = db.SessionFactory()
    try:
        from sqlalchemy import and_, func
        from postop_collector.storage.database import PDFDocument
        
        # Start query
        query = session.query(PDFDocument)
        
        # Apply filters
        filters = [PDFDocument.confidence_score >= min_confidence]
        
        if procedure_type:
            filters.append(PDFDocument.procedure_type == procedure_type.value)
        
        if source_domain:
            filters.append(PDFDocument.source_domain == source_domain)
        
        query = query.filter(and_(*filters))
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        pdfs = query.offset(offset).limit(limit).all()
        
        # Convert to response models
        items = [
            PDFResponse(
                id=pdf.id,
                url=pdf.url,
                filename=pdf.filename,
                file_path=pdf.file_path,
                file_hash=pdf.file_hash,
                file_size=pdf.file_size,
                source_domain=pdf.source_domain,
                download_timestamp=pdf.download_timestamp,
                confidence_score=pdf.confidence_score,
                procedure_type=pdf.procedure_type,
                content_quality=pdf.content_quality,
                timeline_elements=pdf.timeline_elements or [],
                medication_instructions=pdf.medication_instructions or [],
                warning_signs=pdf.warning_signs or [],
                page_count=pdf.page_count,
                has_images=pdf.has_images,
                has_tables=pdf.has_tables,
            )
            for pdf in pdfs
        ]
        
        return PDFListResponse(
            total=total,
            limit=limit,
            offset=offset,
            has_more=(offset + limit) < total,
            items=items
        )
        
    finally:
        session.close()


@router.get("/{pdf_id}", response_model=PDFResponse)
async def get_pdf(
    request: Request,
    pdf_id: int = Path(..., description="PDF ID")
) -> PDFResponse:
    """Get PDF metadata by ID."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from postop_collector.storage.database import PDFDocument
        
        pdf = session.query(PDFDocument).filter_by(id=pdf_id).first()
        
        if not pdf:
            raise HTTPException(status_code=404, detail=f"PDF with ID {pdf_id} not found")
        
        return PDFResponse(
            id=pdf.id,
            url=pdf.url,
            filename=pdf.filename,
            file_path=pdf.file_path,
            file_hash=pdf.file_hash,
            file_size=pdf.file_size,
            source_domain=pdf.source_domain,
            download_timestamp=pdf.download_timestamp,
            confidence_score=pdf.confidence_score,
            procedure_type=pdf.procedure_type,
            content_quality=pdf.content_quality,
            timeline_elements=pdf.timeline_elements or [],
            medication_instructions=pdf.medication_instructions or [],
            warning_signs=pdf.warning_signs or [],
            page_count=pdf.page_count,
            has_images=pdf.has_images,
            has_tables=pdf.has_tables,
        )
        
    finally:
        session.close()


@router.get("/{pdf_id}/download")
async def download_pdf(
    request: Request,
    pdf_id: int = Path(..., description="PDF ID")
):
    """Download PDF file by ID."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from postop_collector.storage.database import PDFDocument
        
        pdf = session.query(PDFDocument).filter_by(id=pdf_id).first()
        
        if not pdf:
            raise HTTPException(status_code=404, detail=f"PDF with ID {pdf_id} not found")
        
        # Check if file exists
        if not os.path.exists(pdf.file_path):
            raise HTTPException(status_code=404, detail="PDF file not found on disk")
        
        return FileResponse(
            path=pdf.file_path,
            media_type="application/pdf",
            filename=pdf.filename
        )
        
    finally:
        session.close()


@router.get("/{pdf_id}/analysis", response_model=List[AnalysisResultResponse])
async def get_pdf_analysis(
    request: Request,
    pdf_id: int = Path(..., description="PDF ID"),
    analysis_type: Optional[str] = Query(None, description="Filter by analysis type")
) -> List[AnalysisResultResponse]:
    """Get analysis results for a PDF."""
    db = request.app.state.db
    
    results = db.get_analysis_results(pdf_id, analysis_type)
    
    if not results:
        raise HTTPException(status_code=404, detail=f"No analysis results found for PDF {pdf_id}")
    
    return [
        AnalysisResultResponse(
            id=r["id"],
            analysis_type=r["analysis_type"],
            analysis_version=r["analysis_version"],
            results=r["results"],
            confidence=r["confidence"],
            processing_time_ms=r["processing_time_ms"],
            created_at=r["created_at"]
        )
        for r in results
    ]


@router.delete("/{pdf_id}")
async def delete_pdf(
    request: Request,
    pdf_id: int = Path(..., description="PDF ID")
):
    """Delete a PDF and its associated data."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from postop_collector.storage.database import PDFDocument
        
        pdf = session.query(PDFDocument).filter_by(id=pdf_id).first()
        
        if not pdf:
            raise HTTPException(status_code=404, detail=f"PDF with ID {pdf_id} not found")
        
        # Delete file from disk if it exists
        if os.path.exists(pdf.file_path):
            try:
                os.remove(pdf.file_path)
            except Exception as e:
                # Log error but continue with database deletion
                pass
        
        # Delete from database (cascade will handle related records)
        session.delete(pdf)
        session.commit()
        
        return {"message": f"PDF {pdf_id} deleted successfully"}
        
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()