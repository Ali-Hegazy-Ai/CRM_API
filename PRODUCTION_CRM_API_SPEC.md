# Production CRM Mock API - Complete Specification

## Overview

This API simulates a real production CRM system with 3+ years of operational history, multiple data migrations, integration with external systems (Salesforce, HubSpot, Zoho), and all the data quality problems that accumulate in real enterprise systems.

**Domain Model:**
- Companies (organizations/accounts)
- Contacts (people at companies)
- Leads (unqualified prospects)
- Customers (converted/qualified accounts)
- Deals (sales opportunities)
- Activities (calls, emails, meetings, tasks)
- Notes (free-form annotations)
- Owners (sales reps, account managers)
- Pipeline Stages (deal progression)

**Key Characteristics:**
- Data spans 2021-2024
- Multiple source systems with different schemas
- Partial migrations with inconsistent field mappings
- Real-world data quality issues (not artificial chaos)
- Versioned snapshots showing data evolution
- Realistic entity relationships and lifecycle transitions

---

## API Endpoints

### Core Entity Endpoints

| Method | Path | Purpose | Pagination | Versioning |
|--------|------|---------|------------|------------|
| GET | `/customers` | List all customers | Yes | Yes |
| GET | `/customers/:id` | Get single customer | No | Yes |
| GET | `/contacts` | List all contacts | Yes | Yes |
| GET | `/contacts/:id` | Get single contact | No | Yes |
| GET | `/leads` | List all leads | Yes | Yes |
| GET | `/leads/:id` | Get single lead | No | Yes |
| GET | `/deals` | List all deals | Yes | Yes |
| GET | `/deals/:id` | Get single deal | No | Yes |
| GET | `/activities` | List all activities | Yes | Yes |
| GET | `/activities/:id` | Get single activity | No | Yes |
| GET | `/notes` | List all notes | Yes | Yes |
| GET | `/companies` | List all companies | Yes | Yes |
| GET | `/companies/:id` | Get single company | No | Yes |

### Supporting Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/owners` | List sales reps and owners |
| GET | `/pipeline-stages` | List deal stages |
| GET | `/sync-status` | Get sync health by source |
| GET | `/metadata` | Get API schema metadata |
| GET | `/search?q=` | Search across entities |
| GET | `/events` | Get change event log |

### Versioning

All endpoints support `?version=v1`, `?version=v2`, `?version=v3` query parameter.
- **v1**: January 2023 snapshot (oldest, most inconsistent)
- **v2**: September 2023 snapshot (partial cleanup)
- **v3**: Current state (default, still has issues)

### Pagination

List endpoints support:
- `?page=1&limit=20` (default)
- `?offset=0&limit=50`
- Response includes: `total`, `page`, `limit`, `has_more`, `next_page`

**Intentional pagination issues:**
- Some pages have duplicate records
- Page boundaries shift between calls
- Total count doesn't always match actual records
- Last page sometimes incomplete

---

## Entity Schemas & Sample Data

### 1. GET /customers

**Purpose:** Customer master data (converted from leads or direct entry)

**Response Wrapper:** `{ "data": [...], "total": N, "page": 1, "limit": 20, "has_more": bool }`

**Sample Response (v3):**

```json
{
  "data": [
    {
      "id": "cust_8x9k2m4n5p",
      "external_id": "SF-ACC-10234",
      "customer_id": "CUST-10234",
      "name": "Acme Corporation",
      "email": "contact@acmecorp.com",
      "phone": "+1-555-0123",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-01-15T10:30:00Z",
      "updated_at": "2024-03-20T14:22:11Z",
      "last_activity_at": "2024-04-10T09:15:00Z",
      "first_seen_at": "2022-11-20T08:00:00Z",
      "owner_id": "usr_445",
      "assigned_team": "enterprise",
      "source_system": "salesforce",
      "source_record_id": "0018x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 47,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "company_id": "comp_8x9k2m4n5p",
      "country": "USA",
      "region": "North America",
      "timezone": "America/Los_Angeles",
      "currency": "USD",
      "annual_revenue": 4500000,
      "employee_count": 1250,
      "industry": "Technology"
    },
    {
      "id": "cust_7h3j9k1m2n",
      "external_id": "HUB-12456",
      "customer_id": "CUST-10235",
      "name": "TechStart Inc.",
      "email": "info@techstart",
      "phone": "555.0124",
      "status": "Active",
      "lifecycle_stage": "customer",
      "created_at": "2023-02-10 11:45:30",
      "updated_at": "2024-01-15T09:10:22Z",
      "last_activity_at": "2024-01-15T09:10:22Z",
      "owner_id": "usr_447",
      "assigned_team": "SMB",
      "source_system": "hubspot",
      "source_record_id": "12456",
      "sync_status": "pending",
      "sync_version": 12,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "company_id": "comp_7h3j9k1m2n",
      "country": "US",
      "region": "North America",
      "currency": "USD",
      "employee_count": "50-100"
    },
    {
      "id": "cust_8x9k2m4n5p",
      "external_id": "SF-ACC-10236",
      "customer_id": "CUST-10236",
      "name": "Global Solutions Ltd",
      "email": null,
      "phone": "+44 20 7123 4567",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-03-22T08:15:00Z",
      "updated_at": null,
      "last_activity_at": "2023-12-05T14:30:00Z",
      "first_seen_at": "2023-03-22T08:15:00Z",
      "owner_id": null,
      "source_system": "salesforce",
      "source_record_id": "0018x00000XyZaB",
      "sync_status": "synced",
      "sync_version": 3,
      "last_synced_at": "2023-12-10T03:00:00Z",
      "company_id": "comp_8x9k2m4n5p",
      "country": "UK",
      "region": "EMEA",
      "currency": "GBP",
      "annual_revenue": 2800000
    },
    {
      "id": "cust_2p9k8m3n1x",
      "external_id": "PIPE-789",
      "customer_id": "CUST-10237",
      "name": "innovate labs",
      "email_address": "CONTACT@INNOVATELABS.COM",
      "phone_number": "(555) 0125",
      "Status": "inactive",
      "lifecycle_stage": "churned",
      "created_at": "2022-11-05T14:20:00Z",
      "updated_at": "2023-12-01T10:30:00Z",
      "last_activity_at": "2023-06-15T11:00:00Z",
      "owner_id": "usr_445",
      "source_system": "pipedrive",
      "source_record_id": "789",
      "sync_status": "failed",
      "sync_version": 8,
      "last_synced_at": "2024-04-10T12:00:00Z",
      "company_id": "comp_2p9k8m3n1x",
      "country": "USA",
      "currency": "USD"
    },
    {
      "id": "cust_5k2m9n4p7x",
      "external_id": "SF-ACC-10238",
      "customer_id": "CUST-10238",
      "name": "DataFlow Systems",
      "email": "admin@dataflow.io",
      "phone": "+1-416-555-0199",
      "status": "ACTIVE",
      "lifecycle_stage": "customer",
      "created_at": "2023-06-18T16:45:00Z",
      "updated_at": "2024-04-10T11:20:33Z",
      "last_activity_at": "2024-04-11T15:45:00Z",
      "first_seen_at": "2023-05-10T09:00:00Z",
      "owner_id": "usr_449",
      "assigned_team": "Enterprise",
      "source_system": "salesforce",
      "source_record_id": "0018x00000QwErTy",
      "sync_status": "synced",
      "sync_version": 89,
      "last_synced_at": "2024-04-12T07:00:00Z",
      "company_id": "comp_5k2m9n4p7x",
      "country": "Canada",
      "region": "North America",
      "timezone": "America/Toronto",
      "currency": "CAD",
      "annual_revenue": 1550000,
      "employee_count": 320,
      "industry": "Data Analytics"
    },
    {
      "id": "cust_7h3j9k1m2n",
      "external_id": "SF-ACC-10239",
      "customer_id": "CUST-10239",
      "name": "TechStart Inc",
      "email": "sales@techstart.com",
      "phone": "+1 555 0124",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-02-10T11:45:30Z",
      "updated_at": "2024-03-28T15:40:12Z",
      "last_activity_at": "2024-04-09T10:20:00Z",
      "first_seen_at": "2023-01-15T14:00:00Z",
      "owner_id": "usr_447",
      "assigned_team": "smb",
      "source_system": "salesforce",
      "source_record_id": "0018x00000MnOpQ",
      "sync_status": "synced",
      "sync_version": 34,
      "last_synced_at": "2024-04-12T06:45:00Z",
      "company_id": "comp_7h3j9k1m2n",
      "country": "USA",
      "region": "North America",
      "timezone": "America/Chicago",
      "currency": "USD",
      "employee_count": 75,
      "industry": "Software"
    },
    {
      "id": "cust_9m2n5p8k3x",
      "external_id": "HUB-12457",
      "customer_id": "CUST-10240",
      "name": "CloudVentures",
      "email": "contact@cloudventures.com",
      "phone": "",
      "status": "deleted",
      "lifecycle_stage": "churned",
      "created_at": "2022-08-12T09:00:00Z",
      "updated_at": "2023-10-15T13:25:00Z",
      "deleted_at": "2023-10-15T13:25:00Z",
      "last_activity_at": "2023-09-30T16:00:00Z",
      "is_deleted": true,
      "owner_id": "usr_450",
      "source_system": "hubspot",
      "source_record_id": "12457",
      "sync_status": "synced",
      "sync_version": 15,
      "last_synced_at": "2023-10-15T14:00:00Z",
      "company_id": "comp_9m2n5p8k3x",
      "country": "USA",
      "currency": "USD"
    },
    {
      "id": "cust_3k8m2n9p5x",
      "external_id": "ZOHO-5678",
      "customer_id": "CUST-10241",
      "name": "Pyramid Solutions",
      "email": "info@pyramidsolutions.eg",
      "phone": "+20 2 1234 5678",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-09-10T07:30:00Z",
      "updated_at": "2024-04-05T12:15:00Z",
      "last_activity_at": "2024-04-08T08:30:00Z",
      "first_seen_at": "2023-08-22T10:00:00Z",
      "owner_id": "usr_451",
      "assigned_team": "EMEA",
      "source_system": "zoho",
      "source_record_id": "5678",
      "sync_status": "synced",
      "sync_version": 22,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "company_id": "comp_3k8m2n9p5x",
      "country": "Egypt",
      "region": "EMEA",
      "timezone": "Africa/Cairo",
      "currency": "EGP",
      "annual_revenue": 850000,
      "employee_count": 180,
      "industry": "Consulting"
    }
  ],
  "total": 8,
  "page": 1,
  "limit": 20,
  "has_more": false
}
```

**Data Quality Issues:**
- Duplicate IDs: `cust_8x9k2m4n5p` appears twice (records 1 and 3)
- Duplicate IDs: `cust_7h3j9k1m2n` appears twice (records 2 and 6)
- Field name inconsistency: `email` vs `email_address`, `phone` vs `phone_number`
- Field name inconsistency: `status` vs `Status`
- Status casing: "active", "Active", "ACTIVE", "inactive", "deleted"
- Team casing: "enterprise", "SMB", "Enterprise", "smb", "EMEA"
- Date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS"
- Invalid email: "info@techstart" (missing TLD)
- Empty phone: ""
- Null values: email, phone, updated_at, owner_id
- Country variations: "USA", "US", "UK", "Canada", "Egypt"
- Employee count: integer vs string range "50-100"
- Soft-deleted record with `deleted_at` and `is_deleted`
- Conflicting timestamps: `updated_at` null but `last_activity_at` recent
- Same company different names: "TechStart Inc." vs "TechStart Inc"
- Stale sync: record 3 last synced Dec 2023 but still in v3

---


### 2. GET /contacts

**Purpose:** Individual people at companies

**Response Wrapper:** `{ "contacts": [...], "count": N, "page": 1 }`

