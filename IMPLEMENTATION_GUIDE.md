# CRM Mock API - Implementation Guide

## Quick Start

### 1. Install Mockoon
```bash
npm install -g @mockoon/cli
# Or download desktop app from https://mockoon.com/download/
```

### 2. Create the API

You have two options:

**Option A: Use the provided JSON file** (if you create it)
```bash
mockoon-cli start --data ./mockoon-crm-production-api.json --port 3000
```

**Option B: Build it manually in Mockoon Desktop**
1. Open Mockoon Desktop
2. Create new environment: "CRM Production Mock API"
3. Set port: 3000
4. Follow the endpoint configurations in `PRODUCTION_CRM_API_SPEC.md`
5. Copy/paste the JSON responses from the spec
6. Configure versioning rules
7. Save and start

### 3. Test It
```bash
# Test customers endpoint
curl http://localhost:3000/customers | jq

# Test with versioning
curl "http://localhost:3000/customers?version=v1" | jq

# Test pagination
curl "http://localhost:3000/customers?page=1&limit=5" | jq

# Test single record
curl http://localhost:3000/customers/cust_8x9k2m4n5p | jq
```

---

## File Structure

```
.
├── PRODUCTION_CRM_API_SPEC.md          # Complete API specification
├── IMPLEMENTATION_GUIDE.md             # This file
├── mockoon-crm-production-api.json     # Mockoon configuration (to be created)
├── data_quality_analysis.py            # Python analysis script
├── requirements.txt                    # Python dependencies
└── README.md                           # Project overview
```

---

## Building the Mockoon Configuration

### Step 1: Environment Setup

1. Open Mockoon Desktop
2. Click "New Environment"
3. Name: "CRM Production Mock API"
4. Port: 3000
5. Enable CORS: Yes

### Step 2: Global Headers

Add these headers to the environment:
```
Content-Type: application/json
X-API-Version: {{queryParam 'version' 'v3'}}
X-Request-ID: {{faker 'datatype.uuid'}}
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: {{faker 'datatype.number' min=800 max=1000}}
```

### Step 3: Create Endpoints

For each endpoint in the spec, create a route:

#### Example: GET /customers

1. Click "Add Route"
2. Method: GET
3. Path: `/customers`
4. Documentation: "List all customers with messy data"

5. **Add Response 1 (v3 - default)**
   - Status: 200
   - Label: "v3 (current)"
   - Body: Copy JSON from spec section "GET /customers"
   - Headers: `Content-Type: application/json`
   - Rules: None (default response)

6. **Add Response 2 (v2)**
   - Status: 200
   - Label: "v2 (Sept 2023)"
   - Body: Modified JSON (remove records after Sept 2023)
   - Headers: `Content-Type: application/json`
   - Rules: Add rule → Query param `version` equals `v2`

7. **Add Response 3 (v1)**
   - Status: 200
   - Label: "v1 (Jan 2023)"
   - Body: Modified JSON (remove records after Jan 2023)
   - Headers: `Content-Type: application/json`
   - Rules: Add rule → Query param `version` equals `v1`

8. **Add Response 4 (404)**
   - Status: 404
   - Label: "Not Found"
   - Body: `{"error": "not_found", "message": "Resource not found", "status": 404}`
   - Rules: Add rule → Query param `error` equals `404`

#### Example: GET /customers/:id

1. Click "Add Route"
2. Method: GET
3. Path: `/customers/:id`
4. Documentation: "Get single customer by ID"

5. **Add Response (200)**
   - Status: 200
   - Body: Single customer record from list
   - Use URL param: `{{urlParam 'id'}}`
   - Note: For simplicity, return a fixed record or use multiple responses with rules

### Step 4: Repeat for All Endpoints

Create routes for:
- GET /customers
- GET /customers/:id
- GET /contacts
- GET /contacts/:id
- GET /leads
- GET /leads/:id
- GET /deals
- GET /deals/:id
- GET /activities
- GET /activities/:id
- GET /notes
- GET /companies
- GET /companies/:id
- GET /owners
- GET /pipeline-stages
- GET /sync-status
- GET /metadata
- GET /search
- GET /events

### Step 5: Add Latency

1. Go to Environment Settings
2. Set latency: 50-200ms
3. This simulates realistic API response times

### Step 6: Export Configuration

1. Click "File" → "Export environment"
2. Save as: `mockoon-crm-production-api.json`
3. This file can be shared and imported by others

---

## Versioning Strategy

### Creating Version-Specific Data

**v1 (January 2023):**
- Remove all records with `created_at` after 2023-01-31
- Keep only: cust_8x9k2m4n5p, cust_7h3j9k1m2n, cust_2p9k8m3n1x
- Add more duplicates
- Use older `sync_version` numbers (1-5)
- More null values
- More field name inconsistencies

**v2 (September 2023):**
- Remove all records with `created_at` after 2023-09-30
- Keep: v1 records + cust_5k2m9n4p7x, cust_9m2n5p8k3x
- Some duplicates removed
- Some field names standardized
- Medium `sync_version` numbers (5-20)
- Some records soft-deleted

**v3 (Current):**
- All records
- Latest `sync_version` numbers
- Most complete data
- Still has quality issues

### Implementation in Mockoon

