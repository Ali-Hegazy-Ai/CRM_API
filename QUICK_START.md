# Quick Start Guide

## Get Running in 3 Steps

### Step 1: Install Mockoon
```bash
# Using npm
npm install -g @mockoon/cli

# Or download desktop app from https://mockoon.com/download/
```

### Step 2: Start the API
```bash
# Using CLI
mockoon-cli start --data ./mockoon-crm-api.json --port 3000

# Or open mockoon-crm-api.json in Mockoon Desktop and click Start
```

### Step 3: Test It
```bash
# Test customers endpoint
curl http://localhost:3000/api/v1/customers | jq

# Test contacts endpoint
curl http://localhost:3000/api/v1/contacts | jq

# Test all endpoints
curl http://localhost:3000/api/v1/leads | jq
curl http://localhost:3000/api/v1/deals | jq
curl http://localhost:3000/api/v1/activities | jq
curl http://localhost:3000/api/v1/notes | jq
curl http://localhost:3000/api/v1/companies | jq
```

## What You'll Find

This API simulates a real CRM system with **intentional data quality issues**:

✅ **Realistic Problems**
- Duplicate records
- Missing fields
- Inconsistent formatting
- Invalid data
- Mixed data types
- Null values
- Soft deletes

✅ **Real-World Scenarios**
- Multiple source systems (Salesforce, HubSpot, Pipedrive)
- Sync status tracking
- Timestamp variations
- Entity relationships
- Lifecycle states

✅ **Perfect for Testing**
- ETL pipelines
- Data validation
- Data quality checks
- Schema design
- Deduplication logic
- Data modeling

## Next Steps

1. Read `CRM_API_DOCUMENTATION.md` for full details
2. Run `data_quality_analysis.py` to see issues
3. Build your ETL pipeline
4. Test your data quality rules
5. Create your data models

## Common Issues & Solutions

### Issue: Port 3000 already in use
```bash
# Use a different port
mockoon-cli start --data ./mockoon-crm-api.json --port 3001
```

### Issue: Mockoon CLI not found
```bash
# Install globally
npm install -g @mockoon/cli

# Or use npx
npx @mockoon/cli start --data ./mockoon-crm-api.json --port 3000
```

### Issue: Can't parse JSON
```bash
# Install jq for pretty printing
# Mac: brew install jq
# Ubuntu: sudo apt-get install jq
# Windows: choco install jq
```

## Example: Quick Data Quality Check

```python
import requests
import pandas as pd

# Fetch customers
response = requests.get('http://localhost:3000/api/v1/customers')
customers = pd.DataFrame(response.json()['data'])

# Check for issues
print("Duplicate IDs:", customers['id'].duplicated().sum())
print("Missing emails:", customers['email'].isna().sum())
print("Status variations:", customers['status'].unique())
print("Date format issues:", customers['created_at'].apply(type).value_counts())
```

Happy data engineering! 🚀
