# CRM Mock API Documentation

## Overview
This is a Mockoon-compatible CRM API designed for data engineering projects. It simulates realistic production data with intentional quality issues to test ETL pipelines, data validation, and data modeling workflows.

## Setup Instructions

### 1. Install Mockoon
- Download from: https://mockoon.com/download/
- Or use CLI: `npm install -g @mockoon/cli`

### 2. Import the API
- Open Mockoon Desktop
- Click "File" → "Open environment"
- Select `mockoon-crm-api.json`
- Click "Start" to run the API on `http://localhost:3000`

### 3. Alternative: CLI Usage
```bash
mockoon-cli start --data ./mockoon-crm-api.json --port 3000
```

## API Endpoints

### 1. GET /api/v1/customers
Returns customer records with various data quality issues.

**Response Structure:**
```json
{
  "data": [...],
  "total": 7,
  "page": 1,
  "per_page": 20
}
```

**Data Quality Issues:**
- Duplicate IDs (cust_8x9k2m4n5p, cust_7h3j9k1m2n)
- Inconsistent status casing: "active", "Active", "ACTIVE", "inactive"
- Missing field: `Status` vs `status` (field name inconsistency)
- Null values in email, phone, updated_at, owner_id
- Inconsistent date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS"
- Invalid email: "info@techstart" (missing domain)
- Empty phone: ""
- Inconsistent country codes: "USA", "US", "UK"
- Missing currency field in some records
- Soft-deleted record with deleted_at timestamp
- Inconsistent phone formats: "+1-555-0123", "555.0124", "+44 20 7123 4567", "(555) 0125"

---

### 2. GET /api/v1/contacts
Returns contact records with field name variations and missing data.

**Response Structure:**
```json
{
  "contacts": [...],
  "count": 6
}
```

**Data Quality Issues:**
- Duplicate contact IDs (cont_8k2m9n5p3x appears twice)
- Field name inconsistencies: `first_name` vs `firstName`, `last_name` vs `lastName`
- Inconsistent field names: `created_date`, `last_modified` vs `created_at`, `updated_at`
- Null phone numbers
- Empty last_name
- Inconsistent email casing: lowercase vs UPPERCASE
- Invalid email: "m.chen@globalsolutions" (missing TLD)
- Inconsistent status field: `status` vs `Status`
- Status casing: "active", "Active", "ACTIVE", "INACTIVE"
- Missing title field in some records
- Null owner field
- Extra field in one record: linkedin_url (not present in others)
- Same person with different emails and titles (John Smith)
- Inconsistent date formats

---

### 3. GET /api/v1/leads
Returns lead records with scoring and qualification data.

**Response Structure:**
```json
{
  "results": [...],
  "total_count": 6,
  "page": 1
}
```

**Data Quality Issues:**
- Duplicate lead IDs (lead_9k5m2n8p3x)
- Field name variations: `lead_status` vs `leadStatus`, `lead_score` vs `score`
- Null lead_score values
- Inconsistent status casing: "qualified", "New", "contacted", "QUALIFIED", "lost", "Qualified"
- Invalid email: "athompson@" (incomplete)
- Empty phone: ""
- Null contact_name
- Null owner_id
- Null campaign_id
- Inconsistent date formats
- Inconsistent source values: "website" vs "website_form"
- Same company with slight name variations: "NextGen Analytics" vs "NextGen Analytics Inc"
- Same contact with different names: "Robert Martinez" vs "Bob Martinez"
- Lost lead with lost_reason field (not present in others)

---

### 4. GET /api/v1/deals
Returns deal/opportunity records with nested and flat contact structures.

**Response Structure:**
```json
{
  "data": [...],
  "total": 6,
  "page": 1,
  "limit": 20
}
```

