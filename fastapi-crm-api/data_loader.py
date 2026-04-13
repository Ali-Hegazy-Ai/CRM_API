"""
Data loading utilities for CRM API

Loads JSON data files from disk and caches them in memory.
Supports versioned snapshots (v1, v2, v3).
"""

import json
import os
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DataLoader:
    """Loads and caches CRM data from JSON files"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.cache: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
        self.static_cache: Dict[str, Any] = {}
        self._load_all_data()
    
    def _load_all_data(self):
        """Load all data files at startup"""
        missing_files = []
        
        # Load versioned data (v1, v2, v3)
        for version in ["v1", "v2", "v3"]:
            self.cache[version] = {}
            version_dir = self.data_dir / version
            
            if not version_dir.exists():
                logger.warning(f"Version directory missing: {version_dir}")
                missing_files.append(f"{version}/ (entire directory)")
            else:
                # Load each entity
                entities = [
                    "customers", "contacts", "leads", "deals",
                    "activities", "notes", "companies"
                ]
                
                for entity in entities:
                    file_path = version_dir / f"{entity}.json"
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            self.cache[version][entity] = json.load(f)
                    else:
                        self.cache[version][entity] = []
                        missing_files.append(f"{version}/{entity}.json")
        
        # Load static data (not versioned)
        static_dir = self.data_dir / "static"
        if not static_dir.exists():
            logger.warning(f"Static directory missing: {static_dir}")
            missing_files.append("static/ (entire directory)")
        else:
            static_files = ["owners", "pipeline_stages", "sync_status"]
            for filename in static_files:
                file_path = static_dir / f"{filename}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        self.static_cache[filename] = json.load(f)
                else:
                    missing_files.append(f"static/{filename}.json")
        
        # Log missing files
        if missing_files:
            logger.warning("=" * 60)
            logger.warning("DATA FILES MISSING - API will return empty arrays")
            logger.warning("=" * 60)
            for missing in missing_files:
                logger.warning(f"  - data/{missing}")
            logger.warning("=" * 60)
    
    def get_data(self, entity: str, version: str = "v3") -> List[Dict[str, Any]]:
        """
        Get data for an entity and version
        
        Args:
            entity: Entity name (e.g., "customers", "contacts")
            version: Version identifier (v1, v2, v3)
        
        Returns:
            List of records for the entity
        """
        if version not in self.cache:
            version = "v3"  # Default to v3 if invalid version
        
        return self.cache.get(version, {}).get(entity, [])
    
    def get_static_data(self, entity: str) -> Any:
        """
        Get static data (not versioned)
        
        Args:
            entity: Entity name (e.g., "owners", "pipeline_stages")
        
        Returns:
            Data for the entity
        """
        return self.static_cache.get(entity, [])
    
    def get_record_by_id(
        self, 
        entity: str, 
        record_id: str, 
        version: str = "v3"
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single record by ID
        
        Args:
            entity: Entity name
            record_id: Record ID to find
            version: Version identifier
        
        Returns:
            Record if found, None otherwise
        """
        data = self.get_data(entity, version)
        
        # Try to find by 'id' field
        for record in data:
            if record.get('id') == record_id:
                return record
        
        # Try other ID fields as fallback
        id_fields = ['customer_id', 'contact_id', 'lead_id', 'deal_id', 
                     'activity_id', 'note_id', 'company_id', 'user_id']
        
        for record in data:
            for id_field in id_fields:
                if record.get(id_field) == record_id:
                    return record
        
        return None
    
    def search_across_entities(
        self, 
        query: str, 
        version: str = "v3"
    ) -> List[Dict[str, Any]]:
        """
        Search across all entities for a query string
        
        Args:
            query: Search query
            version: Version identifier
        
        Returns:
            List of matching records with entity_type added
        """
        query_lower = query.lower()
        results = []
        
        # Define searchable fields per entity
        search_config = {
            "customers": ["id", "customer_id", "name", "email", "external_id"],
            "contacts": ["id", "contact_id", "first_name", "last_name", 
                        "email", "full_name", "firstName", "lastName"],
            "leads": ["id", "lead_id", "company_name", "contact_name", 
                     "email", "first_name", "last_name"],
            "deals": ["id", "deal_id", "deal_name", "external_id"],
            "activities": ["id", "activity_id", "subject", "type"],
            "notes": ["id", "note_id", "title", "content"],
            "companies": ["id", "company_id", "name", "legal_name"]
        }
        
        for entity, fields in search_config.items():
            data = self.get_data(entity, version)
            
            for record in data:
                # Check if query matches any searchable field
                match = False
                match_field = None
                
                for field in fields:
                    value = record.get(field)
                    if value and query_lower in str(value).lower():
                        match = True
                        match_field = field
                        break
                
                if match:
                    result = {
                        "entity_type": entity,
                        "entity_id": record.get('id'),
                        "match_field": match_field,
                        "match_score": 0.85,  # Simplified scoring
                        **record
                    }
                    results.append(result)
        
        return results
    
    def get_all_versions(self) -> List[str]:
        """Get list of available versions"""
        return list(self.cache.keys())
    
    def reload_data(self):
        """Reload all data from disk (useful for development)"""
        self.cache.clear()
        self.static_cache.clear()
        self._load_all_data()


# Global data loader instance
data_loader = DataLoader()