**Sample Response (v3):**

```json
{
  "contacts": [
    {
      "id": "cont_8k2m9n5p3x",
      "external_id": "SF-CONT-5001",
      "contact_id": "CONT-5001",
      "first_name": "John",
      "last_name": "Smith",
      "full_name": "John Smith",
      "email": "john.smith@acmecorp.com",
      "phone": "+1-555-0199",
      "mobile": "+1-555-0198",
      "title": "VP of Engineering",
      "department": "Engineering",
      "company_id": "comp_8x9k2m4n5p",
      "customer_id": "cust_8x9k2m4n5p",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-01-20T09:15:00Z",
      "updated_at": "2024-03-15T10:20:00Z",
      "last_activity_at": "2024-04-10T14:30:00Z",
      "first_seen_at": "2023-01-20T09:15:00Z",
      "owner_id": "usr_445",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "0038x00000PqRsT",
      "sync_status": "synced",
      "sync_version": 28,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "country": "USA",
      "timezone": "America/Los_Angeles",
      "linkedin_url": "https://linkedin.com/in/johnsmith"
    },
    {
      "id": "cont_3n5p8k2m9x",
      "external_id": "HUB-CONT-2001",
      "contact_id": "CONT-5002",
      "firstName": "sarah",
      "lastName": "johnson",
      "email": "SARAH.JOHNSON@TECHSTART.COM",
      "phone": null,
      "title": "CTO",
      "company_id": "comp_7h3j9k1m2n",
      "customer_id": "cust_7h3j9k1m2n",
      "status": "Active",
      "lifecycle_stage": "customer",
      "created_date": "2023-02-15 14:30:00",
      "updated_date": "2024-01-20T11:45:00Z",
      "last_activity_at": "2024-04-09T09:00:00Z",
      "owner_id": "usr_447",
      "source_system": "hubspot",
      "source_record_id": "2001",
      "sync_status": "synced",
      "sync_version": 15,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "country": "US"
    },
    {
      "id": "cont_5p8k3m2n9x",
      "external_id": "SF-CONT-5003",
      "contact_id": "CONT-5003",
      "first_name": "Michael",
      "last_name": "Chen",
      "email": "m.chen@globalsolutions",
      "phone": "+44-20-7123-4570",
      "title": "Director of Operations",
      "company_id": "comp_8x9k2m4n5p",
      "customer_id": "cust_8x9k2m4n5p",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-03-25T10:00:00Z",
      "updated_at": "2023-03-25T10:00:00Z",
      "last_activity_at": "2023-11-10T15:00:00Z",
      "owner_id": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "0038x00000UvWxY",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2023-11-15T02:00:00Z",
      "country": "UK"
    },
    {
      "id": "cont_2m9n5p3k8x",
      "external_id": "PIPE-CONT-301",
      "contact_id": "CONT-5004",
      "first_name": "Emily",
      "last_name": "",
      "email": "emily@innovatelabs.com",
      "phone_number": "555-0177",
      "company_id": "comp_2p9k8m3n1x",
      "customer_id": "cust_2p9k8m3n1x",
      "Status": "INACTIVE",
      "lifecycle_stage": "churned",
      "created_at": "2022-11-10T08:30:00Z",
      "updated_at": "2023-11-30T16:20:00Z",
      "last_activity_at": "2023-06-10T10:00:00Z",
      "owner_id": null,
      "source_system": "pipedrive",
      "source_record_id": "301",
      "sync_status": "failed",
      "sync_version": 5,
      "last_synced_at": "2024-04-10T12:00:00Z",
      "country": "USA"
    },
    {
      "id": "cont_8k2m9n5p3x",
      "external_id": "SF-CONT-5005",
      "contact_id": "CONT-5005",
      "first_name": "John",
      "last_name": "Smith",
      "full_name": "John Smith",
      "email": "j.smith@acmecorp.com",
      "phone": "+1 555 0199",
      "title": "Vice President of Engineering",
      "department": "Engineering",
      "company_id": "comp_8x9k2m4n5p",
      "customer_id": "cust_8x9k2m4n5p",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-01-20T09:15:00Z",
      "updated_at": "2024-04-01T14:10:00Z",
      "last_activity_at": "2024-04-11T11:00:00Z",
      "first_seen_at": "2023-01-20T09:15:00Z",
      "owner_id": "usr_445",
      "created_by": "usr_445",
      "updated_by": "usr_448",
      "source_system": "manual_entry",
      "sync_status": "not_synced",
      "country": "USA",
      "timezone": "America/Los_Angeles",
      "linkedin_url": "https://www.linkedin.com/in/john-smith-12345"
    },
    {
      "id": "cont_7k3m2n9p5x",
      "external_id": "SF-CONT-5006",
      "contact_id": "CONT-5006",
      "first_name": "David",
      "last_name": "Williams",
      "email": "dwilliams@dataflow.io",
      "phone": "",
      "mobile": "+1-416-555-0188",
      "title": "Product Manager",
      "company_id": "comp_5k2m9n4p7x",
      "customer_id": "cust_5k2m9n4p7x",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-07-01T12:00:00Z",
      "updated_at": "2024-02-14T09:30:00Z",
      "last_activity_at": "2024-04-11T16:00:00Z",
      "owner_id": "usr_449",
      "source_system": "salesforce",
      "source_record_id": "0038x00000ZaBcD",
      "sync_status": "synced",
      "sync_version": 18,
      "last_synced_at": "2024-04-12T07:00:00Z",
      "country": "Canada",
      "timezone": "America/Toronto"
    },
    {
      "id": "cont_4n9p2k5m8x",
      "external_id": "ZOHO-CONT-401",
      "contact_id": "CONT-5007",
      "first_name": "Fatima",
      "last_name": "Hassan",
      "email": "fhassan@pyramidsolutions.eg",
      "phone": "+20-2-1234-5679",
      "title": "Managing Director",
      "company_id": "comp_3k8m2n9p5x",
      "customer_id": "cust_3k8m2n9p5x",
      "status": "active",
      "lifecycle_stage": "customer",
      "created_at": "2023-09-12T08:00:00Z",
      "updated_at": "2024-04-05T13:00:00Z",
      "last_activity_at": "2024-04-08T09:00:00Z",
      "owner_id": "usr_451",
      "source_system": "zoho",
      "source_record_id": "401",
      "sync_status": "synced",
      "sync_version": 12,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "country": "EGYPT",
      "timezone": "Africa/Cairo"
    },
    {
      "id": "cont_6m3n8p2k9x",
      "external_id": "HUB-CONT-2002",
      "contact_id": "CONT-5008",
      "firstName": "Robert",
      "lastName": "Martinez",
      "full_name": "Robert Martinez",
      "email": "rmartinez@cloudventures.com",
      "phone": "+1-555-0166",
      "title": "CEO",
      "company_id": "comp_9m2n5p8k3x",
      "customer_id": "cust_9m2n5p8k3x",
      "status": "inactive",
      "lifecycle_stage": "churned",
      "created_at": "2022-08-15T10:00:00Z",
      "updated_at": "2023-10-15T13:30:00Z",
      "deleted_at": "2023-10-15T13:30:00Z",
      "last_activity_at": "2023-09-28T14:00:00Z",
      "is_deleted": true,
      "owner_id": "usr_450",
      "source_system": "hubspot",
      "source_record_id": "2002",
      "sync_status": "synced",
      "sync_version": 8,
      "last_synced_at": "2023-10-15T14:00:00Z",
      "country": "US"
    }
  ],
  "count": 8,
  "page": 1
}
```

**Data Quality Issues:**
- Duplicate IDs: `cont_8k2m9n5p3x` appears twice (same person, different sources)
- Field name variations: `first_name`/`firstName`, `last_name`/`lastName`, `phone`/`phone_number`
- Field name variations: `created_at`/`created_date`, `updated_at`/`updated_date`
- Missing `full_name` in some records
- Empty last_name
- Null phone
- Empty phone string
- Invalid email: "m.chen@globalsolutions" (missing TLD)
- Email casing: "SARAH.JOHNSON@TECHSTART.COM" vs lowercase
- Status casing: "active", "Active", "INACTIVE", "inactive"
- Country variations: "USA", "US", "UK", "Canada", "EGYPT"
- Same person different emails: john.smith@ vs j.smith@
- Same person different titles: "VP of Engineering" vs "Vice President of Engineering"
- Different LinkedIn URL formats
- Soft-deleted contact
- Stale data: record 3 not updated since creation
- Missing department in most records
- Inconsistent mobile field presence

---

### 3. GET /leads

**Purpose:** Unqualified prospects (pre-customer)

**Response Wrapper:** `{ "results": [...], "total_count": N, "page": 1, "next_page": URL }`

**Sample Response (v3):**

