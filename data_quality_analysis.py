"""
Data Quality Analysis Script for CRM Mock API
Demonstrates common data quality issues and how to detect them
"""

import requests
import pandas as pd
from collections import Counter
import re
from datetime import datetime

# API Base URL
BASE_URL = "http://localhost:3000/api/v1"

def fetch_endpoint(endpoint):
    """Fetch data from API endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/{endpoint}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {endpoint}: {e}")
        return None

def analyze_customers():
    """Analyze customer data quality"""
    print("\n" + "="*60)
    print("CUSTOMERS DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("customers")
    if not data:
        return
    
    df = pd.DataFrame(data['data'])
    
    # Duplicate IDs
    duplicates = df[df.duplicated(subset=['id'], keep=False)]
    print(f"\n1. Duplicate IDs: {len(duplicates)} records")
    if not duplicates.empty:
        print(f"   Duplicate IDs: {duplicates['id'].unique().tolist()}")
    
    # Missing values
    print(f"\n2. Missing Values:")
    for col in df.columns:
        null_count = df[col].isna().sum()
        empty_count = (df[col] == "").sum() if df[col].dtype == 'object' else 0
        if null_count > 0 or empty_count > 0:
            print(f"   - {col}: {null_count} nulls, {empty_count} empty strings")
    
    # Status inconsistency
    if 'status' in df.columns or 'Status' in df.columns:
        status_col = 'status' if 'status' in df.columns else 'Status'
        statuses = df[status_col].dropna().unique()
        print(f"\n3. Status Value Variations: {statuses.tolist()}")
        print(f"   Issue: Inconsistent casing")
    
    # Date format inconsistency
    print(f"\n4. Date Format Issues:")
    date_formats = []
    for date_str in df['created_at'].dropna():
        if 'T' in str(date_str) and 'Z' in str(date_str):
            date_formats.append('ISO 8601')
        elif ' ' in str(date_str):
            date_formats.append('SQL datetime')
        else:
            date_formats.append('Unknown')
    format_counts = Counter(date_formats)
    print(f"   Formats found: {dict(format_counts)}")
    
    # Invalid emails
    print(f"\n5. Invalid Emails:")
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    invalid_emails = []
    for idx, email in df['email'].dropna().items():
        if not re.match(email_pattern, str(email)):
            invalid_emails.append(email)
    print(f"   Found {len(invalid_emails)} invalid: {invalid_emails}")
    
    # Phone format variations
    print(f"\n6. Phone Format Variations:")
    phone_formats = df['phone'].dropna().apply(lambda x: 
        'Plus format' if str(x).startswith('+') else
        'Dot format' if '.' in str(x) else
        'Parentheses' if '(' in str(x) else
        'Plain'
    ).value_counts()
    print(f"   {phone_formats.to_dict()}")
    
    # Soft deletes
    if 'deleted_at' in df.columns:
        deleted = df['deleted_at'].notna().sum()
        print(f"\n7. Soft-Deleted Records: {deleted}")

def analyze_contacts():
    """Analyze contact data quality"""
    print("\n" + "="*60)
    print("CONTACTS DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("contacts")
    if not data:
        return
    
    df = pd.DataFrame(data['contacts'])
    
    # Field name inconsistencies
    print(f"\n1. Field Name Inconsistencies:")
    if 'first_name' in df.columns and 'firstName' in df.columns:
        print(f"   - Both 'first_name' and 'firstName' exist")
    if 'last_name' in df.columns and 'lastName' in df.columns:
        print(f"   - Both 'last_name' and 'lastName' exist")
    
    # Duplicate contacts
    email_dupes = df[df.duplicated(subset=['email'], keep=False)]
    print(f"\n2. Duplicate Emails: {len(email_dupes)} records")
    
    id_dupes = df[df.duplicated(subset=['contact_id'], keep=False)]
    print(f"   Duplicate Contact IDs: {len(id_dupes)} records")
    if not id_dupes.empty:
        print(f"   IDs: {id_dupes['contact_id'].unique().tolist()}")
    
    # Email casing issues
    print(f"\n3. Email Casing Issues:")
    emails = df['email'].dropna()
    uppercase = emails[emails.str.isupper()].count()
    lowercase = emails[emails.str.islower()].count()
    mixed = len(emails) - uppercase - lowercase
    print(f"   Uppercase: {uppercase}, Lowercase: {lowercase}, Mixed: {mixed}")
    
    # Missing last names
    if 'last_name' in df.columns:
        missing_last = (df['last_name'] == "").sum() + df['last_name'].isna().sum()
        print(f"\n4. Missing Last Names: {missing_last} records")

def analyze_leads():
    """Analyze lead data quality"""
    print("\n" + "="*60)
    print("LEADS DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("leads")
    if not data:
        return
    
    df = pd.DataFrame(data['results'])
    
    # Field name variations
    print(f"\n1. Field Name Variations:")
    score_fields = [col for col in df.columns if 'score' in col.lower()]
    status_fields = [col for col in df.columns if 'status' in col.lower()]
    print(f"   Score fields: {score_fields}")
    print(f"   Status fields: {status_fields}")
    
    # Lead score completeness
    score_col = 'lead_score' if 'lead_score' in df.columns else 'score'
    if score_col in df.columns:
        missing_scores = df[score_col].isna().sum()
        print(f"\n2. Missing Lead Scores: {missing_scores} out of {len(df)}")
    
    # Status variations
    status_col = [col for col in df.columns if 'status' in col.lower()][0]
    statuses = df[status_col].dropna().unique()
    print(f"\n3. Lead Status Variations: {statuses.tolist()}")
    
    # Company name variations (potential duplicates)
    print(f"\n4. Potential Duplicate Companies:")
    companies = df['company_name'].str.lower().str.strip()
    for company in companies.unique():
        similar = df[companies.str.contains(company.split()[0], case=False, na=False)]
        if len(similar) > 1:
            print(f"   - {similar['company_name'].tolist()}")

def analyze_deals():
    """Analyze deal data quality"""
    print("\n" + "="*60)
    print("DEALS DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("deals")
    if not data:
        return
    
    df = pd.DataFrame(data['data'])
    
    # Contact representation inconsistency
    print(f"\n1. Contact Representation:")
    has_nested = df['contact'].notna().sum() if 'contact' in df.columns else 0
    has_flat = df['contact_id'].notna().sum() if 'contact_id' in df.columns else 0
    print(f"   Nested contact objects: {has_nested}")
    print(f"   Flat contact_id fields: {has_flat}")
    print(f"   Issue: Inconsistent structure")
    
    # Currency variations
    currencies = df['currency'].unique()
    print(f"\n2. Currency Variations: {currencies.tolist()}")
    print(f"   Issue: Inconsistent casing")
    
    # Amount data types
    print(f"\n3. Amount Field Analysis:")
    amounts = df['amount'].dropna()
    has_decimals = amounts.apply(lambda x: isinstance(x, float) and x % 1 != 0).sum()
    print(f"   Values with decimals: {has_decimals}")
    print(f"   Integer values: {len(amounts) - has_decimals}")
    
    # Stage variations
    stage_col = 'stage' if 'stage' in df.columns else 'Stage'
    stages = df[stage_col].dropna().unique()
    print(f"\n4. Deal Stage Variations: {stages.tolist()}")
    print(f"   Issue: Inconsistent casing and naming")

def analyze_activities():
    """Analyze activity data quality"""
    print("\n" + "="*60)
    print("ACTIVITIES DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("activities")
    if not data:
        return
    
    df = pd.DataFrame(data['activities'])
    
    # Activity type variations
    types = df['type'].unique()
    print(f"\n1. Activity Type Variations: {types.tolist()}")
    print(f"   Issue: Inconsistent casing")
    
    # Missing descriptions
    missing_desc = df['description'].isna().sum()
    print(f"\n2. Missing Descriptions: {missing_desc} out of {len(df)}")
    
    # Date field variations
    date_fields = [col for col in df.columns if 'date' in col.lower()]
    print(f"\n3. Date Fields Present: {date_fields}")
    print(f"   Issue: Inconsistent field names (activity_date vs due_date)")
    
    # Source system variations
    sources = df['source'].unique()
    print(f"\n4. Source Systems: {sources.tolist()}")

def analyze_notes():
    """Analyze note data quality"""
    print("\n" + "="*60)
    print("NOTES DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("notes")
    if not data:
        return
    
    df = pd.DataFrame(data['data'])
    
    # Missing titles
    missing_titles = df['title'].isna().sum() if 'title' in df.columns else 0
    print(f"\n1. Missing Titles: {missing_titles} out of {len(df)}")
    
    # Empty content
    empty_content = (df['content'] == "").sum()
    print(f"\n2. Empty Content: {empty_content} out of {len(df)}")
    
    # Tags completeness
    if 'tags' in df.columns:
        missing_tags = df['tags'].isna().sum()
        print(f"\n3. Missing Tags: {missing_tags} out of {len(df)}")

def analyze_companies():
    """Analyze company data quality"""
    print("\n" + "="*60)
    print("COMPANIES DATA QUALITY ANALYSIS")
    print("="*60)
    
    data = fetch_endpoint("companies")
    if not data:
        return
    
    df = pd.DataFrame(data['companies'])
    
    # Duplicate company IDs
    duplicates = df[df.duplicated(subset=['company_id'], keep=False)]
    print(f"\n1. Duplicate Company IDs: {len(duplicates)} records")
    
    # Employee count data type variations
    print(f"\n2. Employee Count Data Types:")
    emp_types = df['employee_count'].apply(type).value_counts()
    print(f"   {emp_types.to_dict()}")
    print(f"   Issue: Mixed integers and string ranges")
    
    # Address structure variations
    print(f"\n3. Address Structure:")
    has_nested = df['address'].notna().sum() if 'address' in df.columns else 0
    has_flat = df['street'].notna().sum() if 'street' in df.columns else 0
    print(f"   Nested address objects: {has_nested}")
    print(f"   Flat address fields: {has_flat}")
    print(f"   Issue: Inconsistent structure")
    
    # Website format variations
    print(f"\n4. Website Format Variations:")
    websites = df['website'].dropna()
    with_https = websites.str.startswith('https://').sum()
    with_www = websites.str.contains('www.').sum()
    print(f"   With https://: {with_https}")
    print(f"   With www.: {with_www}")
    print(f"   Without protocol: {len(websites) - with_https}")

def generate_summary():
    """Generate overall data quality summary"""
    print("\n" + "="*60)
    print("OVERALL DATA QUALITY SUMMARY")
    print("="*60)
    
    print("""