**Data Quality Issues:**
- Mixed contact representation: nested object vs flat fields (contact_id, contact_name, contact_email)
- Inconsistent currency casing: "USD", "usd", "GBP", "CAD"
- Inconsistent stage casing: "negotiation", "Proposal", "discovery", "CLOSED_WON", "qualification", "closed_lost"
- Field name inconsistency: `stage` vs `Stage`
- Null probability
- Null amount
- Null customer_id (deal linked to lead instead)
- Decimal vs integer amounts: 45000.00 vs 125000
- Inconsistent date formats
- Additional fields for closed deals: actual_close_date, lost_reason
- Missing contact information in some records
- Deals with different lifecycle stages (won, lost, active)

---

### 5. GET /api/v1/activities
Returns activity/interaction records with varying types.

**Response Structure:**
```json
{
  "activities": [...],
  "count": 6,
  "page": 1
}
```

**Data Quality Issues:**
- Inconsistent type casing: "call", "Email", "meeting", "CALL", "task", "email"
- Field name inconsistency: `status` vs `Status`
- Status casing: "completed", "Completed", "COMPLETED", "scheduled", "in_progress"
- Null description
- Missing duration_minutes in some records
- Inconsistent date formats
- Different date fields: activity_date vs due_date
- Missing deal_id in some records
- Activity linked to lead instead of customer
- Extra fields in some records: priority, updated_at
- Different source systems: "salesforce", "hubspot", "gmail_sync"

---

### 6. GET /api/v1/notes
Returns note records with optional metadata.

**Response Structure:**
```json
{
  "data": [...],
  "total": 5
}
```

**Data Quality Issues:**
- Null title
- Empty content: ""
- Field name inconsistency: `title` vs `Title`
- Inconsistent date formats
- Missing updated_at in some records
- Missing tags array in some records
- Missing contact_id in some records
- Boolean field: is_pinned

---

### 7. GET /api/v1/companies
Returns company records with address variations.

**Response Structure:**
```json
{
  "companies": [...],
  "total_count": 5,
  "page_number": 1,
  "page_size": 20
}
```

**Data Quality Issues:**
- Duplicate company_id (comp_8x9k2m4n5p)
- Inconsistent industry casing: "Technology", "software", "Consulting", "DATA_ANALYTICS", "Research"
- Field name inconsistency: `industry` vs `Industry`
- Mixed employee_count types: integer vs string range "50-100"
- Null annual_revenue
- Null employee_count
- Inconsistent website formats: with/without https://, with/without www
- Address structure variations: nested object vs flat fields
- Missing address fields (street in one record)
- Null updated_at
- Inconsistent date formats
- Extra field: is_active (only in one record)
- Inconsistent country codes: "USA", "US", "UK", "Canada"

---

## Entity Relationships

```
Companies (1) ──→ (N) Customers
Customers (1) ──→ (N) Contacts
Customers (1) ──→ (N) Deals
Customers (1) ──→ (N) Activities
Customers (1) ──→ (N) Notes
Leads (1) ──→ (N) Activities
Leads (1) ──→ (0..1) Deals (conversion)
Contacts (1) ──→ (N) Activities
Contacts (1) ──→ (N) Notes
Deals (1) ──→ (N) Activities
Deals (1) ──→ (N) Notes
```

## Common Data Quality Patterns

### 1. Duplicate Records
- Same ID appearing multiple times with different data
- Same entity with slight variations (name spelling, email)

### 2. Missing/Null Values
- Critical fields like email, phone, owner_id
- Optional fields inconsistently populated

### 3. Inconsistent Formatting
- Date formats: ISO 8601 vs SQL datetime
- Phone numbers: various international formats
- Email casing: mixed case
- Status/enum values: inconsistent casing

### 4. Field Name Variations
- Snake_case vs camelCase
- Different field names for same concept across endpoints

### 5. Invalid Data
- Incomplete emails
- Empty strings vs null
- Invalid phone formats

### 6. Structural Inconsistencies
- Nested objects vs flat fields
- Different response wrapper keys
- Inconsistent pagination metadata

### 7. Lifecycle States
- Soft-deleted records (deleted_at)
- Inactive/archived records
- Records in various stages

### 8. Source System Artifacts
- Different sync_status values
- Multiple source_system identifiers
- Timestamp fields from different systems