```json
{
  "results": [
    {
      "id": "lead_9k5m2n8p3x",
      "external_id": "SF-LEAD-7001",
      "lead_id": "LEAD-7001",
      "company_name": "NextGen Analytics",
      "contact_name": "Robert Martinez",
      "first_name": "Robert",
      "last_name": "Martinez",
      "email": "rmartinez@nextgen.com",
      "phone": "+1-555-0188",
      "title": "Director of Analytics",
      "lead_status": "qualified",
      "lead_source": "website",
      "lead_score": 85,
      "priority": "high",
      "created_at": "2024-01-10T08:30:00Z",
      "updated_at": "2024-03-25T14:15:00Z",
      "last_activity_at": "2024-04-08T10:00:00Z",
      "first_seen_at": "2024-01-10T08:30:00Z",
      "owner_id": "usr_445",
      "assigned_team": "enterprise",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "00Q8x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 15,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "campaign_id": "camp_123",
      "campaign_name": "Q1 2024 Webinar",
      "country": "USA",
      "region": "North America",
      "timezone": "America/New_York",
      "currency": "USD",
      "estimated_value": 125000,
      "employee_count": "500-1000",
      "industry": "Analytics"
    },
    {
      "id": "lead_3m8n2p5k9x",
      "external_id": "HUB-LEAD-3001",
      "lead_id": "LEAD-7002",
      "company_name": "smart solutions inc",
      "contact_name": "jennifer lee",
      "email": "JLEE@SMARTSOLUTIONS.COM",
      "phone": "555.0166",
      "title": "VP Sales",
      "leadStatus": "New",
      "lead_source": "trade_show",
      "score": null,
      "priority": "medium",
      "created_at": "2024-02-05 10:20:15",
      "updated_at": "2024-02-05 10:20:15",
      "last_activity_at": "2024-02-05 10:20:15",
      "owner_id": "usr_447",
      "assigned_team": "SMB",
      "source_system": "hubspot",
      "source_record_id": "3001",
      "sync_status": "pending",
      "sync_version": 1,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "campaign_id": null,
      "country": "US",
      "currency": "USD"
    },
    {
      "id": "lead_5p2k9m3n8x",
      "external_id": "SF-LEAD-7003",
      "lead_id": "LEAD-7003",
      "company_name": "FutureTech Corp",
      "contact_name": "Alex Thompson",
      "first_name": "Alex",
      "last_name": "Thompson",
      "email": "athompson@",
      "phone": "+1 (555) 0177",
      "title": "CTO",
      "lead_status": "contacted",
      "lead_source": "referral",
      "lead_score": 62,
      "priority": "high",
      "created_at": "2024-01-28T11:45:00Z",
      "updated_at": "2024-03-10T09:20:00Z",
      "last_activity_at": "2024-03-10T09:20:00Z",
      "owner_id": "usr_449",
      "source_system": "salesforce",
      "source_record_id": "00Q8x00000FgHiJ",
      "sync_status": "synced",
      "sync_version": 8,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "country": "USA",
      "currency": "USD"
    },
    {
      "id": "lead_8k3m5n2p9x",
      "external_id": "SF-LEAD-7004",
      "lead_id": "LEAD-7004",
      "company_name": "DataDriven LLC",
      "contact_name": null,
      "email": "info@datadriven.com",
      "phone": "",
      "lead_status": "QUALIFIED",
      "lead_source": "linkedin",
      "lead_score": 78,
      "priority": "HIGH",
      "created_at": "2024-03-01T14:00:00Z",
      "updated_at": "2024-04-05T16:30:00Z",
      "last_activity_at": "2024-04-11T12:00:00Z",
      "owner_id": null,
      "source_system": "salesforce",
      "source_record_id": "00Q8x00000KlMnO",
      "sync_status": "synced",
      "sync_version": 12,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "campaign_id": "camp_125",
      "campaign_name": "LinkedIn Campaign March 2024",
      "country": "USA",
      "currency": "USD",
      "estimated_value": 95000
    },
    {
      "id": "lead_2n9p5k3m8x",
      "external_id": "SF-LEAD-7005",
      "lead_id": "LEAD-7005",
      "company_name": "CloudFirst Technologies",
      "contact_name": "Maria Garcia",
      "first_name": "Maria",
      "last_name": "Garcia",
      "email": "m.garcia@cloudfirst.io",
      "phone": "+1-555-0144",
      "title": "VP Engineering",
      "lead_status": "lost",
      "lead_source": "cold_call",
      "lead_score": 45,
      "priority": "low",
      "created_at": "2023-11-15T09:00:00Z",
      "updated_at": "2024-01-20T11:30:00Z",
      "last_activity_at": "2024-01-18T15:00:00Z",
      "lost_reason": "budget_constraints",
      "lost_date": "2024-01-20",
      "owner_id": "usr_450",
      "source_system": "salesforce",
      "source_record_id": "00Q8x00000PqRsT",
      "sync_status": "synced",
      "sync_version": 6,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "country": "USA",
      "currency": "USD"
    },
    {
      "id": "lead_9k5m2n8p3x",
      "external_id": "SF-LEAD-7006",
      "lead_id": "LEAD-7006",
      "company_name": "NextGen Analytics Inc",
      "contact_name": "Bob Martinez",
      "first_name": "Robert",
      "last_name": "Martinez",
      "email": "bob.martinez@nextgen.com",
      "phone": "+1 555 0188",
      "title": "Director of Analytics",
      "lead_status": "Qualified",
      "lead_source": "website_form",
      "lead_score": 87,
      "priority": "high",
      "created_at": "2024-01-10T08:30:00Z",
      "updated_at": "2024-04-08T10:45:00Z",
      "last_activity_at": "2024-04-11T09:30:00Z",
      "converted_date": "2024-04-08",
      "converted_contact_id": "cont_9k5m2n8p3x",
      "converted_deal_id": "deal_8k3m5n2p9x",
      "owner_id": "usr_445",
      "assigned_team": "Enterprise",
      "source_system": "salesforce",
      "source_record_id": "00Q8x00000UvWxY",
      "sync_status": "synced",
      "sync_version": 18,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "campaign_id": "camp_123",
      "country": "USA",
      "region": "North America",
      "currency": "USD",
      "estimated_value": 130000
    },
    {
      "id": "lead_7k2m3n9p5x",
      "external_id": "ZOHO-LEAD-501",
      "lead_id": "LEAD-7007",
      "company_name": "Cairo Tech Hub",
      "contact_name": "Ahmed Khalil",
      "first_name": "Ahmed",
      "last_name": "Khalil",
      "email": "akhalil@cairotech.eg",
      "phone": "+20 2 9876 5432",
      "title": "Founder",
      "lead_status": "new",
      "lead_source": "partner",
      "lead_score": 55,
      "priority": "medium",
      "created_at": "2024-03-15T09:00:00Z",
      "updated_at": "2024-04-02T11:00:00Z",
      "last_activity_at": "2024-04-02T11:00:00Z",
      "owner_id": "usr_451",
      "assigned_team": "EMEA",
      "source_system": "zoho",
      "source_record_id": "501",
      "sync_status": "synced",
      "sync_version": 5,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "country": "EG",
      "region": "EMEA",
      "timezone": "Africa/Cairo",
      "currency": "EGP",
      "estimated_value": 45000,
      "employee_count": "10-50",
      "industry": "Technology"
    }
  ],
  "total_count": 7,
  "page": 1,
  "next_page": null
}
```

**Data Quality Issues:**
- Duplicate IDs: `lead_9k5m2n8p3x` appears twice (records 1 and 6)
- Field name variations: `lead_status`/`leadStatus`, `lead_score`/`score`
- Status casing: "qualified", "New", "contacted", "QUALIFIED", "lost", "Qualified", "new"
- Priority casing: "high", "medium", "HIGH", "low"
- Team casing: "enterprise", "SMB", "Enterprise", "EMEA"
- Company name variations: "NextGen Analytics" vs "NextGen Analytics Inc"
- Contact name variations: "Robert Martinez" vs "Bob Martinez"
- Email variations: "rmartinez@nextgen.com" vs "bob.martinez@nextgen.com"
- Invalid email: "athompson@" (incomplete)
- Empty phone: ""
- Null values: score, contact_name, owner_id, campaign_id
- Date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS"
- Country variations: "USA", "US", "EG"
- Employee count as string range
- Converted lead with conversion fields
- Lost lead with lost_reason and lost_date
- Same lead appears unconverted and converted
- Inconsistent field presence: estimated_value, region, timezone

---


### 4. GET /deals

**Purpose:** Sales opportunities/pipeline

**Response Wrapper:** `{ "data": [...], "total": N, "page": 1, "limit": 20, "has_more": bool }`

**Sample Response (v3):**

```json
{
  "data": [
    {
      "id": "deal_7k2m9n5p8x",
      "external_id": "SF-OPP-9001",
      "deal_id": "DEAL-9001",
      "deal_name": "Acme Corp - Enterprise License",
      "amount": 125000,
      "currency": "USD",
      "stage": "negotiation",
      "stage_id": "stage_4",
      "probability": 75,
      "expected_close_date": "2024-05-15",
      "close_date": null,
      "status": "open",
      "priority": "high",
      "deal_type": "new_business",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_8k2m9n5p3x",
      "owner_id": "usr_445",
      "assigned_team": "enterprise",
      "created_at": "2024-02-01T10:00:00Z",
      "updated_at": "2024-04-10T15:30:00Z",
      "last_activity_at": "2024-04-11T14:00:00Z",
      "first_seen_at": "2024-02-01T10:00:00Z",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "0068x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 42,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "lead_id": null,
      "lead_source": "referral",
      "campaign_id": null,
      "country": "USA",
      "region": "North America",
      "contact": {
        "id": "cont_8k2m9n5p3x",
        "name": "John Smith",
        "email": "john.smith@acmecorp.com",
        "title": "VP of Engineering"
      },
      "products": [
        {"name": "Enterprise Platform", "quantity": 1, "price": 125000}
      ]
    },
    {
      "id": "deal_3n5p8k2m9x",
      "external_id": "HUB-DEAL-5001",
      "deal_id": "DEAL-9002",
      "deal_name": "TechStart - Annual Subscription",
      "amount": 45000.00,
      "currency": "usd",
      "stage": "Proposal",
      "stage_id": "stage_3",
      "probability": 60,
      "expected_close_date": "2024-04-30",
      "status": "Open",
      "priority": "medium",
      "deal_type": "renewal",
      "customer_id": "cust_7h3j9k1m2n",
      "company_id": "comp_7h3j9k1m2n",
      "contact_id": "cont_3n5p8k2m9x",
      "owner_id": "usr_447",
      "assigned_team": "SMB",
      "created_at": "2024-01-15 09:30:00",
      "updated_at": "2024-03-28T11:20:00Z",
      "last_activity_at": "2024-04-09T10:00:00Z",
      "source_system": "hubspot",
      "source_record_id": "5001",
      "sync_status": "pending",
      "sync_version": 18,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "lead_source": "existing_customer",
      "country": "US",
      "contact_name": "Sarah Johnson",
      "contact_email": "sarah.johnson@techstart.com"
    },
    {
      "id": "deal_5p8k3m2n9x",
      "external_id": "SF-OPP-9003",
      "deal_id": "DEAL-9003",
      "deal_name": "Global Solutions - Consulting Package",
      "amount": 85000,
      "currency": "GBP",
      "stage": "discovery",
      "stage_id": "stage_2",
      "probability": null,
      "expected_close_date": "2024-06-20",
      "status": "open",
      "priority": "high",
      "deal_type": "new_business",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_5p8k3m2n9x",
      "owner_id": "usr_445",
      "created_at": "2024-03-10T14:15:00Z",
      "updated_at": "2024-04-01T10:00:00Z",
      "last_activity_at": "2024-04-01T10:00:00Z",
      "source_system": "salesforce",
      "source_record_id": "0068x00000FgHiJ",
      "sync_status": "synced",
      "sync_version": 8,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "country": "UK",
      "region": "EMEA"
    },
    {
      "id": "deal_2m9n5p3k8x",
      "external_id": "SF-OPP-9004",
      "deal_id": "DEAL-9004",
      "deal_name": "DataFlow - Implementation Services",
      "amount": 67500,
      "currency": "CAD",
      "Stage": "CLOSED_WON",
      "stage_id": "stage_6",
      "probability": 100,
      "expected_close_date": "2024-03-31",
      "close_date": "2024-03-28T16:45:00Z",
      "actual_close_date": "2024-03-28",
      "status": "closed",
      "priority": "high",
      "deal_type": "new_business",
      "customer_id": "cust_5k2m9n4p7x",
      "company_id": "comp_5k2m9n4p7x",
      "contact_id": "cont_7k3m2n9p5x",
      "owner_id": "usr_449",
      "assigned_team": "Enterprise",
      "created_at": "2024-01-20T11:00:00Z",
      "updated_at": "2024-03-28T16:45:00Z",
      "last_activity_at": "2024-03-28T16:45:00Z",
      "closed_by": "usr_449",
      "source_system": "salesforce",
      "source_record_id": "0068x00000KlMnO",
      "sync_status": "synced",
      "sync_version": 25,
      "last_synced_at": "2024-04-12T07:00:00Z",
      "country": "Canada",
      "region": "North America",
      "contact": {
        "id": "cont_7k3m2n9p5x",
        "name": "David Williams"
      }
    },
    {
      "id": "deal_8k3m5n2p9x",
      "external_id": "SF-OPP-9005",
      "deal_id": "DEAL-9005",
      "deal_name": "NextGen - Platform Migration",
      "amount": null,
      "currency": "USD",
      "stage": "qualification",
      "stage_id": "stage_1",
      "probability": 30,
      "expected_close_date": "2024-07-15",
      "status": "open",
      "priority": "medium",
      "deal_type": "new_business",
      "customer_id": null,
      "company_id": null,
      "contact_id": null,
      "lead_id": "lead_9k5m2n8p3x",
      "owner_id": "usr_445",
      "created_at": "2024-03-20T13:00:00Z",
      "updated_at": "2024-04-05T09:15:00Z",
      "last_activity_at": "2024-04-11T11:00:00Z",
      "source_system": "salesforce",
      "source_record_id": "0068x00000PqRsT",
      "sync_status": "synced",
      "sync_version": 12,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "lead_source": "website",
      "country": "USA"
    },
    {
      "id": "deal_9m2n5p8k3x",
      "external_id": "HUB-DEAL-5002",
      "deal_id": "DEAL-9006",
      "deal_name": "CloudVentures - Support Contract",
      "amount": 24000,
      "currency": "USD",
      "stage": "closed_lost",
      "stage_id": "stage_7",
      "probability": 0,
      "expected_close_date": "2023-12-31",
      "close_date": "2023-12-15",
      "actual_close_date": "2023-12-15T14:30:00Z",
      "status": "closed",
      "priority": "low",
      "deal_type": "renewal",
      "lost_reason": "competitor",
      "customer_id": "cust_9m2n5p8k3x",
      "company_id": "comp_9m2n5p8k3x",
      "contact_id": "cont_6m3n8p2k9x",
      "owner_id": "usr_450",
      "created_at": "2023-10-01T10:00:00Z",
      "updated_at": "2023-12-15T14:30:00Z",
      "last_activity_at": "2023-12-10T16:00:00Z",
      "source_system": "hubspot",
      "source_record_id": "5002",
      "sync_status": "synced",
      "sync_version": 10,
      "last_synced_at": "2023-12-16T02:00:00Z",
      "country": "USA"
    },
    {
      "id": "deal_4n8p3k2m9x",
      "external_id": "ZOHO-DEAL-601",
      "deal_id": "DEAL-9007",
      "deal_name": "Pyramid Solutions - Consulting Engagement",
      "amount": 55000,
      "currency": "EGP",
      "stage": "proposal",
      "stage_id": "stage_3",
      "probability": 65,
      "expected_close_date": "2024-05-30",
      "status": "open",
      "priority": "high",
      "deal_type": "new_business",
      "customer_id": "cust_3k8m2n9p5x",
      "company_id": "comp_3k8m2n9p5x",
      "contact_id": "cont_4n9p2k5m8x",
      "owner_id": "usr_451",
      "assigned_team": "EMEA",
      "created_at": "2024-03-25T10:00:00Z",
      "updated_at": "2024-04-08T12:00:00Z",
      "last_activity_at": "2024-04-10T09:00:00Z",
      "source_system": "zoho",
      "source_record_id": "601",
      "sync_status": "synced",
      "sync_version": 8,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "country": "Egypt",
      "region": "EMEA",
      "timezone": "Africa/Cairo"
    },
    {
      "id": "deal_7k2m9n5p8x",
      "external_id": "SF-OPP-9008",
      "deal_id": "DEAL-9008",
      "deal_name": "Acme Corporation - Enterprise License Renewal",
      "amount": "135000",
      "currency": "USD",
      "stage": "negotiation",
      "stage_id": "stage_4",
      "probability": "80",
      "expected_close_date": "05/20/2024",
      "status": "open",
      "priority": "critical",
      "deal_type": "renewal",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "owner_id": "usr_445",
      "assigned_team": "enterprise",
      "created_at": "2024-04-01T09:00:00Z",
      "updated_at": "2024-04-11T16:00:00Z",
      "last_activity_at": "2024-04-12T08:00:00Z",
      "source_system": "salesforce",
      "source_record_id": "0068x00000UvWxY",
      "sync_status": "synced",
      "sync_version": 5,
      "last_synced_at": "2024-04-12T08:15:00Z",
      "country": "USA",
      "region": "North America"
    }
  ],
  "total": 8,
  "page": 1,
  "limit": 20,
  "has_more": false
}
```