**Option 1: Multiple Responses (Recommended)**
- Create 3 separate responses per endpoint
- Use query param rules: `version` equals `v1`, `v2`, or default

**Option 2: Templating**
- Use Handlebars conditionals in single response
- More complex but more maintainable

```handlebars
{
  "data": [
    {{#if (eq (queryParam 'version') 'v1')}}
      // v1 records only
    {{else if (eq (queryParam 'version') 'v2')}}
      // v2 records only
    {{else}}
      // v3 records (default)
    {{/if}}
  ]
}
```

---

## Pagination Strategy

### Simple Approach (Recommended for MVP)

Create separate responses for each page:

**Page 1:**
- Rule: `page` equals `1` OR `page` is not present
- Return first 20 records
- Include: `"has_more": true, "next_page": 2`

**Page 2:**
- Rule: `page` equals `2`
- Return next 20 records (with 1-2 duplicates from page 1)
- Include: `"has_more": false`

### Advanced Approach

Use Mockoon's data buckets (if available) or templating to calculate pagination dynamically.

---

## Testing the API

### Manual Testing

```bash
# Test all endpoints
curl http://localhost:3000/customers
curl http://localhost:3000/contacts
curl http://localhost:3000/leads
curl http://localhost:3000/deals
curl http://localhost:3000/activities
curl http://localhost:3000/notes
curl http://localhost:3000/companies
curl http://localhost:3000/owners
curl http://localhost:3000/pipeline-stages
curl http://localhost:3000/sync-status
curl http://localhost:3000/metadata
curl http://localhost:3000/search?q=acme
curl http://localhost:3000/events

# Test versioning
curl "http://localhost:3000/customers?version=v1"
curl "http://localhost:3000/customers?version=v2"
curl "http://localhost:3000/customers?version=v3"

# Test pagination
curl "http://localhost:3000/customers?page=1&limit=5"
curl "http://localhost:3000/customers?page=2&limit=5"

# Test single records
curl http://localhost:3000/customers/cust_8x9k2m4n5p
curl http://localhost:3000/contacts/cont_8k2m9n5p3x
curl http://localhost:3000/deals/deal_7k2m9n5p8x
```

### Automated Testing

Create a test script:

```python
import requests

BASE_URL = "http://localhost:3000"

def test_endpoints():
    endpoints = [
        "/customers",
        "/contacts",
        "/leads",
        "/deals",
        "/activities",
        "/notes",
        "/companies",
        "/owners",
        "/pipeline-stages",
        "/sync-status",
        "/metadata",
        "/events"
    ]
    
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        assert response.status_code == 200, f"{endpoint} failed"
        print(f"✓ {endpoint}")

def test_versioning():
    for version in ["v1", "v2", "v3"]:
        response = requests.get(f"{BASE_URL}/customers?version={version}")
        assert response.status_code == 200
        print(f"✓ Version {version}")

def test_pagination():
    response = requests.get(f"{BASE_URL}/customers?page=1&limit=5")
    assert response.status_code == 200
    data = response.json()
    assert len(data['data']) <= 5
    print(f"✓ Pagination")

if __name__ == "__main__":
    test_endpoints()
    test_versioning()
    test_pagination()
    print("\nAll tests passed! ✓")
```

---

## Data Quality Analysis

Run the provided analysis script:

```bash
pip install -r requirements.txt
python data_quality_analysis.py
```

This will show you all the intentional data quality issues in the API.

---

## Common Issues and Solutions

### Issue: Port 3000 already in use
```bash
# Use a different port
mockoon-cli start --data ./mockoon-crm-production-api.json --port 3001
```

### Issue: CORS errors
- Enable CORS in Mockoon environment settings
- Add `Access-Control-Allow-Origin: *` header

### Issue: Versioning not working
- Check query param rules are set correctly
- Ensure `version` parameter is spelled correctly
- Check rule operator is "equals" not "contains"

### Issue: Pagination not working
- Verify query param rules for `page`
- Check response bodies have correct page numbers
- Ensure `has_more` field is accurate

### Issue: JSON syntax errors
- Validate JSON in each response body
- Check for trailing commas
- Ensure proper quote escaping

---

## Next Steps

### Phase 1: Basic Implementation
1. Create all core endpoints (/customers, /contacts, /leads, /deals)
2. Add sample data from spec
3. Test basic functionality

### Phase 2: Versioning
1. Add v1, v2, v3 responses
2. Configure query param rules
3. Test version switching

### Phase 3: Advanced Features
1. Add pagination
2. Add error responses
3. Add supporting endpoints

### Phase 4: Realism Enhancements
1. Add webhook events
2. Add data lineage fields
3. Add time-based snapshots
4. Add partial failures
5. Add rate limiting

---

## Resources

- **Mockoon Documentation**: https://mockoon.com/docs/latest/about/
- **Mockoon Templating**: https://mockoon.com/docs/latest/templating/overview/
- **Faker.js**: https://fakerjs.dev/api/
- **Handlebars**: https://handlebarsjs.com/guide/

---

## Support

For issues or questions:
1. Check the `PRODUCTION_CRM_API_SPEC.md` for detailed specifications
2. Review Mockoon documentation
3. Test with cURL or Postman
4. Validate JSON syntax

---

## License

Free to use for educational and testing purposes.