Key Issues Found:
1. ✗ Duplicate records across multiple endpoints
2. ✗ Inconsistent field naming (snake_case vs camelCase)
3. ✗ Inconsistent value casing (status, type, currency)
4. ✗ Mixed date formats (ISO 8601 vs SQL datetime)
5. ✗ Invalid data (incomplete emails, empty strings)
6. ✗ Null values in critical fields
7. ✗ Mixed data types (integers vs strings)
8. ✗ Inconsistent data structures (nested vs flat)
9. ✗ Missing required fields
10. ✗ Soft-deleted records mixed with active data

Recommended Actions:
→ Implement deduplication logic
→ Standardize field names and casing
→ Validate and clean email/phone formats
→ Normalize date formats to ISO 8601
→ Handle null vs empty string consistently
→ Type conversion and validation
→ Separate active from deleted records
→ Create data quality rules and monitoring
→ Build master data management process
→ Implement schema validation

This API is perfect for testing your data engineering pipeline! 🚀
    """)

if __name__ == "__main__":
    print("\n" + "="*60)
    print("CRM MOCK API - DATA QUALITY ANALYSIS")
    print("="*60)
    print("\nMake sure the Mockoon API is running on http://localhost:3000")
    print("Run: mockoon-cli start --data ./mockoon-crm-api.json --port 3000")
    
    try:
        # Run all analyses
        analyze_customers()
        analyze_contacts()
        analyze_leads()
        analyze_deals()
        analyze_activities()
        analyze_notes()
        analyze_companies()
        generate_summary()
        
    except Exception as e:
        print(f"\nError: {e}")
        print("\nMake sure:")
        print("1. Mockoon is running on port 3000")
        print("2. Required packages are installed: pip install requests pandas")