**Data Quality Issues:**
- Duplicate IDs: `deal_7k2m9n5p8x` appears twice (records 1 and 8)
- Field name variations: `stage` vs `Stage`
- Stage casing: "negotiation", "Proposal", "discovery", "CLOSED_WON", "qualification", "closed_lost", "proposal"
- Status casing: "open", "Open", "closed"
- Priority variations: "high", "medium", "low", "critical"
- Team casing: "enterprise", "SMB", "Enterprise", "EMEA"
- Currency casing: "USD", "usd", "GBP", "CAD", "EGP"
- Amount types: integer vs float (45000.00) vs string ("135000")
- Probability types: integer vs string ("80")
- Date formats: ISO 8601 vs "MM/DD/YYYY" vs date-only strings
- Multiple close date fields: close_date, actual_close_date
- Contact representation: nested object vs flat fields (contact_name, contact_email)
- Null values: probability, amount, close_date, customer_id, company_id, contact_id
- Deal linked to lead instead of customer (record 5)
- Closed deals with additional fields: closed_by, lost_reason
- Country variations: "USA", "US", "UK", "Canada", "Egypt"
- Same company different deal names: "Acme Corp" vs "Acme Corporation"
- Inconsistent field presence: products array, timezone, region
- Stale sync: record 6 last synced Dec 2023

---

### 5. GET /activities

**Purpose:** Interactions, tasks, calls, emails, meetings

**Response Wrapper:** `{ "activities": [...], "count": N, "page": 1, "per_page": 20 }`

**Sample Response (v3):**

```json
{
  "activities": [
    {
      "id": "act_5k2m9n8p3x",
      "external_id": "SF-TASK-1001",
      "activity_id": "ACT-1001",
      "type": "call",
      "subject": "Discovery Call",
      "description": "Initial discovery call to understand requirements and pain points",
      "duration_minutes": 45,
      "activity_date": "2024-04-08T14:00:00Z",
      "due_date": null,
      "completed_date": "2024-04-08T14:45:00Z",
      "status": "completed",
      "priority": "high",
      "outcome": "positive",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_8k2m9n5p3x",
      "deal_id": "deal_7k2m9n5p8x",
      "lead_id": null,
      "owner_id": "usr_445",
      "assigned_to": "usr_445",
      "created_at": "2024-04-08T13:50:00Z",
      "updated_at": "2024-04-08T14:50:00Z",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "00T8x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 3,
      "last_synced_at": "2024-04-12T06:30:00Z"
    },
    {
      "id": "act_3n8p5k2m9x",
      "external_id": "HUB-ACT-2001",
      "activity_id": "ACT-1002",
      "type": "Email",
      "subject": "Follow up on proposal",
      "description": null,
      "activity_date": "2024-04-09 10:30:00",
      "completed_date": "2024-04-09 10:35:00",
      "Status": "Completed",
      "priority": "medium",
      "customer_id": "cust_7h3j9k1m2n",
      "company_id": "comp_7h3j9k1m2n",
      "contact_id": "cont_3n5p8k2m9x",
      "deal_id": "deal_3n5p8k2m9x",
      "owner_id": "usr_447",
      "created_at": "2024-04-09T10:30:00Z",
      "updated_at": "2024-04-09T10:35:00Z",
      "source_system": "hubspot",
      "source_record_id": "2001",
      "sync_status": "synced",
      "sync_version": 2,
      "last_synced_at": "2024-04-11T22:15:00Z"
    },
    {
      "id": "act_8p2k9m5n3x",
      "external_id": "SF-EVENT-3001",
      "activity_id": "ACT-1003",
      "type": "meeting",
      "subject": "Product Demo",
      "description": "Demonstrated key features of the platform including analytics dashboard and reporting",
      "duration_minutes": 60,
      "activity_date": "2024-04-10T15:00:00Z",
      "completed_date": "2024-04-10T16:00:00Z",
      "status": "completed",
      "priority": "high",
      "outcome": "very_positive",
      "customer_id": "cust_5k2m9n4p7x",
      "company_id": "comp_5k2m9n4p7x",
      "contact_id": "cont_7k3m2n9p5x",
      "deal_id": null,
      "owner_id": "usr_449",
      "assigned_to": "usr_449",
      "created_at": "2024-04-10T14:50:00Z",
      "updated_at": "2024-04-10T16:05:00Z",
      "source_system": "salesforce",
      "source_record_id": "00U8x00000FgHiJ",
      "sync_status": "synced",
      "sync_version": 2,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "attendees": ["usr_449", "cont_7k3m2n9p5x"]
    },
    {
      "id": "act_2m5n9p3k8x",
      "external_id": "SF-TASK-1002",
      "activity_id": "ACT-1004",
      "type": "CALL",
      "subject": "Check-in call",
      "description": "",
      "activity_date": "2024-04-11T11:00:00Z",
      "due_date": "2024-04-11T11:00:00Z",
      "status": "scheduled",
      "priority": "medium",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_5p8k3m2n9x",
      "deal_id": "deal_5p8k3m2n9x",
      "owner_id": "usr_445",
      "assigned_to": "usr_445",
      "created_at": "2024-04-07T09:20:00Z",
      "updated_at": "2024-04-07T09:20:00Z",
      "created_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "00T8x00000KlMnO",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-04-12T06:30:00Z"
    },
    {
      "id": "act_9k3m2n5p8x",
      "external_id": "SF-TASK-1003",
      "activity_id": "ACT-1005",
      "type": "task",
      "subject": "Send contract for review",
      "description": "Prepare and send final contract documents to legal and customer",
      "due_date": "2024-04-12",
      "status": "in_progress",
      "priority": "high",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "deal_id": "deal_7k2m9n5p8x",
      "owner_id": "usr_445",
      "assigned_to": "usr_445",
      "created_at": "2024-04-10T17:00:00Z",
      "updated_at": "2024-04-11T09:00:00Z",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "00T8x00000PqRsT",
      "sync_status": "synced",
      "sync_version": 2,
      "last_synced_at": "2024-04-12T06:30:00Z"
    },
    {
      "id": "act_7k5m3n2p9x",
      "external_id": "GMAIL-MSG-4001",
      "activity_id": "ACT-1006",
      "type": "email",
      "subject": "RE: Pricing Question",
      "description": "Responded to pricing inquiry with detailed breakdown",
      "activity_date": "2024-03-15T09:45:00Z",
      "completed_date": "2024-03-15T09:45:00Z",
      "status": "COMPLETED",
      "lead_id": "lead_9k5m2n8p3x",
      "owner_id": "usr_445",
      "created_at": "2024-03-15T09:50:00Z",
      "updated_at": "2024-03-15T09:50:00Z",
      "source_system": "gmail_sync",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-03-15T10:00:00Z"
    },
    {
      "id": "act_6m8n3p2k9x",
      "external_id": "ZOHO-ACT-501",
      "activity_id": "ACT-1007",
      "type": "meeting",
      "subject": "Quarterly Business Review",
      "description": "Review Q1 performance and discuss Q2 goals",
      "duration_minutes": 90,
      "activity_date": "2024-04-05T13:00:00Z",
      "completed_date": "2024-04-05T14:30:00Z",
      "status": "completed",
      "priority": "high",
      "outcome": "positive",
      "customer_id": "cust_3k8m2n9p5x",
      "company_id": "comp_3k8m2n9p5x",
      "contact_id": "cont_4n9p2k5m8x",
      "deal_id": "deal_4n8p3k2m9x",
      "owner_id": "usr_451",
      "assigned_to": "usr_451",
      "created_at": "2024-04-05T12:50:00Z",
      "updated_at": "2024-04-05T14:35:00Z",
      "source_system": "zoho",
      "source_record_id": "501",
      "sync_status": "synced",
      "sync_version": 2,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "attendees": ["usr_451", "cont_4n9p2k5m8x", "usr_452"]
    },
    {
      "id": "act_4n2p9k5m8x",
      "external_id": "HUB-ACT-2002",
      "activity_id": "ACT-1008",
      "type": "note",
      "subject": "Customer feedback",
      "description": "Customer expressed interest in additional modules for Q3",
      "activity_date": "2024-04-11T16:30:00Z",
      "Status": "completed",
      "customer_id": "cust_7h3j9k1m2n",
      "company_id": "comp_7h3j9k1m2n",
      "contact_id": "cont_3n5p8k2m9x",
      "owner_id": "usr_447",
      "created_at": "2024-04-11T16:35:00Z",
      "updated_at": "2024-04-11T16:35:00Z",
      "source_system": "hubspot",
      "source_record_id": "2002",
      "sync_status": "pending",
      "sync_version": 1,
      "last_synced_at": "2024-04-11T22:15:00Z"
    }
  ],
  "count": 8,
  "page": 1,
  "per_page": 20
}
```

