"""
Production CRM API - Comprehensive Data Quality Analysis
Detects and reports all intentional data quality issues in the mock API
"""

import requests
import pandas as pd
from collections import Counter, defaultdict
import re
from datetime import datetime
import json

# API Base URL
BASE_URL = "http://localhost:3000"

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*70}{Colors.END}\n")

def print_section(text):
    """Print formatted section"""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}")
    print(f"{Colors.CYAN}{'-'*len(text)}{Colors.END}")

def print_issue(text, count=None):
    """Print formatted issue"""
    if count is not None:
        print(f"{Colors.YELLOW}⚠️  {text}: {Colors.RED}{count}{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_success(text):
    """Print formatted success"""
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def fetch_endpoint(endpoint, version='v3'):
    """Fetch data from API endpoint"""
    try:
        url = f"{BASE_URL}/{endpoint}"
        if version != 'v3':
            url += f"?version={version}"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print_issue(f"Error fetching {endpoint}: {e}")
        return None

def analyze_duplicates(df, id_field='id', name='records'):
    """Analyze duplicate IDs"""
    duplicates = df[df.duplicated(subset=[id_field], keep=False)]
    if not duplicates.empty:
        dup_ids = duplicates[id_field].value_counts()
        print_issue(f"Duplicate {name}", len(duplicates))
        for dup_id, count in dup_ids.items():
            print(f"   - {dup_id}: appears {count} times")
        return len(duplicates)
    return 0

def analyze_missing_values(df, name='records'):
    """Analyze missing and null values"""
    print_section(f"Missing Values in {name}")
    total_issues = 0
    for col in df.columns:
        null_count = df[col].isna().sum()
        empty_count = (df[col] == "").sum() if df[col].dtype == 'object' else 0
        if null_count > 0 or empty_count > 0:
            print_issue(f"{col}", f"{null_count} nulls, {empty_count} empty strings")
            total_issues += null_count + empty_count
    return total_issues

def analyze_field_name_variations(df, name='records'):
    """Detect field name inconsistencies"""
    print_section(f"Field Name Variations in {name}")
    variations = []
    
    # Common variations to check
    patterns = [
        ('first_name', 'firstName'),
        ('last_name', 'lastName'),
        ('email', 'email_address'),
        ('phone', 'phone_number'),
        ('created_at', 'created_date'),
        ('updated_at', 'updated_date'),
        ('status', 'Status'),
        ('industry', 'Industry'),
        ('stage', 'Stage'),
        ('title', 'Title'),
    ]
    
    for pattern1, pattern2 in patterns:
        if pattern1 in df.columns and pattern2 in df.columns:
            print_issue(f"Both '{pattern1}' and '{pattern2}' exist")
            variations.append((pattern1, pattern2))
    
    return len(variations)

def analyze_value_casing(df, field, name='values'):
    """Analyze inconsistent casing in values"""
    if field not in df.columns:
        return 0
    
    values = df[field].dropna().unique()
    if len(values) == 0:
        return 0
    
    # Group by lowercase version
    casing_groups = defaultdict(list)
    for val in values:
        casing_groups[str(val).lower()].append(str(val))
    
    # Find groups with multiple casings
    issues = {k: v for k, v in casing_groups.items() if len(v) > 1}
    
    if issues:
        print_section(f"Casing Inconsistencies in {field}")
        for base, variations in issues.items():
            print_issue(f"'{base}' appears as: {variations}")
        return len(issues)
    return 0

def analyze_date_formats(df, date_fields, name='records'):
    """Analyze date format inconsistencies"""
    print_section(f"Date Format Issues in {name}")
    total_issues = 0
    
    for field in date_fields:
        if field not in df.columns:
            continue
        
        formats = defaultdict(int)
        for date_str in df[field].dropna():
            date_str = str(date_str)
            if 'T' in date_str and 'Z' in date_str:
                formats['ISO 8601'] += 1
            elif ' ' in date_str and ':' in date_str:
                formats['SQL datetime'] += 1
            elif '/' in date_str:
                formats['Slash format'] += 1
            elif re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
                formats['Date only'] += 1
            else:
                formats['Unknown'] += 1
        
        if len(formats) > 1:
            print_issue(f"{field} has {len(formats)} different formats")
            for fmt, count in formats.items():
                print(f"   - {fmt}: {count} records")
            total_issues += len(formats) - 1
    
    return total_issues

def analyze_invalid_emails(df, email_field='email', name='records'):
    """Detect invalid email addresses"""
    if email_field not in df.columns:
        return 0
    
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    invalid_emails = []
    
    for idx, email in df[email_field].dropna().items():
        if not re.match(email_pattern, str(email)):
            invalid_emails.append(email)
    
    if invalid_emails:
        print_section(f"Invalid Emails in {name}")
        print_issue(f"Found {len(invalid_emails)} invalid emails")
        for email in invalid_emails[:5]:  # Show first 5
            print(f"   - {email}")
        if len(invalid_emails) > 5:
            print(f"   ... and {len(invalid_emails) - 5} more")
        return len(invalid_emails)
    return 0

def analyze_phone_formats(df, phone_field='phone', name='records'):
    """Analyze phone format variations"""
    if phone_field not in df.columns:
        return 0
    
    formats = defaultdict(int)
    for phone in df[phone_field].dropna():
        phone_str = str(phone)
        if phone_str == '':
            formats['Empty string'] += 1
        elif phone_str.startswith('+'):
            formats['Plus format'] += 1
        elif '.' in phone_str:
            formats['Dot format'] += 1
        elif '(' in phone_str:
            formats['Parentheses'] += 1
        elif '-' in phone_str:
            formats['Dash format'] += 1
        else:
            formats['Plain'] += 1
    
    if len(formats) > 1:
        print_section(f"Phone Format Variations in {name}")
        for fmt, count in formats.items():
            print(f"   - {fmt}: {count} records")
        return len(formats) - 1
    return 0

def analyze_country_variations(df, country_field='country', name='records'):
    """Analyze country name/code variations"""
    if country_field not in df.columns:
        return 0
    
    countries = df[country_field].dropna().unique()
    
    # Group similar countries
    usa_variations = [c for c in countries if 'us' in str(c).lower()]
    egypt_variations = [c for c in countries if 'eg' in str(c).lower() or 'egypt' in str(c).lower()]
    
    issues = 0
    if len(usa_variations) > 1:
        print_section(f"Country Variations in {name}")
        print_issue(f"USA appears as: {usa_variations}")
        issues += len(usa_variations) - 1
    
    if len(egypt_variations) > 1:
        if issues == 0:
            print_section(f"Country Variations in {name}")
        print_issue(f"Egypt appears as: {egypt_variations}")
        issues += len(egypt_variations) - 1
    
    return issues

def analyze_type_inconsistencies(df, field, name='records'):
    """Detect mixed data types in a field"""
    if field not in df.columns:
        return 0
    
    types = df[field].dropna().apply(type).value_counts()
    if len(types) > 1:
        print_section(f"Type Inconsistencies in {name}")
        print_issue(f"{field} has {len(types)} different types")
        for dtype, count in types.items():
            print(f"   - {dtype.__name__}: {count} records")
        return len(types) - 1
    return 0

def analyze_customers():
    """Comprehensive analysis of customers endpoint"""
    print_header("CUSTOMERS DATA QUALITY ANALYSIS")
    
    data = fetch_endpoint("customers")
    if not data or 'data' not in data:
        print_issue("Failed to fetch customers data")
        return
    
    df = pd.DataFrame(data['data'])
    print(f"Total records: {len(df)}")
    
    issues = 0
    
    # Duplicates
    print_section("Duplicate Records")
    issues += analyze_duplicates(df, 'id', 'customer IDs')
    
    # Missing values
    issues += analyze_missing_values(df, 'customers')
    
    # Field name variations
    issues += analyze_field_name_variations(df, 'customers')
    
    # Value casing
    issues += analyze_value_casing(df, 'status', 'status values')
    issues += analyze_value_casing(df, 'assigned_team', 'team values')
    
    # Date formats
    issues += analyze_date_formats(df, ['created_at', 'updated_at', 'last_activity_at'], 'customers')
    
    # Invalid emails
    issues += analyze_invalid_emails(df, 'email', 'customers')
    
    # Phone formats
    issues += analyze_phone_formats(df, 'phone', 'customers')
    
    # Country variations
    issues += analyze_country_variations(df, 'country', 'customers')
    
    # Type inconsistencies
    issues += analyze_type_inconsistencies(df, 'employee_count', 'customers')
    
    # Soft deletes
    if 'deleted_at' in df.columns:
        deleted = df['deleted_at'].notna().sum()
        if deleted > 0:
            print_section("Soft-Deleted Records")
            print_issue(f"Found {deleted} soft-deleted records")
            issues += deleted
    
    print(f"\n{Colors.BOLD}Total issues found: {Colors.RED}{issues}{Colors.END}\n")
    return issues

def analyze_contacts():
    """Comprehensive analysis of contacts endpoint"""
    print_header("CONTACTS DATA QUALITY ANALYSIS")
    
    data = fetch_endpoint("contacts")
    if not data or 'contacts' not in data:
        print_issue("Failed to fetch contacts data")
        return
    
    df = pd.DataFrame(data['contacts'])
    print(f"Total records: {len(df)}")
    
    issues = 0
    
    # Duplicates
    print_section("Duplicate Records")
    issues += analyze_duplicates(df, 'id', 'contact IDs')
    
    # Missing values
    issues += analyze_missing_values(df, 'contacts')
    
    # Field name variations
    issues += analyze_field_name_variations(df, 'contacts')
    
    # Value casing
    issues += analyze_value_casing(df, 'status', 'status values')
    
    # Date formats
    date_fields = [f for f in ['created_at', 'created_date', 'updated_at', 'updated_date'] if f in df.columns]
    issues += analyze_date_formats(df, date_fields, 'contacts')
    
    # Invalid emails
    issues += analyze_invalid_emails(df, 'email', 'contacts')
    
    # Phone formats
    phone_fields = [f for f in ['phone', 'phone_number'] if f in df.columns]
    for field in phone_fields:
        issues += analyze_phone_formats(df, field, 'contacts')
    
    # Country variations
    issues += analyze_country_variations(df, 'country', 'contacts')
    
    print(f"\n{Colors.BOLD}Total issues found: {Colors.RED}{issues}{Colors.END}\n")
    return issues

def analyze_leads():
    """Comprehensive analysis of leads endpoint"""
    print_header("LEADS DATA QUALITY ANALYSIS")
    
    data = fetch_endpoint("leads")
    if not data or 'results' not in data:
        print_issue("Failed to fetch leads data")
        return
    
    df = pd.DataFrame(data['results'])
    print(f"Total records: {len(df)}")
    
    issues = 0
    
    # Duplicates
    print_section("Duplicate Records")
    issues += analyze_duplicates(df, 'id', 'lead IDs')
    
    # Missing values
    issues += analyze_missing_values(df, 'leads')
    
    # Field name variations
    issues += analyze_field_name_variations(df, 'leads')
    
    # Value casing
    status_field = 'lead_status' if 'lead_status' in df.columns else 'leadStatus'
    issues += analyze_value_casing(df, status_field, 'lead status values')
    issues += analyze_value_casing(df, 'priority', 'priority values')
    
    # Date formats
    issues += analyze_date_formats(df, ['created_at', 'updated_at'], 'leads')
    
    # Invalid emails
    issues += analyze_invalid_emails(df, 'email', 'leads')
    
    # Phone formats
    issues += analyze_phone_formats(df, 'phone', 'leads')
    
    # Country variations
    issues += analyze_country_variations(df, 'country', 'leads')
    
    # Type inconsistencies
    score_field = 'lead_score' if 'lead_score' in df.columns else 'score'
    issues += analyze_type_inconsistencies(df, score_field, 'leads')
    
    print(f"\n{Colors.BOLD}Total issues found: {Colors.RED}{issues}{Colors.END}\n")
    return issues

def analyze_deals():
    """Comprehensive analysis of deals endpoint"""
    print_header("DEALS DATA QUALITY ANALYSIS")
    
    data = fetch_endpoint("deals")
    if not data or 'data' not in data:
        print_issue("Failed to fetch deals data")
        return
    
    df = pd.DataFrame(data['data'])
    print(f"Total records: {len(df)}")
    
    issues = 0
    
    # Duplicates
    print_section("Duplicate Records")
    issues += analyze_duplicates(df, 'id', 'deal IDs')
    
    # Missing values
    issues += analyze_missing_values(df, 'deals')
    
    # Field name variations
    issues += analyze_field_name_variations(df, 'deals')
    
    # Value casing
    stage_field = 'stage' if 'stage' in df.columns else 'Stage'
    issues += analyze_value_casing(df, stage_field, 'stage values')
    issues += analyze_value_casing(df, 'currency', 'currency values')
    issues += analyze_value_casing(df, 'status', 'status values')
    
    # Date formats
    issues += analyze_date_formats(df, ['created_at', 'updated_at', 'expected_close_date'], 'deals')
    
    # Type inconsistencies
    issues += analyze_type_inconsistencies(df, 'amount', 'deals')
    issues += analyze_type_inconsistencies(df, 'probability', 'deals')
    
    # Structural inconsistencies
    print_section("Structural Inconsistencies")
    has_nested_contact = df['contact'].notna().sum() if 'contact' in df.columns else 0
    has_flat_contact = df['contact_id'].notna().sum() if 'contact_id' in df.columns else 0
    if has_nested_contact > 0 and has_flat_contact > 0:
        print_issue(f"Contact representation: {has_nested_contact} nested, {has_flat_contact} flat")
        issues += 1
    
    print(f"\n{Colors.BOLD}Total issues found: {Colors.RED}{issues}{Colors.END}\n")
    return issues

def analyze_versioning():
    """Analyze differences between API versions"""
    print_header("VERSION COMPARISON ANALYSIS")
    
    versions = ['v1', 'v2', 'v3']
    version_data = {}
    
    for version in versions:
        data = fetch_endpoint("customers", version=version)
        if data and 'data' in data:
            version_data[version] = data['data']
    
    if len(version_data) < 2:
        print_issue("Could not fetch multiple versions for comparison")
        return
    
    print_section("Record Count by Version")
    for version, data in version_data.items():
        print(f"   {version}: {len(data)} records")
    
    # Compare v1 vs v3
    if 'v1' in version_data and 'v3' in version_data:
        v1_ids = {r['id'] for r in version_data['v1']}
        v3_ids = {r['id'] for r in version_data['v3']}
        
        new_records = v3_ids - v1_ids
        removed_records = v1_ids - v3_ids
        
        print_section("Changes from v1 to v3")
        print(f"   New records: {len(new_records)}")
        print(f"   Removed records: {len(removed_records)}")
        
        # Field changes
        if version_data['v1'] and version_data['v3']:
            v1_fields = set(version_data['v1'][0].keys())
            v3_fields = set(version_data['v3'][0].keys())
            new_fields = v3_fields - v1_fields
            removed_fields = v1_fields - v3_fields
            
            if new_fields:
                print(f"   New fields: {new_fields}")
            if removed_fields:
                print(f"   Removed fields: {removed_fields}")

def generate_summary(total_issues):
    """Generate overall summary"""
    print_header("OVERALL DATA QUALITY SUMMARY")
    
    print(f"{Colors.BOLD}Total Issues Found: {Colors.RED}{total_issues}{Colors.END}\n")
    
    print(f"{Colors.BOLD}Issue Categories:{Colors.END}")
    print(f"  {Colors.YELLOW}✗{Colors.END} Duplicate records")
    print(f"  {Colors.YELLOW}✗{Colors.END} Missing/null values")
    print(f"  {Colors.YELLOW}✗{Colors.END} Inconsistent field naming")
    print(f"  {Colors.YELLOW}✗{Colors.END} Inconsistent value casing")
    print(f"  {Colors.YELLOW}✗{Colors.END} Mixed date formats")
    print(f"  {Colors.YELLOW}✗{Colors.END} Invalid data (emails, phones)")
    print(f"  {Colors.YELLOW}✗{Colors.END} Mixed data types")
    print(f"  {Colors.YELLOW}✗{Colors.END} Structural inconsistencies")
    print(f"  {Colors.YELLOW}✗{Colors.END} Country/region variations")
    print(f"  {Colors.YELLOW}✗{Colors.END} Soft-deleted records")
    
    print(f"\n{Colors.BOLD}Recommended Actions:{Colors.END}")
    print(f"  {Colors.GREEN}→{Colors.END} Implement deduplication logic")
    print(f"  {Colors.GREEN}→{Colors.END} Standardize field names and casing")
    print(f"  {Colors.GREEN}→{Colors.END} Validate and clean email/phone formats")
    print(f"  {Colors.GREEN}→{Colors.END} Normalize date formats to ISO 8601")
    print(f"  {Colors.GREEN}→{Colors.END} Handle null vs empty string consistently")
    print(f"  {Colors.GREEN}→{Colors.END} Type conversion and validation")
    print(f"  {Colors.GREEN}→{Colors.END} Separate active from deleted records")
    print(f"  {Colors.GREEN}→{Colors.END} Create data quality rules and monitoring")
    print(f"  {Colors.GREEN}→{Colors.END} Build master data management process")
    print(f"  {Colors.GREEN}→{Colors.END} Implement schema validation")
    
    print(f"\n{Colors.BOLD}{Colors.GREEN}This API is perfect for testing your data engineering pipeline! 🚀{Colors.END}\n")

if __name__ == "__main__":
    print_header("PRODUCTION CRM API - DATA QUALITY ANALYSIS")
    print(f"\n{Colors.BOLD}API Endpoint:{Colors.END} {BASE_URL}")
    print(f"{Colors.BOLD}Make sure the Mockoon API is running!{Colors.END}\n")
    
    try:
        # Test connection
        response = requests.get(f"{BASE_URL}/customers", timeout=5)
        response.raise_for_status()
        print_success("API connection successful\n")
        
        # Run all analyses
        total_issues = 0
        total_issues += analyze_customers() or 0
        total_issues += analyze_contacts() or 0
        total_issues += analyze_leads() or 0
        total_issues += analyze_deals() or 0
        
        # Version comparison
        analyze_versioning()
        
        # Generate summary
        generate_summary(total_issues)
        
    except requests.exceptions.ConnectionError:
        print_issue("\nCould not connect to API. Make sure Mockoon is running on port 3000")
        print("\nTo start the API:")
        print("  mockoon-cli start --data ./mockoon-crm-production-api.json --port 3000")
    except Exception as e:
        print_issue(f"\nError: {e}")
        print("\nMake sure:")
        print("  1. Mockoon is running on port 3000")
        print("  2. Required packages are installed: pip install requests pandas")
