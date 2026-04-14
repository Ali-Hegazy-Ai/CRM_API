"""
Production CRM API - FastAPI Implementation

A realistic, intentionally messy CRM API for data engineering testing.
"""

from fastapi import FastAPI, Query, HTTPException, Path
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional
from datetime import datetime
import uvicorn

from cdc_store import cdc_store
from data_loader import data_loader
from pagination import (
    paginate_data,
    paginate_with_wrapper,
    paginate_contacts,
    paginate_leads,
    paginate_activities,
    paginate_companies
)
from search import search_entities
from events import generate_events
from stream_engine import (
    start_stream_engine,
    stop_stream_engine,
    refresh_stream_state,
    get_recent_changes,
    get_batch_export,
    list_entities,
    sse_event_generator,
)
from runtime_generator import (
    start_runtime_generator,
    stop_runtime_generator,
    get_runtime_generator_config,
    get_runtime_generator_metrics,
)


# Initialize FastAPI app
app = FastAPI(
    title="Production CRM API",
    description="A realistic, intentionally messy CRM API for data engineering testing",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.on_event("startup")
async def on_startup():
    """Initialize CDC/stream state and start runtime generator loops."""
    await start_stream_engine()
    await start_runtime_generator()


@app.on_event("shutdown")
async def on_shutdown():
    """Stop runtime generator and stream tasks cleanly."""
    await stop_runtime_generator()
    await stop_stream_engine()


# Custom exception handler
@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(
        status_code=404,
        content={
            "error": "not_found",
            "message": "Resource not found",
            "status": 404,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """API root - returns basic info"""
    runtime_generator = get_runtime_generator_config()
    return {
        "name": "Production CRM API",
        "version": "3.0.0",
        "description": "A realistic, messy CRM API for data engineering testing",
        "endpoints": {
            "customers": "/customers",
            "contacts": "/contacts",
            "leads": "/leads",
            "deals": "/deals",
            "activities": "/activities",
            "notes": "/notes",
            "companies": "/companies",
            "owners": "/owners",
            "pipeline_stages": "/pipeline-stages",
            "sync_status": "/sync-status",
            "metadata": "/metadata",
            "search": "/search?q=query",
            "events": "/events",
            "changes": "/changes?since=event_id_or_timestamp",
            "stream_changes": "/stream/changes",
            "stream_events": "/stream/events",
            "metrics": "/metrics",
            "batch_export": "/batch/export"
        },
        "versioning": "Add ?version=v1, ?version=v2, or ?version=v3",
        "pagination": "Add ?page=1&limit=20",
        "runtime_generator": {
            "interval_seconds": runtime_generator.get("interval_seconds"),
            "max_ops_per_cycle": runtime_generator.get("max_ops_per_cycle"),
            "incremental_query": "Add ?updated_after=ISO_TIMESTAMP&include_deleted=false to list endpoints",
        },
        "docs": "/docs"
    }


async def _load_entity_list_data(
    entity: str,
    version: str,
    updated_after: Optional[str],
    include_deleted: bool,
):
    try:
        return await list_entities(
            entity=entity,
            version=version,
            updated_after=updated_after,
            include_deleted=include_deleted,
            limit=50000,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ============================================================================
# CUSTOMERS ENDPOINTS
# ============================================================================

@app.get("/customers")
async def list_customers(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all customers with pagination
    
    Returns customers with intentional data quality issues:
    - Duplicate IDs
    - Missing fields
    - Inconsistent formatting
    - Invalid data
    """
    data = await _load_entity_list_data("customers", version, updated_after, include_deleted)
    if updated_after:
        return paginate_with_wrapper(data, page, limit, wrapper_key="data", add_issues=False)
    return paginate_with_wrapper(data, page, limit, wrapper_key="data")


@app.get("/customers/{customer_id}")
async def get_customer(
    customer_id: str = Path(..., description="Customer ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single customer by ID"""
    record = data_loader.get_record_by_id("customers", customer_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Customer {customer_id} not found"
        )
    
    return record


# ============================================================================
# CONTACTS ENDPOINTS
# ============================================================================

@app.get("/contacts")
async def list_contacts(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all contacts with pagination
    
    Returns contacts with intentional data quality issues:
    - Duplicate IDs
    - Field name variations (first_name vs firstName)
    - Invalid emails
    - Missing values
    """
    data = await _load_entity_list_data("contacts", version, updated_after, include_deleted)
    if updated_after:
        page_data, metadata = paginate_data(data, page, limit, add_issues=False)
        return {
            "contacts": page_data,
            "count": len(page_data),
            "page": metadata.page
        }
    return paginate_contacts(data, page, limit)


@app.get("/contacts/{contact_id}")
async def get_contact(
    contact_id: str = Path(..., description="Contact ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single contact by ID"""
    record = data_loader.get_record_by_id("contacts", contact_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Contact {contact_id} not found"
        )
    
    return record


# ============================================================================
# LEADS ENDPOINTS
# ============================================================================

@app.get("/leads")
async def list_leads(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all leads with pagination
    
    Returns leads with intentional data quality issues:
    - Duplicate IDs
    - Field name variations (lead_status vs leadStatus)
    - Missing scores
    - Invalid emails
    """
    data = await _load_entity_list_data("leads", version, updated_after, include_deleted)
    if updated_after:
        page_data, metadata = paginate_data(data, page, limit, add_issues=False)
        return {
            "results": page_data,
            "total_count": metadata.total,
            "page": metadata.page,
            "next_page": f"/leads?page={metadata.next_page}" if metadata.next_page else None
        }
    return paginate_leads(data, page, limit)


@app.get("/leads/{lead_id}")
async def get_lead(
    lead_id: str = Path(..., description="Lead ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single lead by ID"""
    record = data_loader.get_record_by_id("leads", lead_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Lead {lead_id} not found"
        )
    
    return record


# ============================================================================
# DEALS ENDPOINTS
# ============================================================================

@app.get("/deals")
async def list_deals(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all deals with pagination
    
    Returns deals with intentional data quality issues:
    - Duplicate IDs
    - Mixed contact representations (nested vs flat)
    - Type inconsistencies (amount as string vs number)
    - Currency casing variations
    """
    data = await _load_entity_list_data("deals", version, updated_after, include_deleted)
    if updated_after:
        return paginate_with_wrapper(data, page, limit, wrapper_key="data", add_issues=False)
    return paginate_with_wrapper(data, page, limit, wrapper_key="data")


@app.get("/deals/{deal_id}")
async def get_deal(
    deal_id: str = Path(..., description="Deal ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single deal by ID"""
    record = data_loader.get_record_by_id("deals", deal_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Deal {deal_id} not found"
        )
    
    return record


# ============================================================================
# ACTIVITIES ENDPOINTS
# ============================================================================

@app.get("/activities")
async def list_activities(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all activities with pagination
    
    Returns activities with intentional data quality issues:
    - Type casing variations (call vs CALL)
    - Status casing variations
    - Missing fields
    - Date format inconsistencies
    """
    data = await _load_entity_list_data("activities", version, updated_after, include_deleted)
    if updated_after:
        page_data, metadata = paginate_data(data, page, limit, add_issues=False)
        return {
            "activities": page_data,
            "count": len(page_data),
            "page": metadata.page,
            "per_page": metadata.limit
        }
    return paginate_activities(data, page, limit)


@app.get("/activities/{activity_id}")
async def get_activity(
    activity_id: str = Path(..., description="Activity ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single activity by ID"""
    record = data_loader.get_record_by_id("activities", activity_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Activity {activity_id} not found"
        )
    
    return record


# ============================================================================
# NOTES ENDPOINTS
# ============================================================================

@app.get("/notes")
async def list_notes(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all notes with pagination
    
    Returns notes with intentional data quality issues:
    - Null titles
    - Empty content
    - Field name variations
    - Missing fields
    """
    data = await _load_entity_list_data("notes", version, updated_after, include_deleted)
    
    # Notes use simple wrapper
    page_data = paginate_with_wrapper(
        data,
        page,
        limit,
        wrapper_key="data",
        add_issues=False if updated_after else True,
    )
    
    return {
        "data": page_data.get("data", []),
        "total": len(data)
    }


# ============================================================================
# COMPANIES ENDPOINTS
# ============================================================================

@app.get("/companies")
async def list_companies(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    updated_after: Optional[str] = Query(None, description="Optional incremental filter by updated_at"),
    include_deleted: bool = Query(False, description="Include soft-deleted records in incremental reads"),
):
    """
    List all companies with pagination
    
    Returns companies with intentional data quality issues:
    - Duplicate IDs
    - Address structure variations (nested vs flat)
    - Type inconsistencies (employee_count)
    - Industry casing variations
    """
    data = await _load_entity_list_data("companies", version, updated_after, include_deleted)
    if updated_after:
        page_data, metadata = paginate_data(data, page, limit, add_issues=False)
        return {
            "companies": page_data,
            "total_count": metadata.total,
            "page_number": metadata.page,
            "page_size": metadata.limit
        }
    return paginate_companies(data, page, limit)


@app.get("/companies/{company_id}")
async def get_company(
    company_id: str = Path(..., description="Company ID"),
    version: str = Query("v3", description="Data version (v1, v2, v3)")
):
    """Get a single company by ID"""
    record = data_loader.get_record_by_id("companies", company_id, version)
    
    if not record:
        raise HTTPException(
            status_code=404,
            detail=f"Company {company_id} not found"
        )
    
    return record


# ============================================================================
# SUPPORTING ENDPOINTS
# ============================================================================

@app.get("/owners")
async def list_owners():
    """
    List all owners (sales reps, account managers)
    
    Returns bare array (no wrapper) with field name variations
    """
    return data_loader.get_static_data("owners")


@app.get("/pipeline-stages")
async def list_pipeline_stages():
    """List all pipeline stages for deals"""
    stages = data_loader.get_static_data("pipeline_stages")
    return {"stages": stages}


@app.get("/sync-status")
async def get_sync_status():
    """Get sync health status by source system"""
    sync_status = data_loader.get_static_data("sync_status")
    return {
        "sync_status": sync_status,
        "last_updated": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/metadata")
async def get_metadata():
    """Get API schema metadata"""
    return {
        "entities": {
            "customers": {
                "fields": [
                    {"name": "id", "type": "string", "required": True},
                    {"name": "external_id", "type": "string", "required": False},
                    {"name": "customer_id", "type": "string", "required": True},
                    {"name": "name", "type": "string", "required": True},
                    {"name": "email", "type": "string", "required": False},
                    {"name": "status", "type": "string", "required": True},
                    {"name": "created_at", "type": "datetime", "required": True}
                ],
                "relationships": {
                    "company_id": "companies",
                    "owner_id": "owners"
                }
            },
            "contacts": {
                "fields": [
                    {"name": "id", "type": "string", "required": True},
                    {"name": "first_name", "type": "string", "required": True},
                    {"name": "last_name", "type": "string", "required": False},
                    {"name": "email", "type": "string", "required": False}
                ],
                "relationships": {
                    "company_id": "companies",
                    "customer_id": "customers",
                    "owner_id": "owners"
                }
            }
        },
        "version": "3.0.0",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type")
):
    """
    Search across all entities
    
    Searches in: customers, contacts, leads, deals, activities, notes, companies
    """
    if not q or len(q) < 2:
        raise HTTPException(
            status_code=400,
            detail="Search query must be at least 2 characters"
        )
    
    return search_entities(q, version, entity_type)


@app.get("/events")
async def list_events(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=100, description="Records per page")
):
    """
    Get change event log
    
    Returns events showing data changes across versions
    """
    events = generate_events(version, limit)
    
    return {
        "events": events,
        "total": len(events),
        "page": page
    }


@app.get("/changes")
async def changes(
    since: Optional[str] = Query(None, description="Cursor (event_id or timestamp). Returns newer events only"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of events to return"),
    entity_type: Optional[str] = Query(None, description="Optional entity type filter"),
    operation: Optional[str] = Query(None, description="Optional operation filter: create, update, delete"),
):
    """
    Deterministic CDC change feed.

    Uses an append-only persisted event log and returns events strictly after
    the provided cursor.
    """
    try:
        events = await get_recent_changes(
            limit=limit,
            entity=entity_type,
            event_type=operation,
            since=since,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    next_cursor = since
    if len(events) > 0:
        next_cursor = str(events[-1].get("event_id"))

    return {
        "events": events,
        "count": len(events),
        "next_cursor": next_cursor,
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/stream/changes")
async def stream_changes(
    limit: int = Query(100, ge=1, le=500, description="How many recent changes to return"),
    entity: Optional[str] = Query(None, description="Optional entity filter"),
    event_type: Optional[str] = Query(None, description="Optional event_type filter"),
    since: Optional[str] = Query(None, description="Return only events after this timestamp"),
):
    """
    Polling-friendly change feed.

    Returns recent persisted CDC events.
    """
    try:
        events = await get_recent_changes(limit=limit, entity=entity, event_type=event_type, since=since)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "events": events,
        "count": len(events),
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }


@app.get("/batch/export")
async def batch_export(
    version: str = Query("v3", description="Data version (v1, v2, v3)"),
    include_static: bool = Query(True, description="Include static reference data"),
):
    """
    Batch snapshot export for ETL and reconciliation tests.

    Returns a point-in-time export of the current in-memory dataset.
    """
    return await get_batch_export(version=version, include_static=include_static)


@app.get("/stream/events")
async def stream_events(
    limit: int = Query(100, ge=1, le=500, description="Initial backlog size before live stream")
):
    """
    Optional SSE endpoint for near-real-time event streaming.

    Keep-alive frames are emitted while idle so serverless proxies don't
    prematurely close quiet connections.
    """
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no"
    }
    return StreamingResponse(
        sse_event_generator(limit=limit),
        media_type="text/event-stream",
        headers=headers
    )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "3.0.0"
    }


@app.get("/metrics")
async def metrics():
    """Operational metrics for runtime generation and CDC state."""
    generator_metrics = get_runtime_generator_metrics()
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "generator": generator_metrics,
        "current_state_count": cdc_store.count_current_state(),
        "last_event_id": cdc_store.get_last_event_id(),
    }


@app.post("/reload")
async def reload_data():
    """Reload data from disk (useful for development)"""
    await stop_runtime_generator()
    await stop_stream_engine()
    try:
        data_loader.reload_data()
        await refresh_stream_state()
        return {
            "status": "success",
            "message": "Data reloaded from disk",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    finally:
        await start_stream_engine()
        await start_runtime_generator()


# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