**Data Quality Issues:**
- Field name variations: `status` vs `Status`
- Type casing: "call", "Email", "meeting", "CALL", "task", "email", "note"
- Status casing: "completed", "Completed", "COMPLETED", "scheduled", "in_progress"
- Priority casing: "high", "medium"
- Date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS" vs date-only "YYYY-MM-DD"
- Null values: description, due_date, completed_date, deal_id, lead_id
- Empty description: ""
- Missing fields in some records: duration_minutes, outcome, attendees
- Activity linked to lead vs customer
- Inconsistent field presence: assigned_to, created_by, updated_by
- Different source systems: salesforce, hubspot, gmail_sync, zoho
- Outcome values: "positive", "very_positive"
- Attendees as array in some records

---


### 6. GET /notes

**Purpose:** Free-form annotations attached to entities

**Response Wrapper:** `{ "data": [...], "total": N }`

**Sample Response (v3):**

```json
{
  "data": [
    {
      "id": "note_8k2m9n5p3x",
      "external_id": "SF-NOTE-6001",
      "note_id": "NOTE-6001",
      "title": "Meeting Notes - Q1 Planning",
      "content": "Discussed Q1 goals and budget allocation. Customer is interested in expanding to 3 additional departments. Follow up needed on pricing for enterprise tier.",
      "note_type": "meeting_notes",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_8k2m9n5p3x",
      "deal_id": "deal_7k2m9n5p8x",
      "activity_id": "act_5k2m9n8p3x",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "owner_id": "usr_445",
      "created_at": "2024-04-08T14:50:00Z",
      "updated_at": "2024-04-08T14:50:00Z",
      "source_system": "salesforce",
      "source_record_id": "0028x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "is_pinned": true,
      "is_private": false,
      "tags": ["planning", "expansion", "q1"]
    },
    {
      "id": "note_3n5p8k2m9x",
      "external_id": "HUB-NOTE-3001",
      "note_id": "NOTE-6002",
      "title": null,
      "content": "Customer mentioned they are evaluating 2 other vendors. Need to follow up with competitive analysis and differentiation points.",
      "noteType": "general",
      "customer_id": "cust_7h3j9k1m2n",
      "company_id": "comp_7h3j9k1m2n",
      "deal_id": "deal_3n5p8k2m9x",
      "created_by": "usr_447",
      "owner_id": "usr_447",
      "created_at": "2024-04-09 11:15:00",
      "updated_at": "2024-04-09 11:15:00",
      "source_system": "hubspot",
      "source_record_id": "3001",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "is_pinned": false
    },
    {
      "id": "note_5p8k3m2n9x",
      "external_id": "SF-NOTE-6003",
      "note_id": "NOTE-6003",
      "title": "Technical Requirements",
      "content": "Must integrate with existing Salesforce instance. SSO required via SAML 2.0. Data residency in EU. GDPR compliance mandatory. API rate limit concerns for batch processing.",
      "note_type": "technical",
      "customer_id": "cust_8x9k2m4n5p",
      "company_id": "comp_8x9k2m4n5p",
      "contact_id": "cont_5p8k3m2n9x",
      "deal_id": "deal_5p8k3m2n9x",
      "created_by": "usr_445",
      "updated_by": "usr_448",
      "owner_id": "usr_445",
      "created_at": "2024-03-12T16:30:00Z",
      "updated_at": "2024-03-25T10:15:00Z",
      "source_system": "salesforce",
      "source_record_id": "0028x00000FgHiJ",
      "sync_status": "synced",
      "sync_version": 3,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "is_pinned": true,
      "is_private": false,
      "tags": ["technical", "requirements", "integration", "compliance"]
    },
    {
      "id": "note_2m9n5p3k8x",
      "external_id": "SF-NOTE-6004",
      "note_id": "NOTE-6004",
      "Title": "Post-Sale Follow-up",
      "content": "Customer very satisfied with implementation. Mentioned potential referral to sister company DataFlow Europe. Schedule intro call for next week.",
      "note_type": "follow_up",
      "customer_id": "cust_5k2m9n4p7x",
      "company_id": "comp_5k2m9n4p7x",
      "deal_id": "deal_2m9n5p3k8x",
      "created_by": "usr_449",
      "owner_id": "usr_449",
      "created_at": "2024-04-01T09:00:00Z",
      "updated_at": "2024-04-01T09:00:00Z",
      "source_system": "salesforce",
      "source_record_id": "0028x00000KlMnO",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-04-12T07:00:00Z",
      "is_pinned": false,
      "tags": ["success", "referral"]
    },
    {
      "id": "note_7k3m2n9p5x",
      "external_id": "HUB-NOTE-3002",
      "note_id": "NOTE-6005",
      "title": "Budget Concerns",
      "content": "",
      "note_type": "general",
      "customer_id": "cust_7h3j9k1m2n",
      "company_id": "comp_7h3j9k1m2n",
      "contact_id": "cont_3n5p8k2m9x",
      "deal_id": "deal_3n5p8k2m9x",
      "created_by": "usr_447",
      "owner_id": "usr_447",
      "created_at": "2024-03-28T15:20:00Z",
      "updated_at": "2024-03-28T15:20:00Z",
      "source_system": "hubspot",
      "source_record_id": "3002",
      "sync_status": "synced",
      "sync_version": 1,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "is_pinned": false
    },
    {
      "id": "note_9k5m3n2p8x",
      "external_id": "ZOHO-NOTE-501",
      "note_id": "NOTE-6006",
      "title": "Cultural Considerations",
      "content": "Important to schedule calls outside of Ramadan prayer times. Prefer afternoon meetings Cairo time. Decision maker is Fatima but CFO approval also required.",
      "note_type": "account_planning",
      "customer_id": "cust_3k8m2n9p5x",
      "company_id": "comp_3k8m2n9p5x",
      "contact_id": "cont_4n9p2k5m8x",
      "deal_id": "deal_4n8p3k2m9x",
      "created_by": "usr_451",
      "owner_id": "usr_451",
      "created_at": "2024-03-28T11:00:00Z",
      "updated_at": "2024-04-02T09:00:00Z",
      "source_system": "zoho",
      "source_record_id": "501",
      "sync_status": "synced",
      "sync_version": 2,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "is_pinned": true,
      "is_private": false,
      "tags": ["cultural", "emea", "account_planning"]
    }
  ],
  "total": 6
}
```

**Data Quality Issues:**
- Field name variations: `title` vs `Title`, `note_type` vs `noteType`
- Null title
- Empty content: ""
- Date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS"
- Missing fields in some records: contact_id, activity_id, updated_by, is_private, tags
- Inconsistent field presence across records

---

### 7. GET /companies

**Purpose:** Organization/account master data

**Response Wrapper:** `{ "companies": [...], "total_count": N, "page_number": 1, "page_size": 20 }`

**Sample Response (v3):**

```json
{
  "companies": [
    {
      "id": "comp_8x9k2m4n5p",
      "external_id": "SF-ACC-10234",
      "company_id": "COMP-10234",
      "name": "Acme Corporation",
      "legal_name": "Acme Corporation Inc.",
      "industry": "Technology",
      "sub_industry": "Enterprise Software",
      "employee_count": 1250,
      "annual_revenue": 45000000,
      "revenue_currency": "USD",
      "website": "https://www.acmecorp.com",
      "phone": "+1-555-0100",
      "email": "info@acmecorp.com",
      "status": "active",
      "lifecycle_stage": "customer",
      "customer_since": "2023-01-15",
      "address": {
        "street": "123 Tech Boulevard",
        "street2": "Suite 500",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94105",
        "country": "USA",
        "country_code": "US"
      },
      "billing_address": {
        "street": "123 Tech Boulevard",
        "city": "San Francisco",
        "state": "CA",
        "postal_code": "94105",
        "country": "USA"
      },
      "created_at": "2023-01-15T10:30:00Z",
      "updated_at": "2024-03-20T14:22:11Z",
      "last_activity_at": "2024-04-11T14:00:00Z",
      "first_seen_at": "2022-11-20T08:00:00Z",
      "owner_id": "usr_445",
      "assigned_team": "enterprise",
      "created_by": "usr_445",
      "updated_by": "usr_445",
      "source_system": "salesforce",
      "source_record_id": "0018x00000AbCdE",
      "sync_status": "synced",
      "sync_version": 47,
      "last_synced_at": "2024-04-12T06:30:00Z",
      "country": "USA",
      "region": "North America",
      "timezone": "America/Los_Angeles",
      "parent_company_id": null,
      "is_parent": true,
      "subsidiaries_count": 3
    },
    {
      "id": "comp_7h3j9k1m2n",
      "external_id": "HUB-COMP-2001",
      "company_id": "COMP-10235",
      "name": "TechStart Inc.",
      "industry": "software",
      "employee_count": "50-100",
      "annual_revenue": null,
      "website": "www.techstart.com",
      "phone": "555-0124",
      "status": "Active",
      "lifecycle_stage": "customer",
      "customer_since": "2023-02-10",
      "address": {
        "street": "456 Innovation Drive",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "US"
      },
      "created_at": "2023-02-10 11:45:30",
      "updated_at": "2024-01-15T09:10:22Z",
      "last_activity_at": "2024-04-09T10:00:00Z",
      "owner_id": "usr_447",
      "assigned_team": "SMB",
      "source_system": "hubspot",
      "source_record_id": "2001",
      "sync_status": "synced",
      "sync_version": 12,
      "last_synced_at": "2024-04-11T22:15:00Z",
      "country": "US",
      "region": "North America"
    },
    {
      "id": "comp_8x9k2m4n5p",
      "external_id": "SF-ACC-10236",
      "company_id": "COMP-10236",
      "name": "Global Solutions Ltd",
      "legal_name": "Global Solutions Limited",
      "industry": "Consulting",
      "employee_count": 850,
      "annual_revenue": 28000000,
      "revenue_currency": "GBP",
      "website": "https://globalsolutions.co.uk",
      "phone": "+44 20 7123 4567",
      "status": "active",
      "lifecycle_stage": "customer",
      "customer_since": "2023-03-22",
      "street": "789 Business Park",
      "city": "London",
      "postal_code": "SW1A 1AA",
      "country": "UK",
      "created_at": "2023-03-22T08:15:00Z",
      "updated_at": null,
      "last_activity_at": "2023-12-05T14:30:00Z",
      "owner_id": null,
      "source_system": "salesforce",
      "source_record_id": "0018x00000XyZaB",
      "sync_status": "synced",
      "sync_version": 3,
      "last_synced_at": "2023-12-10T03:00:00Z",
      "region": "EMEA"
    },
    {
      "id": "comp_5k2m9n4p7x",
      "external_id": "SF-ACC-10238",
      "company_id": "COMP-10238",
      "name": "DataFlow Systems",
      "legal_name": "DataFlow Systems Corp.",
      "Industry": "DATA_ANALYTICS",
      "sub_industry": "Business Intelligence",
      "employee_count": 320,
      "annual_revenue": 15500000,
      "revenue_currency": "CAD",
      "website": "https://www.dataflow.io",
      "phone": "+1-416-555-0100",
      "email": "contact@dataflow.io",
      "status": "ACTIVE",
      "lifecycle_stage": "customer",
      "customer_since": "2023-06-18",
      "address": {
        "street": "100 Data Lane",
        "street2": "Floor 12",
        "city": "Toronto",
        "state": "ON",
        "postal_code": "M5H 2N2",
        "country": "Canada",
        "country_code": "CA"
      },
      "created_at": "2023-06-18T16:45:00Z",
      "updated_at": "2024-04-10T11:20:33Z",
      "last_activity_at": "2024-04-11T16:00:00Z",
      "first_seen_at": "2023-05-10T09:00:00Z",
      "owner_id": "usr_449",
      "assigned_team": "Enterprise",
      "created_by": "usr_449",
      "updated_by": "usr_449",
      "source_system": "salesforce",
      "source_record_id": "0018x00000QwErTy",
      "sync_status": "synced",
      "sync_version": 89,
      "last_synced_at": "2024-04-12T07:00:00Z",
      "country": "Canada",
      "region": "North America",
      "timezone": "America/Toronto"
    },
    {
      "id": "comp_2p9k8m3n1x",
      "external_id": "PIPE-COMP-789",
      "company_id": "COMP-10237",
      "name": "innovate labs",
      "industry": "Research",
      "employee_count": null,
      "website": "innovatelabs.com",
      "status": "inactive",
      "lifecycle_stage": "churned",
      "churn_date": "2023-12-01",
      "address": {
        "city": "Boston",
        "state": "MA",
        "country": "USA"
      },
      "created_at": "2022-11-05T14:20:00Z",
      "updated_at": "2023-12-01T10:30:00Z",
      "last_activity_at": "2023-06-15T11:00:00Z",
      "owner_id": "usr_445",
      "source_system": "pipedrive",
      "source_record_id": "789",
      "sync_status": "failed",
      "sync_version": 8,
      "last_synced_at": "2024-04-10T12:00:00Z",
      "country": "USA",
      "is_active": false
    },
    {
      "id": "comp_9m2n5p8k3x",
      "external_id": "HUB-COMP-2002",
      "company_id": "COMP-10240",
      "name": "CloudVentures",
      "legal_name": "CloudVentures LLC",
      "industry": "Cloud Services",
      "employee_count": "100-250",
      "website": "https://cloudventures.com",
      "phone": "+1-555-0155",
      "status": "deleted",
      "lifecycle_stage": "churned",
      "customer_since": "2022-08-12",
      "churn_date": "2023-10-15",
      "address": {
        "street": "200 Cloud Street",
        "city": "Seattle",
        "state": "WA",
        "postal_code": "98101",
        "country": "USA"
      },
      "created_at": "2022-08-12T09:00:00Z",
      "updated_at": "2023-10-15T13:25:00Z",
      "deleted_at": "2023-10-15T13:25:00Z",
      "last_activity_at": "2023-09-30T16:00:00Z",
      "is_deleted": true,
      "owner_id": "usr_450",
      "source_system": "hubspot",
      "source_record_id": "2002",
      "sync_status": "synced",
      "sync_version": 15,
      "last_synced_at": "2023-10-15T14:00:00Z",
      "country": "USA",
      "region": "North America"
    },
    {
      "id": "comp_3k8m2n9p5x",
      "external_id": "ZOHO-COMP-5678",
      "company_id": "COMP-10241",
      "name": "Pyramid Solutions",
      "legal_name": "Pyramid Solutions SAE",
      "industry": "Consulting",
      "sub_industry": "Management Consulting",
      "employee_count": 180,
      "annual_revenue": 850000,
      "revenue_currency": "EGP",
      "website": "https://www.pyramidsolutions.eg",
      "phone": "+20 2 1234 5678",
      "email": "info@pyramidsolutions.eg",
      "status": "active",
      "lifecycle_stage": "customer",
      "customer_since": "2023-09-10",
      "address": {
        "street": "15 Nile Corniche",
        "city": "Cairo",
        "postal_code": "11511",
        "country": "Egypt",
        "country_code": "EG"
      },
      "created_at": "2023-09-10T07:30:00Z",
      "updated_at": "2024-04-05T12:15:00Z",
      "last_activity_at": "2024-04-10T09:00:00Z",
      "first_seen_at": "2023-08-22T10:00:00Z",
      "owner_id": "usr_451",
      "assigned_team": "EMEA",
      "created_by": "usr_451",
      "updated_by": "usr_451",
      "source_system": "zoho",
      "source_record_id": "5678",
      "sync_status": "synced",
      "sync_version": 22,
      "last_synced_at": "2024-04-12T05:30:00Z",
      "country": "EGYPT",
      "region": "EMEA",
      "timezone": "Africa/Cairo"
    }
  ],
  "total_count": 7,
  "page_number": 1,
  "page_size": 20
}
```

