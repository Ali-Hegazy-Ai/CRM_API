# Production CRM Mock API - Complete Data Engineering Testing Suite

A comprehensive, production-realistic CRM API with intentional data quality issues for testing data pipelines, ETL processes, and data quality frameworks.

## 🎯 What Makes This Different

This is **not** a clean demo API. This is a realistic simulation of production CRM data with 3+ years of operational history, multiple system migrations, and all the data quality problems that break real ETL pipelines.

**Key Features:**
- ✅ 50+ intentional data quality issues (believable, not random)
- ✅ 13 endpoints with full CRUD operations
- ✅ 3 versioned snapshots showing data evolution (v1, v2, v3)
- ✅ Multiple source systems (Salesforce, HubSpot, Zoho, Pipedrive)
- ✅ Realistic entity relationships and lifecycle transitions
- ✅ Pagination issues, sync failures, and temporal inconsistencies
- ✅ 100% free Mockoon features (no premium required)

## 📊 API Overview

### Core Entities (8)
- **Customers** - Converted accounts with full history
- **Contacts** - People at companies
- **Leads** - Unqualified prospects
- **Deals** - Sales opportunities with pipeline stages
- **Activities** - Calls, emails, meetings, tasks
- **Notes** - Free-form annotations
- **Companies** - Organization master data
- **Owners** - Sales reps and account managers

### Supporting Endpoints (5)
- **Pipeline Stages** - Deal progression definitions
- **Sync Status** - Health monitoring by source system
- **Metadata** - API schema and field definitions
- **Search** - Cross-entity search
- **Events** - Change event log / audit trail

### Total: 13 Endpoints, 100+ Sample Records

## 🚀 Quick Start

### 1. Install Mockoon
```bash
npm install -g @mockoon/cli
# Or download desktop: https://mockoon.com/download/
```

### 2. Build the API
Follow the detailed guide in `IMPLEMENTATION_GUIDE.md` to:
- Create the Mockoon environment
- Configure all 13 endpoints
- Set up versioning (v1, v2, v3)
- Add pagination and error responses

**Estimated setup time:** 2-3 hours for complete implementation

### 3. Start the API
```bash
mockoon-cli start --data ./mockoon-crm-production-api.json --port 3000
```

### 4. Test It
```bash
# Test core endpoints
curl http://localhost:3000/customers | jq
curl http://localhost:3000/contacts | jq
curl http://localhost:3000/deals | jq

# Test versioning
curl "http://localhost:3000/customers?version=v1" | jq
curl "http://localhost:3000/customers?version=v2" | jq
curl "http://localhost:3000/customers?version=v3" | jq

# Test pagination
curl "http://localhost:3000/customers?page=1&limit=5" | jq
curl "http://localhost:3000/customers?page=2&limit=5" | jq

# Test single records
curl http://localhost:3000/customers/cust_8x9k2m4n5p | jq

# Test search
curl "http://localhost:3000/search?q=acme" | jq

# Test events
curl http://localhost:3000/events | jq
```

## 📁 Documentation Files

| File | Purpose | Size |
|------|---------|------|
| **PRODUCTION_CRM_API_SPEC.md** | Complete API specification with all endpoints, sample data, and data quality issues | 25KB |
| **IMPLEMENTATION_GUIDE.md** | Step-by-step guide to build the API in Mockoon | 8KB |
| **data_quality_analysis.py** | Python script to analyze and report all data quality issues | 5KB |
| **requirements.txt** | Python dependencies | 1KB |
| **README.md** | This file | 4KB |

## 🔍 Data Quality Issues (50+)

### By Category

| Category | Count | Examples |
|----------|-------|----------|
| **Duplicate Records** | 8 | Same ID appearing multiple times, similar entities |
| **Missing/Null Values** | 35+ | Required fields null, inconsistent null vs empty |
| **Inconsistent Formatting** | 40+ | Date formats, phone formats, email casing |
| **Field Name Variations** | 15+ | snake_case vs camelCase, different names |
| **Invalid Data** | 10+ | Incomplete emails, invalid phones, malformed URLs |
| **Type Inconsistencies** | 8+ | String vs number, string ranges vs integers |
| **Structural Issues** | 12+ | Nested vs flat, different wrappers |
| **Relationship Issues** | 6+ | Orphaned records, stale relationships |
| **Temporal Issues** | 10+ | Conflicting timestamps, stale data |
| **Source System Artifacts** | 15+ | Different schemas, sync failures |

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

## 🎓 What You'll Learn

### ETL Pipeline Testing
- ✅ Deduplication logic
- ✅ Data normalization
- ✅ Validation rules
- ✅ Type conversion
- ✅ Schema evolution handling

### Data Quality Frameworks
- ✅ Completeness checks
- ✅ Consistency validation
- ✅ Accuracy verification
- ✅ Uniqueness detection
- ✅ Timeliness monitoring

### Data Modeling
- ✅ Dimensional modeling
- ✅ Entity resolution
- ✅ Relationship mapping
- ✅ Slowly changing dimensions
- ✅ Temporal queries

## 💡 Example Use Cases

