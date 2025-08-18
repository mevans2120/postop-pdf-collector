"""Statistics endpoints."""

from fastapi import APIRouter, Request

from ..schemas import StatisticsResponse

router = APIRouter()


@router.get("/", response_model=StatisticsResponse)
async def get_statistics(request: Request) -> StatisticsResponse:
    """Get database statistics."""
    db = request.app.state.db
    
    stats = db.get_statistics()
    
    return StatisticsResponse(
        total_pdfs=stats["total_pdfs"],
        total_collection_runs=stats["total_collection_runs"],
        total_analysis_results=stats["total_analysis_results"],
        pdfs_by_procedure=stats["pdfs_by_procedure"],
        pdfs_by_quality=stats["pdfs_by_quality"],
        average_confidence=stats["average_confidence"],
        total_storage_mb=stats["total_storage_bytes"] / (1024 * 1024)
    )


@router.get("/summary")
async def get_summary(request: Request):
    """Get a summary of the collection system."""
    db = request.app.state.db
    
    stats = db.get_statistics()
    
    session = db.SessionFactory()
    try:
        from sqlalchemy import desc, func
        from postop_collector.storage.database import CollectionRun, PDFDocument
        from datetime import datetime, timedelta
        
        # Get recent activity
        last_week = datetime.utcnow() - timedelta(days=7)
        
        recent_pdfs = session.query(func.count(PDFDocument.id)).filter(
            PDFDocument.created_at >= last_week
        ).scalar()
        
        recent_runs = session.query(func.count(CollectionRun.id)).filter(
            CollectionRun.started_at >= last_week
        ).scalar()
        
        # Get top domains
        top_domains = session.query(
            PDFDocument.source_domain,
            func.count(PDFDocument.id).label("count")
        ).group_by(PDFDocument.source_domain).order_by(
            desc("count")
        ).limit(5).all()
        
        # Get latest collection run
        latest_run = session.query(CollectionRun).order_by(
            desc(CollectionRun.started_at)
        ).first()
        
        return {
            "overview": {
                "total_pdfs": stats["total_pdfs"],
                "total_runs": stats["total_collection_runs"],
                "average_confidence": round(stats["average_confidence"], 2),
                "storage_mb": round(stats["total_storage_bytes"] / (1024 * 1024), 2)
            },
            "recent_activity": {
                "pdfs_last_week": recent_pdfs,
                "runs_last_week": recent_runs
            },
            "top_sources": [
                {"domain": domain, "count": count}
                for domain, count in top_domains
            ],
            "latest_run": {
                "run_id": latest_run.run_id,
                "started_at": latest_run.started_at,
                "status": latest_run.status,
                "pdfs_collected": latest_run.total_pdfs_collected
            } if latest_run else None
        }
        
    finally:
        session.close()


@router.get("/procedure-breakdown")
async def get_procedure_breakdown(request: Request):
    """Get detailed breakdown by procedure type."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from sqlalchemy import func
        from postop_collector.storage.database import PDFDocument
        
        breakdown = session.query(
            PDFDocument.procedure_type,
            func.count(PDFDocument.id).label("count"),
            func.avg(PDFDocument.confidence_score).label("avg_confidence"),
            func.avg(PDFDocument.page_count).label("avg_pages")
        ).group_by(PDFDocument.procedure_type).all()
        
        return {
            "procedure_breakdown": [
                {
                    "procedure_type": proc_type,
                    "count": count,
                    "average_confidence": round(avg_conf or 0, 2),
                    "average_pages": int(avg_pages or 0)
                }
                for proc_type, count, avg_conf, avg_pages in breakdown
            ]
        }
        
    finally:
        session.close()