**Data Quality Issues:**
- Duplicate IDs: `comp_8x9k2m4n5p` appears twice (records 1 and 3)
- Field name variations: `industry` vs `Industry`
- Industry casing: "Technology", "software", "Consulting", "DATA_ANALYTICS", "Research", "Cloud Services"
- Status casing: "active", "Active", "ACTIVE", "inactive", "deleted"
- Team casing: "enterprise", "SMB", "Enterprise", "EMEA"
- Employee count: integer vs string range "50-100", "100-250"
- Country variations: "USA", "US", "UK", "Canada", "Egypt", "EGYPT"
- Address structure: nested object vs flat fields (street, city, postal_code)
- Website formats: with/without https://, with/without www
- Null values: annual_revenue, employee_count, updated_at, owner_id
- Missing fields: legal_name, sub_industry, billing_address, parent_company_id
- Soft-deleted company with deleted_at and is_deleted
- Churned companies with churn_date
- Stale data: record 3 not updated since 2023
- Inconsistent field presence across records

---


### 8. GET /owners

**Purpose:** Sales reps, account managers, users

**Response Wrapper:** `[ ... ]` (bare array)

**Sample Response:**

```json
[
  {
    "id": "usr_445",
    "user_id": "USR-445",
    "external_id": "SF-USER-445",
    "email": "john.doe@company.com",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "role": "Account Executive",
    "team": "enterprise",
    "status": "active",
    "is_active": true,
    "created_at": "2022-01-10T09:00:00Z",
    "updated_at": "2024-03-15T10:00:00Z",
    "last_login_at": "2024-04-12T08:30:00Z"
  },
  {
    "id": "usr_447",
    "user_id": "USR-447",
    "external_id": "HUB-USER-447",
    "email": "jane.smith@company.com",
    "firstName": "Jane",
    "lastName": "Smith",
    "role": "Sales Representative",
    "team": "SMB",
    "status": "Active",
    "is_active": true,
    "created_at": "2022-03-15 10:00:00",
    "updated_at": "2024-04-10T14:20:00Z",
    "last_login_at": "2024-04-11T16:45:00Z"
  },
  {
    "id": "usr_449",
    "user_id": "USR-449",
    "external_id": "SF-USER-449",
    "email": "mike.johnson@company.com",
    "first_name": "Mike",
    "last_name": "Johnson",
    "full_name": "Mike Johnson",
    "role": "Senior Account Executive",
    "team": "Enterprise",
    "status": "active",
    "is_active": true,
    "created_at": "2021-11-20T08:00:00Z",
    "updated_at": "2024-04-08T09:15:00Z",
    "last_login_at": "2024-04-12T07:00:00Z"
  },
  {
    "id": "usr_450",
    "user_id": "USR-450",
    "external_id": "HUB-USER-450",
    "email": "sarah.williams@company.com",
    "first_name": "Sarah",
    "last_name": "Williams",
    "role": "Account Executive",
    "team": "smb",
    "status": "inactive",
    "is_active": false,
    "created_at": "2022-06-01T10:00:00Z",
    "updated_at": "2023-11-30T15:00:00Z",
    "last_login_at": "2023-11-28T14:30:00Z",
    "deactivated_at": "2023-11-30T15:00:00Z"
  },
  {
    "id": "usr_451",
    "user_id": "USR-451",
    "external_id": "ZOHO-USER-451",
    "email": "ahmed.hassan@company.com",
    "first_name": "Ahmed",
    "last_name": "Hassan",
    "full_name": "Ahmed Hassan",
    "role": "Regional Sales Manager",
    "team": "EMEA",
    "status": "active",
    "is_active": true,
    "created_at": "2023-08-15T07:00:00Z",
    "updated_at": "2024-04-05T11:00:00Z",
    "last_login_at": "2024-04-12T05:30:00Z",
    "timezone": "Africa/Cairo"
  },
  {
    "id": "usr_448",
    "user_id": "USR-448",
    "email": "lisa.chen@company.com",
    "first_name": "Lisa",
    "last_name": "Chen",
    "role": "Sales Engineer",
    "team": "enterprise",
    "status": "active",
    "is_active": true,
    "created_at": "2022-09-10T09:00:00Z",
    "updated_at": "2024-03-20T10:30:00Z"
  },
  {
    "id": "usr_452",
    "user_id": "USR-452",
    "external_id": "ZOHO-USER-452",
    "email": "fatima.ali@company.com",
    "firstName": "Fatima",
    "lastName": "Ali",
    "role": "Account Manager",
    "team": "EMEA",
    "Status": "active",
    "is_active": true,
    "created_at": "2023-09-01T08:00:00Z",
    "updated_at": "2024-04-02T09:00:00Z",
    "last_login_at": "2024-04-11T10:00:00Z"
  }
]
```

**Data Quality Issues:**
- Field name variations: `first_name`/`firstName`, `last_name`/`lastName`, `status`/`Status`
- Status casing: "active", "Active", "inactive"
- Team casing: "enterprise", "SMB", "Enterprise", "smb", "EMEA"
- Date formats: ISO 8601 vs "YYYY-MM-DD HH:MM:SS"
- Missing fields: external_id, full_name, last_login_at, timezone, deactivated_at
- Bare array response (no wrapper)

---

### 9. GET /pipeline-stages

**Purpose:** Deal stage definitions

**Response Wrapper:** `{ "stages": [...] }`

**Sample Response:**

```json
{
  "stages": [
    {
      "id": "stage_1",
      "stage_id": "STAGE-1",
      "name": "qualification",
      "display_name": "Qualification",
      "order": 1,
      "probability": 10,
      "is_active": true,
      "is_closed": false,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_2",
      "stage_id": "STAGE-2",
      "name": "discovery",
      "display_name": "Discovery",
      "order": 2,
      "probability": 25,
      "is_active": true,
      "is_closed": false,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_3",
      "stage_id": "STAGE-3",
      "name": "proposal",
      "display_name": "Proposal",
      "order": 3,
      "probability": 50,
      "is_active": true,
      "is_closed": false,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_4",
      "stage_id": "STAGE-4",
      "name": "negotiation",
      "display_name": "Negotiation",
      "order": 4,
      "probability": 75,
      "is_active": true,
      "is_closed": false,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_5",
      "stage_id": "STAGE-5",
      "name": "verbal_commit",
      "display_name": "Verbal Commit",
      "order": 5,
      "probability": 90,
      "is_active": true,
      "is_closed": false,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_6",
      "stage_id": "STAGE-6",
      "name": "closed_won",
      "display_name": "Closed Won",
      "order": 6,
      "probability": 100,
      "is_active": true,
      "is_closed": true,
      "is_won": true,
      "created_at": "2021-01-01T00:00:00Z"
    },
    {
      "id": "stage_7",
      "stage_id": "STAGE-7",
      "name": "closed_lost",
      "display_name": "Closed Lost",
      "order": 7,
      "probability": 0,
      "is_active": true,
      "is_closed": true,
      "is_won": false,
      "created_at": "2021-01-01T00:00:00Z"
    }
  ]
}
```

---

### 10. GET /sync-status

**Purpose:** Sync health by source system

**Response Wrapper:** `{ "sync_status": {...}, "last_updated": "..." }`

**Sample Response:**

```json
{
  "sync_status": {
    "salesforce": {
      "status": "healthy",
      "last_sync": "2024-04-12T06:30:00Z",
      "next_sync": "2024-04-12T12:30:00Z",
      "records_synced": 1247,
      "records_failed": 3,
      "sync_duration_seconds": 45,
      "error_rate": 0.24
    },
    "hubspot": {
      "status": "degraded",
      "last_sync": "2024-04-11T22:15:00Z",
      "next_sync": "2024-04-12T10:15:00Z",
      "records_synced": 456,
      "records_failed": 12,
      "sync_duration_seconds": 120,
      "error_rate": 2.56,
      "last_error": "Rate limit exceeded"
    },
    "pipedrive": {
      "status": "error",
      "last_sync": "2024-04-10T12:00:00Z",
      "next_sync": "2024-04-12T18:00:00Z",
      "records_synced": 0,
      "records_failed": 89,
      "sync_duration_seconds": 5,
      "error_rate": 100.0,
      "last_error": "Authentication failed"
    },
    "zoho": {
      "status": "healthy",
      "last_sync": "2024-04-12T05:30:00Z",
      "next_sync": "2024-04-12T11:30:00Z",
      "records_synced": 234,
      "records_failed": 0,
      "sync_duration_seconds": 28,
      "error_rate": 0.0
    }
  },
  "last_updated": "2024-04-12T08:00:00Z"
}
```