### 1. ETL Pipeline Testing
```python
import requests
import pandas as pd

# Extract from multiple endpoints
customers = requests.get('http://localhost:3000/customers').json()['data']
contacts = requests.get('http://localhost:3000/contacts').json()['contacts']
deals = requests.get('http://localhost:3000/deals').json()['data']

# Transform - handle duplicates
df_customers = pd.DataFrame(customers)
df_customers = df_customers.drop_duplicates(subset=['id'], keep='last')

# Transform - normalize dates
df_customers['created_at'] = pd.to_datetime(df_customers['created_at'], errors='coerce')

# Transform - standardize casing
df_customers['status'] = df_customers['status'].str.lower()

# Load to data warehouse
# df_customers.to_sql('customers', engine, if_exists='replace')
```

### 2. Data Quality Monitoring
```python
def check_data_quality(df):
    issues = []
    
    # Check duplicates
    dupes = df[df.duplicated(subset=['id'], keep=False)]
    if len(dupes) > 0:
        issues.append(f"Found {len(dupes)} duplicate IDs")
    
    # Check missing emails
    missing = df['email'].isna().sum()
    if missing > 0:
        issues.append(f"Found {missing} missing emails")
    
    # Check invalid emails
    invalid = df[~df['email'].str.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', na=False)]
    if len(invalid) > 0:
        issues.append(f"Found {len(invalid)} invalid emails")
    
    return issues

# Run quality checks
issues = check_data_quality(df_customers)
for issue in issues:
    print(f"⚠️  {issue}")
```

### 3. Schema Evolution Tracking
```python
# Compare v1 vs v3 to see schema changes
v1_customers = requests.get('http://localhost:3000/customers?version=v1').json()['data']
v3_customers = requests.get('http://localhost:3000/customers?version=v3').json()['data']

# Detect new fields
v1_fields = set(v1_customers[0].keys())
v3_fields = set(v3_customers[0].keys())
new_fields = v3_fields - v1_fields
print(f"New fields in v3: {new_fields}")

# Detect removed records
v1_ids = {c['id'] for c in v1_customers}
v3_ids = {c['id'] for c in v3_customers}
removed = v1_ids - v3_ids
print(f"Removed records: {removed}")
```

## 🔧 5 Advanced Realism Improvements

### 1. Rate Limiting and Throttling
Add 429 responses with `Retry-After` headers to test retry logic and exponential backoff.

### 2. Partial Failures
Simulate 500 errors for specific record IDs and partial data returns (207 Multi-Status).

### 3. Webhook Events
Add change data capture with out-of-order events and duplicate deliveries.

### 4. Data Lineage
Include audit fields, data quality scores, merge history, and confidence levels.

### 5. Time-Based Snapshots
Add `/snapshots/:date` endpoint to query historical data and implement SCD Type 2.

**See `PRODUCTION_CRM_API_SPEC.md` for detailed implementation guides.**

## 📚 Complete Documentation

### For API Users
- **PRODUCTION_CRM_API_SPEC.md** - Complete endpoint documentation, sample responses, data quality issues

### For Implementers
- **IMPLEMENTATION_GUIDE.md** - Step-by-step Mockoon setup, versioning strategy, pagination implementation

### For Data Engineers
- **data_quality_analysis.py** - Automated analysis script to detect all issues
- **requirements.txt** - Python dependencies (requests, pandas)

## 🐍 Run Data Quality Analysis

```bash
# Install dependencies
pip install -r requirements.txt

# Start the API
mockoon-cli start --data ./mockoon-crm-production-api.json --port 3000

# Run analysis
python data_quality_analysis.py
```

**Output:**
- Duplicate record detection
- Missing value analysis
- Format inconsistency detection
- Invalid data identification
- Field name variation tracking
- Comprehensive quality report

## 🎯 Project Ideas

1. **ETL Pipeline** - Build a complete extract-transform-load pipeline
2. **Data Quality Dashboard** - Create metrics and monitoring
3. **Master Data Management** - Implement golden record creation
4. **Change Data Capture** - Track and process change events
5. **Data Lineage Tracker** - Map data flow from source to destination
6. **Validation Framework** - Build a rules engine for quality checks
7. **Schema Registry** - Track schema evolution over time
8. **Entity Resolution** - Match and merge duplicate records
9. **Data Profiling Tool** - Analyze patterns and distributions
10. **API Monitoring** - Track response times and error rates

## 🤝 Contributing

This is a comprehensive learning resource. Contributions welcome:
- Additional endpoints
- More data quality scenarios
- Analysis scripts in other languages
- ETL pipeline examples
- Data quality framework implementations

## 📝 License

Free to use for educational and testing purposes.

## 🙏 Acknowledgments

Built for data engineers who need production-realistic, messy data to test their pipelines, validation frameworks, and data quality systems.

**This is not a toy dataset. This is a realistic simulation of enterprise CRM data with all its problems.**

---

## 🚀 Get Started Now

1. Read `PRODUCTION_CRM_API_SPEC.md` for complete API details
2. Follow `IMPLEMENTATION_GUIDE.md` to build the API
3. Run `data_quality_analysis.py` to see all issues
4. Build your ETL pipeline and data quality framework
5. Test against realistic production scenarios

**Happy Data Engineering!** 🎉
