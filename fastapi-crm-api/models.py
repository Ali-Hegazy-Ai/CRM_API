"""
Pydantic models for CRM API

Note: These models are intentionally flexible to accommodate messy data.
We use Optional for most fields and allow extra fields to preserve
the inconsistencies from the source data.
"""

from typing import Optional, Any, Dict, List
from pydantic import BaseModel, ConfigDict


class FlexibleModel(BaseModel):
    """Base model that allows extra fields and is very permissive"""
    model_config = ConfigDict(extra='allow', arbitrary_types_allowed=True)


class PaginationMetadata(BaseModel):
    """Pagination metadata for list responses"""
    total: int
    page: int
    limit: int
    has_more: bool
    next_page: Optional[int] = None


class CustomerListResponse(FlexibleModel):
    """Response wrapper for customers list"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool


class ContactListResponse(FlexibleModel):
    """Response wrapper for contacts list"""
    contacts: List[Dict[str, Any]]
    count: int
    page: int


class LeadListResponse(FlexibleModel):
    """Response wrapper for leads list"""
    results: List[Dict[str, Any]]
    total_count: int
    page: int
    next_page: Optional[str] = None


class DealListResponse(FlexibleModel):
    """Response wrapper for deals list"""
    data: List[Dict[str, Any]]
    total: int
    page: int
    limit: int
    has_more: bool


class ActivityListResponse(FlexibleModel):
    """Response wrapper for activities list"""
    activities: List[Dict[str, Any]]
    count: int
    page: int
    per_page: int


class NoteListResponse(FlexibleModel):
    """Response wrapper for notes list"""
    data: List[Dict[str, Any]]
    total: int


class CompanyListResponse(FlexibleModel):
    """Response wrapper for companies list"""
    companies: List[Dict[str, Any]]
    total_count: int
    page_number: int
    page_size: int


class SearchResponse(FlexibleModel):
    """Response wrapper for search results"""
    results: List[Dict[str, Any]]
    query: str
    total: int
    search_time_ms: int


class EventListResponse(FlexibleModel):
    """Response wrapper for events list"""
    events: List[Dict[str, Any]]
    total: int
    page: int


class SyncStatusResponse(FlexibleModel):
    """Response wrapper for sync status"""
    sync_status: Dict[str, Any]
    last_updated: str


class MetadataResponse(FlexibleModel):
    """Response wrapper for metadata"""
    entities: Dict[str, Any]
    version: str
    generated_at: str


class ErrorResponse(FlexibleModel):
    """Error response"""
    error: str
    message: str
    status: int
    timestamp: Optional[str] = None