---

### 11. GET /metadata

**Purpose:** API schema and field definitions

**Response Wrapper:** `{ "entities": {...}, "version": "...", "generated_at": "..." }`

**Sample Response:**

```json
{
  "entities": {
    "customers": {
      "fields": [
        {"name": "id", "type": "string", "required": true},
        {"name": "external_id", "type": "string", "required": false},
        {"name": "customer_id", "type": "string", "required": true},
        {"name": "name", "type": "string", "required": true},
        {"name": "email", "type": "string", "required": false},
        {"name": "phone", "type": "string", "required": false},
        {"name": "status", "type": "string", "required": true},
        {"name": "created_at", "type": "datetime", "required": true},
        {"name": "updated_at", "type": "datetime", "required": false}
      ],
      "relationships": {
        "company_id": "companies",
        "owner_id": "owners"
      }
    },
    "contacts": {
      "fields": [
        {"name": "id", "type": "string", "required": true},
        {"name": "first_name", "type": "string", "required": true},
        {"name": "last_name", "type": "string", "required": false},
        {"name": "email", "type": "string", "required": false},
        {"name": "company_id", "type": "string", "required": true}
      ],
      "relationships": {
        "company_id": "companies",
        "customer_id": "customers",
        "owner_id": "owners"
      }
    }
  },
  "version": "3.2.1",
  "generated_at": "2024-04-12T08:00:00Z"
}
```

---

### 12. GET /search?q=

**Purpose:** Cross-entity search

**Query Parameters:** `q` (required), `entity_type` (optional), `limit` (optional)

**Response Wrapper:** `{ "results": [...], "query": "...", "total": N }`

**Sample Response:**

```json
{
  "results": [
    {
      "entity_type": "customer",
      "entity_id": "cust_8x9k2m4n5p",
      "name": "Acme Corporation",
      "email": "contact@acmecorp.com",
      "match_field": "name",
      "match_score": 0.95
    },
    {
      "entity_type": "contact",
      "entity_id": "cont_8k2m9n5p3x",
      "name": "John Smith",
      "email": "john.smith@acmecorp.com",
      "company_name": "Acme Corporation",
      "match_field": "company_name",
      "match_score": 0.87
    },
    {
      "entity_type": "deal",
      "entity_id": "deal_7k2m9n5p8x",
      "name": "Acme Corp - Enterprise License",
      "amount": 125000,
      "match_field": "name",
      "match_score": 0.82
    }
  ],
  "query": "acme",
  "total": 3,
  "search_time_ms": 45
}
```

---

### 13. GET /events

**Purpose:** Change event log / audit trail

**Response Wrapper:** `{ "events": [...], "total": N, "page": 1 }`

**Sample Response:**

```json
{
  "events": [
    {
      "id": "evt_9k2m5n8p3x",
      "event_id": "EVT-10001",
      "event_type": "customer.updated",
      "entity_type": "customer",
      "entity_id": "cust_8x9k2m4n5p",
      "timestamp": "2024-04-11T16:00:00Z",
      "user_id": "usr_445",
      "source_system": "salesforce",
      "changes": {
        "status": {"old": "active", "new": "active"},
        "last_activity_at": {"old": "2024-04-10T09:15:00Z", "new": "2024-04-11T14:00:00Z"}
      },
      "metadata": {
        "sync_version": 47,
        "ip_address": "192.168.1.100"
      }
    },
    {
      "id": "evt_3n8p2k5m9x",
      "event_id": "EVT-10002",
      "event_type": "deal.created",
      "entity_type": "deal",
      "entity_id": "deal_7k2m9n5p8x",
      "timestamp": "2024-04-01T09:00:00Z",
      "user_id": "usr_445",
      "source_system": "salesforce",
      "changes": null,
      "metadata": {
        "sync_version": 1
      }
    },
    {
      "id": "evt_5p2k9m3n8x",
      "event_id": "EVT-10003",
      "event_type": "contact.deleted",
      "entity_type": "contact",
      "entity_id": "cont_6m3n8p2k9x",
      "timestamp": "2023-10-15T13:30:00Z",
      "user_id": "usr_450",
      "source_system": "hubspot",
      "changes": {
        "is_deleted": {"old": false, "new": true},
        "deleted_at": {"old": null, "new": "2023-10-15T13:30:00Z"}
      },
      "metadata": {
        "sync_version": 8,
        "reason": "customer_churned"
      }
    }
  ],
  "total": 3,
  "page": 1
}
```

---

## Entity Relationships

```
Companies (1) ──→ (N) Customers
Companies (1) ──→ (N) Contacts
Customers (1) ──→ (N) Contacts
Customers (1) ──→ (N) Deals
Customers (1) ──→ (N) Activities
Customers (1) ──→ (N) Notes
Leads (1) ──→ (0..1) Customers (conversion)
Leads (1) ──→ (0..1) Contacts (conversion)
Leads (1) ──→ (0..1) Deals (conversion)
Leads (1) ──→ (N) Activities
Contacts (1) ──→ (N) Activities
Contacts (1) ──→ (N) Notes
Deals (1) ──→ (N) Activities
Deals (1) ──→ (N) Notes
Deals (N) ──→ (1) Pipeline Stages
Owners (1) ──→ (N) Customers
Owners (1) ──→ (N) Contacts
Owners (1) ──→ (N) Leads
Owners (1) ──→ (N) Deals
Owners (1) ──→ (N) Activities
```

---

## Versioning Behavior

### Version 1 (v1) - January 2023 Snapshot

**Characteristics:**
- Oldest data, most inconsistent
- More duplicate records
- More missing fields
- Fewer records overall (early system state)
- More field name variations
- More date format inconsistencies

**Changes from v3:**
- Remove records created after 2023-01-31
- Add more duplicates
- Remove some fields that were added later
- Use older sync_version numbers
- More null values

### Version 2 (v2) - September 2023 Snapshot

**Characteristics:**
- Partial cleanup attempted
- Some duplicates removed but not all
- Some field names standardized but not all
- Medium record count
- Some soft-deleted records

**Changes from v3:**
- Remove records created after 2023-09-30
- Keep some duplicates
- Mix of old and new field names
- Some records show as active that are deleted in v3

### Version 3 (v3) - Current State (Default)

**Characteristics:**
- Most recent data
- Still has quality issues (realistic)
- Highest record count
- Most complete field coverage
- Latest sync versions

---

## Pagination Behavior

### Standard Pagination
- Default: `page=1&limit=20`
- Max limit: 100
- Response includes: `total`, `page`, `limit`, `has_more`

### Intentional Pagination Issues

**Issue 1: Duplicate Records Across Pages**
- Record `cust_7h3j9k1m2n` appears on page 1 and page 2
- Caused by unstable sort order

**Issue 2: Shifting Page Boundaries**
- Total count changes between page requests
- New records inserted during pagination
- Page 3 request returns different records than expected

**Issue 3: Incomplete Last Page**
- Last page has fewer records than `limit` suggests
- Some records missing from final page

**Issue 4: Total Count Mismatch**
- `total` field doesn't match actual record count
- Off by 1-3 records typically

---


## Mockoon Implementation Notes

### Basic Setup

1. **Create Environment**
   - Name: "CRM Production Mock API"
   - Port: 3000
   - Enable CORS

2. **Global Headers**
   ```json
   {
     "Content-Type": "application/json",
     "X-API-Version": "{{queryParam 'version' 'v3'}}",
     "X-Request-ID": "{{faker 'datatype.uuid'}}",
     "X-RateLimit-Limit": "1000",
     "X-RateLimit-Remaining": "{{faker 'datatype.number' min=800 max=1000}}"
   }
   ```

3. **Latency**
   - Set global latency: 50-200ms (realistic API response time)
   - Add random jitter for realism

### Endpoint Configuration

**For each endpoint:**

1. **List Endpoints** (e.g., GET /customers)
   - Method: GET
   - Path: `/customers` (or appropriate path)
   - Response: 200 OK
   - Body: Copy JSON from samples above
   - Headers: Content-Type: application/json

2. **Detail Endpoints** (e.g., GET /customers/:id)
   - Method: GET
   - Path: `/customers/:id`
   - Response: 200 OK
   - Body: Single record from list endpoint
   - Use Mockoon's `{{urlParam 'id'}}` to match ID
   - Add 404 response for unknown IDs

3. **Query Parameters**
   - Add rules for `version` parameter
   - Add rules for `page` and `limit` parameters
   - Use Mockoon's templating: `{{queryParam 'version' 'v3'}}`

### Versioning Implementation

**Option 1: Multiple Responses with Rules**

For each endpoint, create 3 responses:
- Response 1: v1 data (rule: `version` equals `v1`)
- Response 2: v2 data (rule: `version` equals `v2`)
- Response 3: v3 data (default, no rule)

**Option 2: Single Response with Templating**

Use Mockoon's templating to conditionally include/exclude records:
```json
{{#if (eq (queryParam 'version') 'v1')}}
  // v1 records only
{{else if (eq (queryParam 'version') 'v2')}}
  // v2 records only
{{else}}
  // v3 records (default)
{{/if}}
```

**Recommended:** Option 1 for simplicity and clarity

### Pagination Implementation

1. **Query Parameters**
   - `page` (default: 1)
   - `limit` (default: 20, max: 100)
   - `offset` (alternative to page)

2. **Response Calculation**
   - Use Mockoon's `{{queryParam 'page' '1'}}` and `{{queryParam 'limit' '20'}}`
   - Calculate `has_more`: `{{gt total (add (mult page limit) 0)}}`
   - Note: Full pagination logic requires custom code or multiple responses

3. **Simplified Approach**
   - Create separate responses for page 1, page 2, etc.
   - Use rules: `page` equals `1`, `page` equals `2`
   - Include intentional issues (duplicates, shifting boundaries)

### Error Responses

Add additional responses for error cases:

**404 Not Found**
```json
{
  "error": "not_found",
  "message": "Resource not found",
  "status": 404,
  "timestamp": "2024-04-12T08:00:00Z"
}
```

