"""
Pagination utilities for CRM API

Implements pagination with intentional issues to simulate production behavior:
- Duplicate records across pages
- Shifting page boundaries
- Total count mismatches
- Incomplete last pages
"""

import random
from typing import List, Dict, Any, Tuple, Optional
from models import PaginationMetadata


def paginate_data(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20,
    offset: Optional[int] = None,
    add_issues: bool = True
) -> Tuple[List[Dict[str, Any]], PaginationMetadata]:
    """
    Paginate data with realistic issues
    
    Args:
        data: Full dataset to paginate
        page: Page number (1-indexed)
        limit: Records per page
        offset: Alternative to page (0-indexed)
        add_issues: Whether to add pagination issues
    
    Returns:
        Tuple of (paginated_data, metadata)
    """
    # Validate inputs
    page = max(1, page)
    limit = min(max(1, limit), 100)  # Max 100 per page
    
    # Calculate offset
    if offset is not None:
        start_idx = max(0, offset)
    else:
        start_idx = (page - 1) * limit
    
    end_idx = start_idx + limit
    
    # Add intentional pagination issues
    if add_issues and len(data) > 0:
        # Issue 1: Occasionally duplicate a record from previous page
        if page > 1 and random.random() < 0.3:  # 30% chance
            # Add one record from previous page
            prev_idx = max(0, start_idx - 1)
            if prev_idx < len(data):
                data = data[:start_idx] + [data[prev_idx]] + data[start_idx:]
        
        # Issue 2: Occasionally shift boundary slightly
        if random.random() < 0.2:  # 20% chance
            start_idx = max(0, start_idx + random.choice([-1, 1]))
        
        # Issue 3: Occasionally return fewer records on last page
        if end_idx >= len(data) and random.random() < 0.3:  # 30% chance
            end_idx = max(start_idx, len(data) - random.randint(1, 3))
    
    # Get page data
    page_data = data[start_idx:end_idx]
    
    # Calculate metadata
    total = len(data)
    
    # Issue 4: Occasionally report wrong total
    if add_issues and random.random() < 0.2:  # 20% chance
        total = total + random.choice([-2, -1, 1, 2])
    
    has_more = end_idx < len(data)
    next_page = page + 1 if has_more else None
    
    metadata = PaginationMetadata(
        total=max(0, total),
        page=page,
        limit=limit,
        has_more=has_more,
        next_page=next_page
    )
    
    return page_data, metadata


def paginate_with_wrapper(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20,
    wrapper_key: str = "data",
    add_issues: bool = True
) -> Dict[str, Any]:
    """
    Paginate and wrap in response object
    
    Args:
        data: Full dataset
        page: Page number
        limit: Records per page
        wrapper_key: Key for data array in response
        add_issues: Whether to add pagination issues
    
    Returns:
        Response dict with data and metadata
    """
    page_data, metadata = paginate_data(data, page, limit, add_issues=add_issues)
    
    return {
        wrapper_key: page_data,
        "total": metadata.total,
        "page": metadata.page,
        "limit": metadata.limit,
        "has_more": metadata.has_more
    }


def paginate_contacts(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Paginate contacts with their specific response format"""
    page_data, metadata = paginate_data(data, page, limit)
    
    return {
        "contacts": page_data,
        "count": len(page_data),
        "page": metadata.page
    }


def paginate_leads(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Paginate leads with their specific response format"""
    page_data, metadata = paginate_data(data, page, limit)
    
    return {
        "results": page_data,
        "total_count": metadata.total,
        "page": metadata.page,
        "next_page": f"/leads?page={metadata.next_page}" if metadata.next_page else None
    }


def paginate_activities(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Paginate activities with their specific response format"""
    page_data, metadata = paginate_data(data, page, limit)
    
    return {
        "activities": page_data,
        "count": len(page_data),
        "page": metadata.page,
        "per_page": metadata.limit
    }


def paginate_companies(
    data: List[Dict[str, Any]],
    page: int = 1,
    limit: int = 20
) -> Dict[str, Any]:
    """Paginate companies with their specific response format"""
    page_data, metadata = paginate_data(data, page, limit)
    
    return {
        "companies": page_data,
        "total_count": metadata.total,
        "page_number": metadata.page,
        "page_size": metadata.limit
    }
