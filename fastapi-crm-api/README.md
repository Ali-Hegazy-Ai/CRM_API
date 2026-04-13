# Production CRM API - FastAPI Implementation

A realistic, intentionally messy CRM API built with FastAPI for data engineering testing.

## Overview

This API simulates a production CRM system with 3+ years of operational history, multiple data migrations, and all the data quality problems that break real ETL pipelines.

**Key Features:**
- 13 REST endpoints serving 8 core entities
- 3 versioned snapshots (v1, v2, v3) showing data evolution
- 50+ intentional data quality issues
- Pagination with realistic issues
- Cross-entity search
- Change event log
- Multiple source systems (Salesforce, HubSpot, Zoho, Pipedrive)

## Quick Start

### 1. Install Dependencies

```bash
cd fastapi-crm-api
pip install -r requirements.txt
```

### 2. Run the API

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --reload --port 8000
```

### 3. Test the API

```bash
# Get all customers (v3, default)
curl http://localhost:8000/customers

# Get customers from v1 snapshot
curl "http://localhost:8000/customers?version=v1"

# Get paginated results
curl "http://localhost:8000/customers?page=1&limit=5"

# Get single customer
curl http://localhost:8000/customers/cust_8x9k2m4n5p

# Search across entities
curl "http://localhost:8000/search?q=acme"

# Get change events
curl http://localhost:8000/events
```

### 4. View API Documentation

Open your browser to:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Core Entities
- `GET /customers` - List all customers
- `GET /customers/{id}` - Get single customer
- `GET /contacts` - List all contacts
- `GET /contacts/{id}` - Get single contact
- `GET /leads` - List all leads
- `GET /leads/{id}` - Get single lead
- `GET /deals` - List all deals
- `GET /deals/{id}` - Get single deal
- `GET /activities` - List all activities
- `GET /activities/{id}` - Get single activity
- `GET /notes` - List all notes
- `GET /companies` - List all companies
- `GET /companies/{id}` - Get single company

### Supporting Endpoints
- `GET /owners` - List sales reps and owners
- `GET /pipeline-stages` - List deal stages
- `GET /sync-status` - Get sync health by source
- `GET /metadata` - Get API schema metadata
- `GET /search?q=` - Search across entities
- `GET /events` - Get change event log

## Query Parameters

### Versioning
All endpoints support `?version=v1`, `?version=v2`, `?version=v3`
- **v1**: January 2023 snapshot (oldest, most inconsistent)
- **v2**: September 2023 snapshot (partial cleanup)
- **v3**: Current state (default, still has issues)

### Pagination
List endpoints support:
- `?page=1` (default: 1)
- `?limit=20` (default: 20, max: 100)
- `?offset=0` (alternative to page)

### Search
- `?q=search_term` - Search across entities

## Data Quality Issues

This API intentionally includes 50+ data quality issues:

### Duplicate Records
- Same ID appearing multiple times
- Same entity with different IDs

### Missing/Null Values
- Required fields null or missing
- Inconsistent null vs empty string

### Inconsistent Formatting
- Date formats: ISO 8601, SQL datetime, slash dates
- Phone formats: various international styles
- Email casing: mixed case
- Status/enum casing: inconsistent

### Field Name Variations
- snake_case vs camelCase
- Different names for same concept

### Invalid Data
- Incomplete emails (missing domain/TLD)
- Empty strings
- Invalid phone formats

### Type Inconsistencies
- String vs number (amount, probability)
- String ranges vs integers (employee_count)

### Structural Inconsistencies
- Nested objects vs flat fields
- Different response wrappers

### Pagination Issues
- Duplicate records across pages
- Shifting page boundaries
- Total count mismatches

## Project Structure

```
fastapi-crm-api/
├── main.py                 # FastAPI application
├── models.py              # Pydantic models (flexible)
├── data_loader.py         # JSON data loading utilities
├── pagination.py          # Pagination utilities
├── search.py              # Search utilities
├── events.py              # Event generation logic
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── data/                 # JSON data files
    ├── v1/
    │   ├── customers.json
    │   ├── contacts.json
    │   ├── leads.json
    │   ├── deals.json
    │   ├── activities.json
    │   ├── notes.json
    │   └── companies.json
    ├── v2/
    │   └── ...
    ├── v3/
    │   └── ...
    └── static/
        ├── owners.json
        ├── pipeline_stages.json
        └── sync_status.json
```

## Development

### Adding New Versions

1. Create new version folder: `data/v4/`
2. Add entity JSON files
3. Update `data_loader.py` to include v4
4. Test with `?version=v4`

### Adding New Entities

1. Create JSON file in `data/v3/entity_name.json`
2. Add endpoint in `main.py`
3. Update search logic in `search.py`
4. Update events in `events.py`

### Modifying Data

Edit JSON files in `data/` directory. Changes take effect on restart.

## Testing

### Manual Testing

```bash
# Test all endpoints
curl http://localhost:8000/customers
curl http://localhost:8000/contacts
curl http://localhost:8000/leads
curl http://localhost:8000/deals
curl http://localhost:8000/activities
curl http://localhost:8000/notes
curl http://localhost:8000/companies
curl http://localhost:8000/owners
curl http://localhost:8000/pipeline-stages
curl http://localhost:8000/sync-status
curl http://localhost:8000/metadata
curl "http://localhost:8000/search?q=acme"
curl http://localhost:8000/events

# Test versioning
curl "http://localhost:8000/customers?version=v1"
curl "http://localhost:8000/customers?version=v2"
curl "http://localhost:8000/customers?version=v3"

# Test pagination
curl "http://localhost:8000/customers?page=1&limit=5"
curl "http://localhost:8000/customers?page=2&limit=5"
```

### Automated Testing

```python
import requests

BASE_URL = "http://localhost:8000"

# Test all endpoints
endpoints = ["/customers", "/contacts", "/leads", "/deals"]
for endpoint in endpoints:
    response = requests.get(f"{BASE_URL}{endpoint}")
    assert response.status_code == 200
    print(f"✓ {endpoint}")

# Test versioning
for version in ["v1", "v2", "v3"]:
    response = requests.get(f"{BASE_URL}/customers?version={version}")
    assert response.status_code == 200
    print(f"✓ Version {version}")
```

## Use Cases

### ETL Pipeline Testing
Extract from this API, transform messy data, load to warehouse

### Data Quality Framework
Build validation rules to catch all the intentional issues

### Schema Evolution
Track how data changes across v1, v2, v3

### Master Data Management
Deduplicate and merge records

### Data Modeling
Build dimensional models from messy source data

## Notes

- Data is loaded at startup and cached in memory
- Pagination boundaries intentionally shift
- Some records appear in multiple pages
- Total counts may not match actual records
- This is all intentional to simulate production issues

## License

Free to use for educational and testing purposes.

## Support

For issues or questions, check the source code comments or API documentation at `/docs`.