**429 Rate Limit**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "status": 429,
  "retry_after": 60
}
```

**500 Internal Server Error**
```json
{
  "error": "internal_error",
  "message": "An unexpected error occurred",
  "status": 500,
  "request_id": "{{faker 'datatype.uuid'}}"
}
```

### Free Features Only

This implementation uses only free Mockoon features:
- ✅ Multiple routes
- ✅ Multiple responses per route
- ✅ Response rules (query params, headers)
- ✅ Templating (Handlebars)
- ✅ Faker.js integration
- ✅ URL parameters
- ✅ Custom headers
- ✅ CORS configuration
- ✅ Latency simulation

**Not used (premium features):**
- ❌ Callbacks
- ❌ Data buckets (advanced)
- ❌ Proxy mode (advanced)
- ❌ Cloud sync

---

## Data Quality Issue Summary

### By Category

**1. Duplicate Records**
- Same ID appearing multiple times
- Same entity with different IDs
- Partial duplicates (similar but not identical)

**2. Missing/Null Values**
- Required fields null or missing
- Inconsistent null vs empty string
- Partial records

**3. Inconsistent Formatting**
- Date formats: ISO 8601, SQL datetime, slash dates
- Phone formats: various international styles
- Email casing: mixed case
- Status/enum casing: inconsistent

**4. Field Name Variations**
- snake_case vs camelCase
- Different names for same concept
- Field name typos

**5. Invalid Data**
- Incomplete emails (missing domain/TLD)
- Empty strings where null expected
- Invalid phone formats
- Malformed URLs

**6. Type Inconsistencies**
- String vs number (amount, probability)
- String ranges vs integers (employee_count)
- Date strings vs timestamps

**7. Structural Inconsistencies**
- Nested objects vs flat fields
- Different response wrappers
- Inconsistent field presence

**8. Relationship Issues**
- Orphaned records (missing foreign keys)
- Circular references
- Stale relationships

**9. Temporal Issues**
- Conflicting timestamps
- Stale data (not updated)
- Future dates
- Missing updated_at

**10. Source System Artifacts**
- Different schemas per source
- Sync status variations
- Version drift
- Failed syncs

### By Endpoint

| Endpoint | Duplicates | Nulls | Format Issues | Field Variations | Invalid Data |
|----------|------------|-------|---------------|------------------|--------------|
| /customers | 2 | 8 | 12 | 4 | 3 |
| /contacts | 1 | 5 | 10 | 6 | 2 |
| /leads | 1 | 6 | 8 | 4 | 2 |
| /deals | 1 | 4 | 9 | 3 | 0 |
| /activities | 0 | 4 | 6 | 2 | 0 |
| /notes | 0 | 2 | 2 | 2 | 0 |
| /companies | 1 | 5 | 11 | 2 | 0 |
| /owners | 0 | 2 | 3 | 3 | 0 |

---

## Testing Scenarios

### ETL Pipeline Testing

**1. Deduplication**
- Detect duplicate IDs
- Merge similar records
- Choose canonical version
- Track merge history

**2. Normalization**
- Standardize date formats
- Normalize casing
- Clean phone numbers
- Validate emails

**3. Validation**
- Required field checks
- Format validation
- Referential integrity
- Business rule validation

**4. Type Conversion**
- String to number
- Date parsing
- Boolean normalization
- Handle mixed types

**5. Schema Evolution**
- Handle field name changes
- Map old to new fields
- Handle missing fields
- Version tracking

### Data Quality Checks

**1. Completeness**
- Missing required fields
- Null value analysis
- Field population rates
- Record completeness score

**2. Consistency**
- Field name consistency
- Value casing consistency
- Format consistency
- Cross-field consistency

**3. Accuracy**
- Email validation
- Phone validation
- URL validation
- Date range validation

**4. Uniqueness**
- Duplicate detection
- Primary key uniqueness
- Natural key uniqueness
- Fuzzy matching

**5. Timeliness**
- Stale data detection
- Update frequency
- Sync lag analysis
- Data freshness score

### Data Modeling

**1. Dimensional Modeling**
- Identify facts and dimensions
- Handle slowly changing dimensions
- Create surrogate keys
- Build star schema

**2. Entity Resolution**
- Match duplicate entities
- Merge records
- Create golden records
- Track lineage

**3. Relationship Mapping**
- Map foreign keys
- Handle orphaned records
- Build relationship graph
- Validate relationships

**4. Temporal Modeling**
- Track changes over time
- Handle late-arriving data
- Implement SCD Type 2
- Version snapshots

---

## 5 Additional Realism Improvements

### 1. Rate Limiting and Throttling

**Implementation:**
- Add 429 responses for specific endpoints
- Include `Retry-After` header
- Vary rate limits by endpoint
- Simulate burst limits

**Example:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit of 1000 requests per hour exceeded",
  "status": 429,
  "retry_after": 3600,
  "limit": 1000,
  "remaining": 0,
  "reset_at": "2024-04-12T09:00:00Z"
}
```

**Testing Value:**
- Test retry logic
- Implement exponential backoff
- Handle rate limit errors gracefully
- Queue management

---

### 2. Partial Failures and Inconsistent Availability

**Implementation:**
- Some endpoints return 500 errors intermittently
- Specific record IDs always fail (e.g., `cust_error_test`)
- Timeout simulation (very slow responses)
- Partial data returns (incomplete records)

**Example:**
```json
{
  "error": "partial_failure",
  "message": "Some records could not be retrieved",
  "status": 207,
  "successful": 18,
  "failed": 2,
  "failed_ids": ["cust_8x9k2m4n5p", "cust_2p9k8m3n1x"],
  "data": [...]
}
```

**Testing Value:**
- Test error handling
- Implement retry logic
- Handle partial data
- Circuit breaker patterns

---

### 3. Webhook Events and Change Data Capture

**Implementation:**
- Add `/webhooks/events` endpoint
- Include event types: created, updated, deleted, merged
- Add sequence numbers for ordering
- Simulate out-of-order delivery
- Include duplicate events

**Example:**
```json
{
  "events": [
    {
      "id": "evt_9k2m5n8p3x",
      "event_type": "customer.updated",
      "entity_type": "customer",
      "entity_id": "cust_8x9k2m4n5p",
      "sequence": 1247,
      "timestamp": "2024-04-11T16:00:00Z",
      "changes": {
        "status": {"old": "active", "new": "active"},
        "last_activity_at": {"old": "2024-04-10T09:15:00Z", "new": "2024-04-11T14:00:00Z"}
      }
    },
    {
      "id": "evt_3n8p2k5m9x",
      "event_type": "deal.created",
      "entity_type": "deal",
      "entity_id": "deal_7k2m9n5p8x",
      "sequence": 1245,
      "timestamp": "2024-04-11T15:30:00Z",
      "changes": null
    }
  ]
}
```

**Testing Value:**
- Test event-driven architecture
- Handle out-of-order events
- Deduplicate events
- Build event sourcing
- Implement CDC patterns

---

### 4. Data Lineage and Audit Fields

**Implementation:**
- Add detailed audit fields to all records
- Include data quality scores
- Add validation status
- Track merge history
- Include confidence levels

**Additional Fields:**
```json
{
  "data_quality": {
    "completeness_score": 0.85,
    "accuracy_score": 0.92,
    "consistency_score": 0.78,
    "last_validated_at": "2024-04-12T06:00:00Z",
    "validation_status": "passed_with_warnings",
    "warnings": ["missing_phone", "stale_data"]
  },
  "lineage": {
    "created_by_system": "salesforce",
    "modified_by_system": ["salesforce", "manual_entry"],
    "import_batch_id": "batch_2024041206",
    "source_record_id": "0018x00000AbCdE",
    "source_record_version": 47,
    "merge_history": [
      {
        "merged_from": "cust_old_123",
        "merged_at": "2024-03-15T10:00:00Z",
        "merged_by": "usr_445"
      }
    ]
  },
  "confidence": {
    "email_confidence": 0.95,
    "phone_confidence": 0.60,
    "address_confidence": 0.88,
    "overall_confidence": 0.81
  }
}
```

**Testing Value:**
- Track data provenance
- Build data lineage graphs
- Implement data quality monitoring
- Create audit trails
- Build confidence scoring

---

### 5. Time-Based Data Evolution

**Implementation:**
- Add `/snapshots/:date` endpoint
- Return data as it existed on specific date
- Show record evolution over time
- Include deleted records in historical views
- Simulate slowly changing dimensions

**Example:**
```
GET /snapshots/2024-01-15/customers
GET /snapshots/2024-03-01/customers
GET /snapshots/2024-04-12/customers
```

**Response:**
```json
{
  "snapshot_date": "2024-01-15",
  "data": [
    {
      "id": "cust_8x9k2m4n5p",
      "name": "Acme Corporation",
      "status": "active",
      "created_at": "2023-01-15T10:30:00Z",
      "updated_at": "2024-01-10T14:00:00Z",
      "snapshot_metadata": {
        "valid_from": "2023-01-15T10:30:00Z",
        "valid_to": "2024-03-20T14:22:11Z",
        "is_current": false,
        "version": 1
      }
    }
  ]
}
```

**Testing Value:**
- Test temporal queries
- Implement SCD Type 2
- Build time-travel queries
- Track historical changes
- Test point-in-time recovery

---

## Implementation Checklist

### Phase 1: Basic Setup
- [ ] Create Mockoon environment
- [ ] Configure global headers
- [ ] Set up CORS
- [ ] Add latency simulation

### Phase 2: Core Endpoints
- [ ] Implement GET /customers (list and detail)
- [ ] Implement GET /contacts (list and detail)
- [ ] Implement GET /leads (list and detail)
- [ ] Implement GET /deals (list and detail)
- [ ] Implement GET /activities (list and detail)
- [ ] Implement GET /notes
- [ ] Implement GET /companies (list and detail)

### Phase 3: Supporting Endpoints
- [ ] Implement GET /owners
- [ ] Implement GET /pipeline-stages
- [ ] Implement GET /sync-status
- [ ] Implement GET /metadata
- [ ] Implement GET /search
- [ ] Implement GET /events

### Phase 4: Versioning
- [ ] Add v1 responses for all endpoints
- [ ] Add v2 responses for all endpoints
- [ ] Add v3 responses (default) for all endpoints
- [ ] Test version switching

### Phase 5: Pagination
- [ ] Add pagination support to list endpoints
- [ ] Implement page/limit parameters
- [ ] Add intentional pagination issues
- [ ] Test page boundaries

### Phase 6: Error Handling
- [ ] Add 404 responses
- [ ] Add 429 rate limit responses
- [ ] Add 500 error responses
- [ ] Test error scenarios

### Phase 7: Advanced Features
- [ ] Add webhook events endpoint
- [ ] Add data lineage fields
- [ ] Add time-based snapshots
- [ ] Add partial failure responses
- [ ] Test advanced scenarios

---

## Usage Examples

### Python with requests

```python
import requests

BASE_URL = "http://localhost:3000"

# Get all customers (v3, default)
response = requests.get(f"{BASE_URL}/customers")
customers = response.json()

# Get customers from v1 snapshot
response = requests.get(f"{BASE_URL}/customers?version=v1")
customers_v1 = response.json()

# Get paginated results
response = requests.get(f"{BASE_URL}/customers?page=2&limit=10")
page2 = response.json()

# Get single customer
response = requests.get(f"{BASE_URL}/customers/cust_8x9k2m4n5p")
customer = response.json()

# Search across entities
response = requests.get(f"{BASE_URL}/search?q=acme")
results = response.json()

# Get change events
response = requests.get(f"{BASE_URL}/events")
events = response.json()
```

### cURL

```bash
# Get all customers
curl http://localhost:3000/customers

# Get v1 snapshot
curl "http://localhost:3000/customers?version=v1"

# Get paginated results
curl "http://localhost:3000/customers?page=2&limit=10"

# Get single customer
curl http://localhost:3000/customers/cust_8x9k2m4n5p

# Search
curl "http://localhost:3000/search?q=acme"

# Get events
curl http://localhost:3000/events
```

---

## Summary

This CRM mock API provides:

✅ **Realistic Data Quality Issues**
- 50+ intentional data quality problems
- Believable issues that occur in real systems
- Not artificial chaos

✅ **Complete Entity Model**
- 8 core entities with relationships
- Supporting reference data
- Audit and metadata

✅ **Versioned Snapshots**
- 3 versions showing data evolution
- Realistic changes over time
- Schema drift simulation

✅ **Production-Like Behavior**
- Multiple source systems
- Sync status tracking
- Pagination issues
- Error scenarios

✅ **Free Mockoon Features Only**
- No premium features required
- Easy to implement
- Fully functional

✅ **Comprehensive Testing**
- ETL pipeline testing
- Data quality validation
- Schema evolution
- Temporal queries
- Error handling

This API is ready for immediate use in data engineering projects, providing a realistic testing environment for building robust data pipelines, validation frameworks, and data quality monitoring systems.