---

## Testing Scenarios

### ETL Pipeline Testing
1. **Deduplication**: Handle duplicate IDs and similar records
2. **Normalization**: Standardize date formats, casing, phone numbers
3. **Validation**: Catch invalid emails, missing required fields
4. **Type Conversion**: Handle mixed types (string vs integer)
5. **Null Handling**: Decide on null vs empty string strategy

### Data Quality Checks
1. **Completeness**: Identify records with missing critical fields
2. **Consistency**: Flag inconsistent field names and values
3. **Accuracy**: Validate email formats, phone numbers
4. **Uniqueness**: Detect and resolve duplicates
5. **Timeliness**: Check for stale data (old updated_at)

### Data Modeling
1. **Schema Design**: Handle field name variations
2. **Relationship Mapping**: Link entities across systems
3. **Slowly Changing Dimensions**: Track changes over time
4. **Fact/Dimension Tables**: Separate transactional vs reference data

---

## 5 Ways to Make It Even More Realistic

### 1. **Add Rate Limiting and Pagination Behavior**
- Implement 429 Too Many Requests responses
- Add pagination with cursor-based or offset-based patterns
- Include incomplete result sets requiring multiple API calls
- Add `next_page` and `has_more` fields with realistic pagination logic

### 2. **Introduce Temporal Data Changes**
- Create multiple versions of the same endpoint that return different data based on time
- Simulate records that change between API calls
- Add `last_sync_token` or `etag` headers for change detection
- Include records with recent updates (within last hour) vs stale data

### 3. **Add API Error Responses**
- 500 Internal Server Error for specific record IDs
- 404 Not Found for deleted/archived records
- 403 Forbidden for records user doesn't have access to
- 422 Unprocessable Entity with validation error details
- Intermittent timeouts or slow responses (>5 seconds)

### 4. **Include Webhook/Event Data**
- Add `/api/v1/webhooks/events` endpoint with change events
- Include event types: created, updated, deleted, merged
- Add event timestamps and sequence numbers
- Simulate out-of-order events and duplicate event deliveries

### 5. **Add Data Lineage and Audit Fields**
- Include `created_by_system`, `modified_by_system` fields
- Add `import_batch_id` for bulk imports
- Include `data_quality_score` or `confidence_level` fields
- Add `last_validated_at` and `validation_status` fields
- Include `merge_history` showing record consolidation
- Add `source_record_id` for tracking original system IDs

---

## Usage Examples

### Python with requests
```python
import requests

# Get all customers
response = requests.get('http://localhost:3000/api/v1/customers')
customers = response.json()

# Get all contacts
response = requests.get('http://localhost:3000/api/v1/contacts')
contacts = response.json()

# Get all deals
response = requests.get('http://localhost:3000/api/v1/deals')
deals = response.json()
```

### cURL
```bash
# Get customers
curl http://localhost:3000/api/v1/customers

# Get contacts
curl http://localhost:3000/api/v1/contacts

# Get leads
curl http://localhost:3000/api/v1/leads

# Get deals
curl http://localhost:3000/api/v1/deals

# Get activities
curl http://localhost:3000/api/v1/activities

# Get notes
curl http://localhost:3000/api/v1/notes

# Get companies
curl http://localhost:3000/api/v1/companies
```

---

## Data Engineering Project Ideas

1. **ETL Pipeline**: Extract from all endpoints, transform to clean schema, load to data warehouse
2. **Data Quality Dashboard**: Build metrics on completeness, validity, consistency
3. **Master Data Management**: Create golden records from duplicates
4. **Change Data Capture**: Track changes between API calls
5. **Data Lineage Tracking**: Map data flow from source to destination
6. **Validation Framework**: Build rules engine for data quality checks
7. **Schema Evolution**: Handle field name changes and new fields
8. **Entity Resolution**: Match and merge duplicate records
9. **Data Profiling**: Analyze patterns, distributions, anomalies
10. **API Monitoring**: Track response times, error rates, data freshness

---

## License
Free to use for educational and testing purposes.
