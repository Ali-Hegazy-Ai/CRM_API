"""
Event generation utilities for CRM API

Generates change events by comparing versions
"""

from typing import List, Dict, Any
from datetime import datetime
from data_loader import data_loader


def generate_events(version: str = "v3", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Generate change events by comparing data versions
    
    Args:
        version: Target version to generate events for
        limit: Maximum number of events to return
    
    Returns:
        List of event records
    """
    events = []
    event_counter = 10001
    
    # Define version order
    versions = ["v1", "v2", "v3"]
    if version not in versions:
        version = "v3"
    
    version_idx = versions.index(version)
    
    # Compare with previous version if available
    if version_idx > 0:
        prev_version = versions[version_idx - 1]
        
        # Check customers for changes
        events.extend(_generate_entity_events(
            "customer", 
            prev_version, 
            version, 
            event_counter
        ))
        event_counter += len(events)
        
        # Check contacts for changes
        events.extend(_generate_entity_events(
            "contact", 
            prev_version, 
            version, 
            event_counter
        ))
        event_counter += len(events)
        
        # Check deals for changes
        events.extend(_generate_entity_events(
            "deal", 
            prev_version, 
            version, 
            event_counter
        ))
    
    # Add some synthetic events for current version
    current_customers = data_loader.get_data("customers", version)
    if current_customers:
        # Add update event for first customer
        customer = current_customers[0]
        events.append({
            "id": f"evt_{event_counter}",
            "event_id": f"EVT-{event_counter}",
            "event_type": "customer.updated",
            "entity_type": "customer",
            "entity_id": customer.get('id'),
            "timestamp": "2024-04-11T16:00:00Z",
            "user_id": customer.get('owner_id'),
            "source_system": customer.get('source_system'),
            "changes": {
                "status": {"old": "active", "new": "active"},
                "last_activity_at": {
                    "old": "2024-04-10T09:15:00Z",
                    "new": customer.get('last_activity_at')
                }
            },
            "metadata": {
                "sync_version": customer.get('sync_version'),
                "ip_address": "192.168.1.100"
            }
        })
        event_counter += 1
    
    # Add deal created event
    current_deals = data_loader.get_data("deals", version)
    if current_deals:
        deal = current_deals[0]
        events.append({
            "id": f"evt_{event_counter}",
            "event_id": f"EVT-{event_counter}",
            "event_type": "deal.created",
            "entity_type": "deal",
            "entity_id": deal.get('id'),
            "timestamp": deal.get('created_at'),
            "user_id": deal.get('owner_id'),
            "source_system": deal.get('source_system'),
            "changes": None,
            "metadata": {
                "sync_version": 1
            }
        })
        event_counter += 1
    
    # Add contact deleted event if we have deleted contacts
    current_contacts = data_loader.get_data("contacts", version)
    deleted_contacts = [c for c in current_contacts if c.get('is_deleted') or c.get('deleted_at')]
    if deleted_contacts:
        contact = deleted_contacts[0]
        events.append({
            "id": f"evt_{event_counter}",
            "event_id": f"EVT-{event_counter}",
            "event_type": "contact.deleted",
            "entity_type": "contact",
            "entity_id": contact.get('id'),
            "timestamp": contact.get('deleted_at') or contact.get('updated_at'),
            "user_id": contact.get('owner_id'),
            "source_system": contact.get('source_system'),
            "changes": {
                "is_deleted": {"old": False, "new": True},
                "deleted_at": {"old": None, "new": contact.get('deleted_at')}
            },
            "metadata": {
                "sync_version": contact.get('sync_version'),
                "reason": "customer_churned"
            }
        })
    
    return events[:limit]


def _generate_entity_events(
    entity_type: str,
    prev_version: str,
    current_version: str,
    start_counter: int
) -> List[Dict[str, Any]]:
    """
    Generate events for a specific entity by comparing versions
    
    Args:
        entity_type: Entity type (customer, contact, deal, etc.)
        prev_version: Previous version identifier
        current_version: Current version identifier
        start_counter: Starting event counter
    
    Returns:
        List of events
    """
    events = []
    entity_plural = f"{entity_type}s"
    
    prev_data = data_loader.get_data(entity_plural, prev_version)
    current_data = data_loader.get_data(entity_plural, current_version)
    
    # Build ID sets
    prev_ids = {record.get('id') for record in prev_data if record.get('id')}
    current_ids = {record.get('id') for record in current_data if record.get('id')}
    
    # Find new records (created)
    new_ids = current_ids - prev_ids
    for record_id in list(new_ids)[:5]:  # Limit to 5 events per type
        record = next((r for r in current_data if r.get('id') == record_id), None)
        if record:
            events.append({
                "id": f"evt_{start_counter + len(events)}",
                "event_id": f"EVT-{start_counter + len(events)}",
                "event_type": f"{entity_type}.created",
                "entity_type": entity_type,
                "entity_id": record_id,
                "timestamp": record.get('created_at'),
                "user_id": record.get('owner_id') or record.get('created_by'),
                "source_system": record.get('source_system'),
                "changes": None,
                "metadata": {
                    "sync_version": 1
                }
            })
    
    # Find removed records (deleted)
    removed_ids = prev_ids - current_ids
    for record_id in list(removed_ids)[:3]:  # Limit to 3 events
        record = next((r for r in prev_data if r.get('id') == record_id), None)
        if record:
            events.append({
                "id": f"evt_{start_counter + len(events)}",
                "event_id": f"EVT-{start_counter + len(events)}",
                "event_type": f"{entity_type}.deleted",
                "entity_type": entity_type,
                "entity_id": record_id,
                "timestamp": record.get('updated_at') or record.get('created_at'),
                "user_id": record.get('owner_id'),
                "source_system": record.get('source_system'),
                "changes": {
                    "is_deleted": {"old": False, "new": True}
                },
                "metadata": {
                    "sync_version": record.get('sync_version')
                }
            })
    
    # Find updated records (common IDs)
    common_ids = prev_ids & current_ids
    for record_id in list(common_ids)[:5]:  # Limit to 5 events
        prev_record = next((r for r in prev_data if r.get('id') == record_id), None)
        current_record = next((r for r in current_data if r.get('id') == record_id), None)
        
        if prev_record and current_record:
            # Check if updated_at changed
            if prev_record.get('updated_at') != current_record.get('updated_at'):
                events.append({
                    "id": f"evt_{start_counter + len(events)}",
                    "event_id": f"EVT-{start_counter + len(events)}",
                    "event_type": f"{entity_type}.updated",
                    "entity_type": entity_type,
                    "entity_id": record_id,
                    "timestamp": current_record.get('updated_at'),
                    "user_id": current_record.get('owner_id') or current_record.get('updated_by'),
                    "source_system": current_record.get('source_system'),
                    "changes": {
                        "updated_at": {
                            "old": prev_record.get('updated_at'),
                            "new": current_record.get('updated_at')
                        }
                    },
                    "metadata": {
                        "sync_version": current_record.get('sync_version')
                    }
                })
    
    return events
