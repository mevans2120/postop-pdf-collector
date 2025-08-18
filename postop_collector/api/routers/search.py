"""Search endpoints."""

import time
from typing import List

from fastapi import APIRouter, Request

from ..schemas import SearchRequest, SearchResultResponse, PDFResponse

router = APIRouter()


@router.post("/", response_model=SearchResultResponse)
async def search_pdfs(
    request: Request,
    search_request: SearchRequest
) -> SearchResultResponse:
    """Search PDFs by content and filters."""
    db = request.app.state.db
    
    start_time = time.time()
    
    # Perform search
    results = db.search_pdfs(
        query=search_request.query,
        procedure_types=search_request.procedure_types,
        min_confidence=search_request.min_confidence,
        limit=search_request.limit
    )
    
    search_time_ms = int((time.time() - start_time) * 1000)
    
    # Convert to response models
    pdf_responses = [
        PDFResponse(
            url=pdf.url,
            filename=pdf.filename,
            file_path=pdf.file_path,
            file_hash=pdf.file_hash,
            file_size=pdf.file_size,
            source_domain=pdf.source_domain,
            download_timestamp=pdf.download_timestamp,
            confidence_score=pdf.confidence_score,
            procedure_type=pdf.procedure_type.value if hasattr(pdf.procedure_type, 'value') else pdf.procedure_type,
            content_quality=pdf.content_quality.value if hasattr(pdf.content_quality, 'value') else pdf.content_quality,
            timeline_elements=pdf.timeline_elements,
            medication_instructions=pdf.medication_instructions,
            warning_signs=pdf.warning_signs,
            page_count=pdf.page_count,
            has_images=pdf.has_images,
            has_tables=pdf.has_tables,
        )
        for pdf in results
    ]
    
    return SearchResultResponse(
        query=search_request.query,
        total_results=len(pdf_responses),
        results=pdf_responses,
        search_time_ms=search_time_ms
    )


@router.get("/cache")
async def get_cached_searches(request: Request):
    """Get list of cached search queries."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from sqlalchemy import desc
        from postop_collector.storage.database import SearchCache
        from datetime import datetime
        
        # Get non-expired cache entries
        cache_entries = session.query(SearchCache).filter(
            SearchCache.expires_at > datetime.utcnow()
        ).order_by(desc(SearchCache.created_at)).limit(20).all()
        
        return {
            "cached_searches": [
                {
                    "query": entry.query_text,
                    "source": entry.source,
                    "result_count": entry.result_count,
                    "expires_at": entry.expires_at,
                    "created_at": entry.created_at
                }
                for entry in cache_entries
            ]
        }
        
    finally:
        session.close()


@router.delete("/cache")
async def clear_search_cache(request: Request):
    """Clear all search cache entries."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from postop_collector.storage.database import SearchCache
        
        count = session.query(SearchCache).delete()
        session.commit()
        
        return {"message": f"Cleared {count} cache entries"}
        
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()