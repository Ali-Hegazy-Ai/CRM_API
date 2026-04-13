"""
Search utilities for CRM API

Implements cross-entity search functionality
"""

import time
from typing import List, Dict, Any, Optional
from data_loader import data_loader


def search_entities(query: str, version: str = "v3", entity_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Search across entities
    
    Args:
        query: Search query string
        version: Data version to search
        entity_type: Optional entity type filter
    
    Returns:
        Search results with metadata
    """
    start_time = time.time()
    
    # Get search results from data loader
    results = data_loader.search_across_entities(query, version)
    
    # Filter by entity type if specified
    if entity_type:
        results = [r for r in results if r.get('entity_type') == entity_type]
    
    # Entity type mapping (handle pluralization correctly)
    entity_type_map = {
        'customers': 'customer',
        'contacts': 'contact',
        'leads': 'lead',
        'deals': 'deal',
        'activities': 'activity',
        'notes': 'note',
        'companies': 'company'
    }
    
    # Format results for response
    formatted_results = []
    for result in results:
        entity_type_raw = result.pop('entity_type', 'unknown')
        entity_type = entity_type_map.get(entity_type_raw, entity_type_raw)
        entity_id = result.get('id')
        match_field = result.pop('match_field', 'unknown')
        match_score = result.pop('match_score', 0.0)
        
        # Extract key fields based on entity type
        formatted_result = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "match_field": match_field,
            "match_score": match_score
        }
        
        # Add entity-specific fields
        if entity_type == 'customer':
            formatted_result.update({
                "name": result.get('name'),
                "email": result.get('email') or result.get('email_address')
            })
        elif entity_type == 'contact':
            formatted_result.update({
                "name": result.get('full_name') or f"{result.get('first_name', '')} {result.get('last_name', '')}".strip(),
                "email": result.get('email'),
                "company_name": result.get('company_id')  # Would need lookup in real system
            })
        elif entity_type == 'lead':
            formatted_result.update({
                "name": result.get('contact_name'),
                "company_name": result.get('company_name'),
                "email": result.get('email')
            })
        elif entity_type == 'deal':
            formatted_result.update({
                "name": result.get('deal_name'),
                "amount": result.get('amount')
            })
        elif entity_type == 'activity':
            formatted_result.update({
                "subject": result.get('subject'),
                "type": result.get('type')
            })
        elif entity_type == 'note':
            formatted_result.update({
                "title": result.get('title'),
                "content": result.get('content', '')[:100]  # Truncate content
            })
        elif entity_type == 'company':
            formatted_result.update({
                "name": result.get('name'),
                "industry": result.get('industry') or result.get('Industry')
            })
        
        formatted_results.append(formatted_result)
    
    # Calculate search time
    search_time_ms = int((time.time() - start_time) * 1000)
    
    return {
        "results": formatted_results[:50],  # Limit to 50 results
        "query": query,
        "total": len(formatted_results),
        "search_time_ms": search_time_ms
    }
