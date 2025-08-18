"""Collection management endpoints."""

import asyncio
import uuid
from typing import Dict, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Path, Request

from postop_collector import PostOpPDFCollector
from postop_collector.config.settings import Settings

from ..schemas import (
    CollectionRequest,
    CollectionRunResponse,
    CollectionStartResponse,
)

router = APIRouter()

# Store active collection tasks
active_collections: Dict[str, asyncio.Task] = {}


async def run_collection_task(
    run_id: str,
    search_queries: Optional[list],
    direct_urls: Optional[list],
    settings: Settings,
    db_url: Optional[str]
):
    """Background task to run PDF collection."""
    try:
        # Update settings for this collection
        collection_settings = Settings(
            **settings.model_dump(),
            database_url=db_url
        )
        
        # Run collection
        async with PostOpPDFCollector(collection_settings, use_database=True) as collector:
            collector.collection_run_id = run_id  # Use existing run_id
            result = await collector.run_collection(
                search_queries=search_queries,
                direct_urls=direct_urls
            )
            
    except Exception as e:
        # Update collection status to failed
        from postop_collector.storage.metadata_db import MetadataDB
        with MetadataDB(database_url=db_url) as db:
            session = db.SessionFactory()
            try:
                from postop_collector.storage.database import CollectionRun
                
                run = session.query(CollectionRun).filter_by(run_id=run_id).first()
                if run:
                    run.status = "failed"
                    run.errors = [str(e)]
                    session.commit()
            finally:
                session.close()
    finally:
        # Remove from active collections
        if run_id in active_collections:
            del active_collections[run_id]


@router.post("/start", response_model=CollectionStartResponse)
async def start_collection(
    request: Request,
    collection_request: CollectionRequest,
    background_tasks: BackgroundTasks
) -> CollectionStartResponse:
    """Start a new PDF collection run."""
    db = request.app.state.db
    settings = request.app.state.settings
    
    # Validate request
    if not collection_request.search_queries and not collection_request.direct_urls:
        raise HTTPException(
            status_code=400,
            detail="Either search_queries or direct_urls must be provided"
        )
    
    # Create collection run
    run_id = db.create_collection_run(
        search_queries=collection_request.search_queries,
        direct_urls=collection_request.direct_urls,
        config={
            "max_pdfs_total": collection_request.max_pdfs,
            "quality_threshold": collection_request.min_confidence
        }
    )
    
    # Create and start background task
    task = asyncio.create_task(
        run_collection_task(
            run_id=run_id,
            search_queries=collection_request.search_queries,
            direct_urls=collection_request.direct_urls,
            settings=settings,
            db_url=settings.database_url
        )
    )
    
    active_collections[run_id] = task
    
    return CollectionStartResponse(
        run_id=run_id,
        message="Collection started successfully",
        status="running"
    )


@router.get("/runs", response_model=list[CollectionRunResponse])
async def list_collection_runs(
    request: Request,
    limit: int = 10,
    offset: int = 0
) -> list[CollectionRunResponse]:
    """List all collection runs."""
    db = request.app.state.db
    
    session = db.SessionFactory()
    try:
        from sqlalchemy import desc
        from postop_collector.storage.database import CollectionRun
        
        runs = session.query(CollectionRun).order_by(
            desc(CollectionRun.started_at)
        ).offset(offset).limit(limit).all()
        
        return [
            CollectionRunResponse(
                run_id=run.run_id,
                status=run.status,
                started_at=run.started_at,
                completed_at=run.completed_at,
                total_pdfs_collected=run.total_pdfs_collected,
                total_urls_discovered=run.total_urls_discovered,
                success_rate=run.success_rate or 0.0,
                average_confidence=run.average_confidence or 0.0,
                errors=run.errors or []
            )
            for run in runs
        ]
        
    finally:
        session.close()


@router.get("/runs/{run_id}", response_model=CollectionRunResponse)
async def get_collection_run(
    request: Request,
    run_id: str = Path(..., description="Collection run ID")
) -> CollectionRunResponse:
    """Get details of a specific collection run."""
    db = request.app.state.db
    
    run_details = db.get_collection_run(run_id)
    
    if not run_details:
        raise HTTPException(status_code=404, detail=f"Collection run {run_id} not found")
    
    return CollectionRunResponse(
        run_id=run_details["run_id"],
        status=run_details["status"],
        started_at=run_details["started_at"],
        completed_at=run_details["completed_at"],
        total_pdfs_collected=run_details["total_pdfs_collected"],
        total_urls_discovered=run_details["total_urls_discovered"],
        success_rate=run_details["success_rate"],
        average_confidence=run_details["average_confidence"],
        errors=run_details["errors"]
    )


@router.post("/runs/{run_id}/stop")
async def stop_collection_run(
    request: Request,
    run_id: str = Path(..., description="Collection run ID")
):
    """Stop an active collection run."""
    # Check if collection is active
    if run_id not in active_collections:
        raise HTTPException(status_code=404, detail=f"Collection run {run_id} is not active")
    
    # Cancel the task
    task = active_collections[run_id]
    task.cancel()
    
    # Update database status
    db = request.app.state.db
    session = db.SessionFactory()
    try:
        from postop_collector.storage.database import CollectionRun
        from datetime import datetime
        
        run = session.query(CollectionRun).filter_by(run_id=run_id).first()
        if run:
            run.status = "cancelled"
            run.completed_at = datetime.utcnow()
            session.commit()
    finally:
        session.close()
    
    # Remove from active collections
    del active_collections[run_id]
    
    return {"message": f"Collection run {run_id} stopped successfully"}


@router.get("/active")
async def get_active_collections():
    """Get list of currently active collection runs."""
    active = []
    for run_id, task in active_collections.items():
        active.append({
            "run_id": run_id,
            "status": "running" if not task.done() else "completed"
        })
    
    return {"active_collections": active}