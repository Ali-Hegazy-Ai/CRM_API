import argparse
import csv
import importlib.util
import json
import os
import random
import ssl
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(ROOT_DIR, "fastapi-crm-api")
BEHAVIOR_EXTRACTOR_PATH = os.path.join(API_DIR, "behavior_extractor.py")


def _load_behavior_functions():
    spec = importlib.util.spec_from_file_location("behavior_extractor", BEHAVIOR_EXTRACTOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load behavior_extractor module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    extract_fn = getattr(module, "extract_behavior_profile", None)
    knobs_fn = getattr(module, "profile_to_generation_knobs", None)

    if extract_fn is None or knobs_fn is None:
        raise RuntimeError("behavior_extractor is missing required functions")

    return extract_fn, knobs_fn


extract_behavior_profile, profile_to_generation_knobs = _load_behavior_functions()


DEFAULT_BASE_URL = "https://ali-hegazy-ai8576-26vewggo.leapcell.dev"
DEFAULT_VERSION = "v3"
DEFAULT_COUNT = 220
DEFAULT_OUT_DIR = os.path.join(os.path.dirname(__file__), "exports")
DEFAULT_BEHAVIOR_CSV = os.path.join(os.path.dirname(__file__), "exports", "ali.csv")

FIRST_NAMES = [
    "Ava", "Noah", "Mia", "Liam", "Emma", "Omar", "Nora", "Yara", "Ali", "Sara",
    "Maya", "Hassan", "Adam", "Lina", "Rami", "Dina", "James", "Layla", "Amir", "Leah",
]

LAST_NAMES = [
    "Park", "Simmons", "Howe", "King", "Nixon", "Stevens", "Cross", "Walker", "Brown", "Nguyen",
    "Johnson", "Miller", "Shaw", "Anderson", "Clark", "Wright", "Brooks", "Hayes", "Cole", "Turner",
]

COMPANY_SUFFIXES = ["Inc", "LLC", "Ltd", "Group", "PLC", "Sons", "Systems", "Partners", "Holdings"]
ACTIVITY_TYPES = ["call", "email", "meeting", "task", "note", "demo", "handoff"]
LEAD_STATES = ["new", "nurturing", "qualified", "stalled", "converted", "dropped"]
DEAL_STATES = ["open", "negotiating", "stalled", "won", "lost", "disappeared"]
CONTACT_STATES = ["active", "watchlist", "inactive", "churn_risk"]

COUNTRIES = ["US", "US", "US", "GB", "GB", "EG", "EG", "AE", "AE", "CA", "DE", "FR"]
SOURCE_CHANNELS = [
    "hubspot", "hubspot", "salesforce", "salesforce", "pipedrive", "zoho", "manual_entry", "internal_crm"
]

SOURCE_CASE_VARIANTS = {
    "hubspot": ["HubSpot", "HUBSPOT"],
    "salesforce": ["SalesForce", "SALESFORCE"],
    "pipedrive": ["PipeDrive"],
    "zoho": ["Zoho"],
    "manual_entry": ["Manual_Entry"],
    "internal_crm": ["Internal_CRM", "iNTERNALcrm"],
}


def clamp(value, low, high):
    return max(low, min(high, value))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic CRM entities using behavior learned from a real CSV (without schema copying)."
    )
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Internet API base URL")
    parser.add_argument("--version", default=DEFAULT_VERSION, help="API version for seed requests")
    parser.add_argument("--behavior-csv", default=DEFAULT_BEHAVIOR_CSV, help="CSV file used only for behavior extraction")
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help="Total records across entities (100-500)")
    parser.add_argument("--timeout", type=int, default=20, help="HTTP timeout in seconds")
    parser.add_argument("--seed", type=int, default=0, help="Random seed (0 disables fixed seed)")
    parser.add_argument("--no-api-read", action="store_true", help="Do not read health/seed endpoints; use local fallback seeds only")
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR, help="Output directory")
    parser.add_argument("--output-prefix", default="crm_behavioral", help="Output file prefix")
    return parser.parse_args()


def safe_base_url(url):
    value = str(url).strip()
    if value.endswith("/"):
        value = value[:-1]
    return value


def iso_utc(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def random_datetime_between(start_value, end_value):
    if end_value <= start_value:
        return start_value
    span = int((end_value - start_value).total_seconds())
    if span <= 0:
        return start_value
    return start_value + timedelta(seconds=random.randint(0, span))


def pick_burst_timestamp(start_value, end_value, burst_centers, knobs):
    if burst_centers and random.random() < knobs["burst_chance"]:
        center = random.choice(burst_centers)
        spread_hours = 1.5 + (knobs["irregularity"] * 8.0)
        spread_seconds = int(spread_hours * 3600)
        jitter = random.randint(-spread_seconds, spread_seconds)
        chosen = center + timedelta(seconds=jitter)
        if chosen < start_value:
            chosen = start_value
        if chosen > end_value:
            chosen = end_value
        return chosen

    return random_datetime_between(start_value, end_value)


def fetch_json(url, timeout):
    request = Request(url, headers={"Accept": "application/json"})
    context = ssl.create_default_context()

    try:
        response = urlopen(request, timeout=timeout, context=context)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"Request failed: {exc}")
        return None

    try:
        text = response.read().decode("utf-8", errors="replace")
    finally:
        try:
            response.close()
        except Exception:
            pass

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        print("Failed to decode JSON payload")
        return None


def build_query_url(base_url, path, query):
    return f"{base_url}{path}?{urlencode(query)}"


def load_seed_companies(base_url, version, timeout):
    names = []
    ids = []

    page = 1
    while page <= 3:
        url = build_query_url(base_url, "/companies", {"version": version, "page": page, "limit": 100})
        payload = fetch_json(url, timeout)
        if not isinstance(payload, dict):
            break

        rows = payload.get("companies", [])
        if not isinstance(rows, list) or len(rows) == 0:
            break

        for row in rows:
            if not isinstance(row, dict):
                continue
            name_value = row.get("name")
            id_value = row.get("id") or row.get("company_id")
            if isinstance(name_value, str) and len(name_value.strip()) > 0:
                names.append(name_value.strip())
            if isinstance(id_value, str) and len(id_value.strip()) > 0:
                ids.append(id_value.strip())

        total_count = payload.get("total_count")
        page_size = payload.get("page_size")
        page_number = payload.get("page_number")

        if isinstance(total_count, int) and isinstance(page_size, int) and isinstance(page_number, int):
            if page_number * page_size >= total_count:
                break

        page = page + 1

    return names, ids


def load_seed_owners(base_url, timeout):
    payload = fetch_json(base_url + "/owners", timeout)
    owners = []
    if isinstance(payload, list):
        for row in payload:
            if not isinstance(row, dict):
                continue
            owner_id = row.get("id")
            if isinstance(owner_id, str) and len(owner_id.strip()) > 0:
                owners.append(owner_id.strip())
    return owners


def slugify(value):
    text = str(value).strip().lower().replace("&", " and ")
    result = []
    for ch in text:
        if ch.isalnum():
            result.append(ch)
        else:
            result.append(" ")

    words = []
    current = ""
    for ch in result:
        if ch == " ":
            if len(current) > 0:
                words.append(current)
                current = ""
        else:
            current = current + ch

    if len(current) > 0:
        words.append(current)

    if len(words) == 0:
        return "entity"

    merged = ""
    for word in words:
        merged = merged + word
    return merged


def choose_company_name(seed_names):
    if seed_names and random.random() < 0.55:
        return random.choice(seed_names)

    a = random.choice(LAST_NAMES)
    b = random.choice(LAST_NAMES)
    c = random.choice(LAST_NAMES)
    shape = random.randint(1, 4)

    if shape == 1:
        return f"{a} {random.choice(COMPANY_SUFFIXES)}"
    if shape == 2:
        return f"{a}, {b} and {c}"
    if shape == 3:
        return f"{a}-{b} {random.choice(COMPANY_SUFFIXES)}"
    return f"{a} and Sons"


def choose_owner(owner_seeds):
    if owner_seeds and random.random() < 0.35:
        return random.choice(owner_seeds)

    roll = random.random()
    if roll < 0.20:
        return "manual_queue"
    if roll < 0.45:
        return f"sales_{random.randint(1, 99):02d}"
    if roll < 0.68:
        return f"rep_{random.randint(1, 99):02d}"
    if roll < 0.92:
        return f"own_{random.randint(1, 999):03d}"
    return f"orphan_{random.randint(1, 999999):06d}"


def choose_source(knobs):
    source = random.choice(SOURCE_CHANNELS)
    if random.random() < knobs["format_noise_chance"] * 0.7:
        variants = SOURCE_CASE_VARIANTS.get(source, [])
        if variants:
            return random.choice(variants)
    return source


def choose_email(first_name, last_name, company_name, knobs):
    first = slugify(first_name)
    last = slugify(last_name)
    domain_root = slugify(company_name)
    tld = random.choice(["com", "com", "org", "net", "biz", "info"])

    if len(domain_root) < 5:
        domain_root = domain_root + "group"

    domain = f"{domain_root}.{tld}"

    # Keep generic placeholders low; mostly name-derived.
    generic_threshold = 0.05
    derived_threshold = 0.68

    roll = random.random()
    if roll < generic_threshold:
        return f"{random.choice(['info', 'contact', 'support', 'sales'])}@{domain}"

    if roll < derived_threshold:
        pattern = random.randint(1, 4)
        if pattern == 1:
            return f"{first}.{last}@{domain}"
        if pattern == 2:
            return f"{first[0]}.{last}@{domain}"
        if pattern == 3:
            return f"{first}@{domain}"
        return f"{first}{last}@{domain}"

    # Mixed realism: person can use another plausible domain.
    alt_domain = f"{slugify(random.choice(LAST_NAMES))}{slugify(random.choice(LAST_NAMES))}.net"
    return f"{first}{random.randint(1, 999)}@{alt_domain}"


def random_digits(country):
    if country in {"US", "CA"}:
        return f"{random.randint(200,999)}{random.randint(100,999)}{random.randint(1000,9999)}"
    if country == "GB":
        return f"{random.randint(1000000000,9999999999)}"
    if country == "EG":
        return f"{random.randint(1000000000,9999999999)}"
    return f"{random.randint(1000000000,9999999999)}"


def format_phone(country, digits, style):
    if style == "paren":
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if style == "dash":
        return f"{digits[0:3]}-{digits[3:6]}-{digits[6:10]}"
    if style == "raw":
        return digits

    if country == "GB":
        return f"+44 {digits[0:4]} {digits[4:10]}"
    if country == "EG":
        return f"+20 {digits[0:3]} {digits[3:10]}"
    if country == "AE":
        return f"+971 {digits[0:2]} {digits[2:10]}"
    return f"+1 {digits[0:3]} {digits[3:6]} {digits[6:10]}"


def choose_phone(country, knobs):
    # 10-15% null phone behavior.
    if random.random() < clamp(0.10 + knobs["missing_field_chance"] * 0.25, 0.10, 0.15):
        return None, None

    digits = random_digits(country)
    style = random.choice(["paren", "dash", "plus", "raw"])
    value = format_phone(country, digits, style)

    if random.random() < 0.08:
        value = f"{value} x{random.randint(1000, 9999)}"

    return value, digits


def maybe_add_redundant_phone(record, digits, country):
    if digits is None:
        return

    if random.random() < 0.10:
        if random.random() < 0.50:
            record["backup_phone"] = record.get("reach_phone")
        else:
            alt_style = random.choice(["paren", "dash", "plus", "raw"])
            record["backup_phone"] = format_phone(country, digits, alt_style)


def make_entity_id(prefix, start_number, index):
    return f"{prefix}_{start_number + index:06d}"


def apply_optional_noise(record, optional_fields, knobs):
    for field in optional_fields:
        if field not in record:
            continue
        if random.random() < knobs["missing_field_chance"]:
            if random.random() < 0.50:
                record[field] = None
            else:
                record.pop(field, None)


def allocate_entity_counts(total_count, knobs):
    dep = knobs["dependency_strength"]
    activity_skew = knobs["activity_skew"]
    missing = knobs["missing_field_chance"]

    contact_ratio = 0.30 + (dep * 0.08)
    lead_ratio = 0.24 + (missing * 0.10)
    deal_ratio = 0.18 + (knobs["long_tail_strength"] * 0.08)

    if contact_ratio + lead_ratio + deal_ratio > 0.82:
        deal_ratio = max(0.14, deal_ratio - 0.05)

    activity_ratio = 1.0 - contact_ratio - lead_ratio - deal_ratio
    activity_ratio = clamp(activity_ratio + ((activity_skew - 0.5) * 0.08), 0.20, 0.36)

    contacts = int(total_count * contact_ratio)
    leads = int(total_count * lead_ratio)
    deals = int(total_count * deal_ratio)
    activities = total_count - contacts - leads - deals

    contacts = max(25, contacts)
    leads = max(20, leads)
    deals = max(15, deals)
    activities = max(20, activities)

    current_total = contacts + leads + deals + activities
    while current_total > total_count:
        if activities > 20:
            activities -= 1
        elif leads > 20:
            leads -= 1
        elif deals > 15:
            deals -= 1
        elif contacts > 25:
            contacts -= 1
        else:
            break
        current_total = contacts + leads + deals + activities

    while current_total < total_count:
        activities += 1
        current_total += 1

    return contacts, leads, deals, activities


def pick_long_tail_weight(strength):
    alpha = 2.6 - (strength * 1.3)
    alpha = clamp(alpha, 1.10, 2.60)
    value = random.paretovariate(alpha)
    return clamp(value, 1.0, 16.0)


def generate_timestamp_pack(now_dt, history_start, history_end, burst_centers, knobs):
    created_dt = pick_burst_timestamp(history_start, history_end, burst_centers, knobs)

    # Updated time usually after created, with irregular spacing.
    base_minutes = random.randint(2, 240)
    irregular_bonus = int(knobs["irregularity"] * random.randint(30, 9000))
    update_candidate = created_dt + timedelta(minutes=base_minutes + irregular_bonus)
    if update_candidate > now_dt:
        update_candidate = random_datetime_between(created_dt + timedelta(minutes=1), now_dt)
    updated_dt = update_candidate

    # Last touch around updated (before or very near it).
    touch_start = created_dt
    touch_end = updated_dt + timedelta(minutes=random.randint(0, 12))
    if touch_end > now_dt:
        touch_end = now_dt
    last_touch_dt = random_datetime_between(touch_start, touch_end)

    # Sync near updated but can lag if noisy.
    if random.random() < knobs["silence_chance"]:
        sync_start = created_dt
    else:
        sync_start = max(created_dt, updated_dt - timedelta(days=random.randint(0, 10)))
    last_sync_dt = random_datetime_between(sync_start, updated_dt)

    return created_dt, updated_dt, last_touch_dt, last_sync_dt


def generate_contacts(count, seed_company_names, seed_company_ids, seed_owners, knobs, now_dt, history_start, history_end, burst_centers):
    contacts = []
    activity_weights = {}
    id_start = random.randint(1000, 900000)

    for index in range(count):
        contact_key = make_entity_id("ctc", id_start, index)

        first_name = random.choice(FIRST_NAMES)
        last_name = random.choice(LAST_NAMES)
        company_name = choose_company_name(seed_company_names)

        if seed_company_ids and random.random() < 0.45:
            account_ref = random.choice(seed_company_ids)
        else:
            account_ref = f"acct_{random.randint(1,999999):06d}"

        country = random.choice(COUNTRIES)
        source_channel = choose_source(knobs)

        created_dt, updated_dt, last_touch_dt, last_sync_dt = generate_timestamp_pack(
            now_dt,
            history_start,
            history_end,
            burst_centers,
            knobs,
        )

        phone_value, digits = choose_phone(country, knobs)

        record = {
            "contact_key": contact_key,
            "display_name": f"{first_name} {last_name}",
            "organization_label": company_name,
            "account_ref": account_ref,
            "reach_email": choose_email(first_name, last_name, company_name, knobs),
            "reach_phone": phone_value,
            "country_code": country,
            "owner_queue": choose_owner(seed_owners),
            "lifecycle_state": random.choice(CONTACT_STATES),
            "created_at": iso_utc(created_dt),
            "updated_at": iso_utc(updated_dt),
            "last_touch_at": iso_utc(last_touch_dt),
            "last_synced_at": iso_utc(last_sync_dt),
            "source_channel": source_channel,
            "sync_health": random.choice(["synced", "ok", "pending", "sync_lag"]),
            "ingest_ref": f"ING-{random.randint(10000, 99999)}",
        }

        maybe_add_redundant_phone(record, digits, country)

        if random.random() < 0.13:
            record["legacy_created_hint"] = iso_utc(created_dt + timedelta(minutes=random.randint(0, 59), seconds=random.randint(0, 59)))

        apply_optional_noise(record, ["reach_phone", "owner_queue", "ingest_ref", "legacy_created_hint"], knobs)

        if random.random() < knobs["format_noise_chance"] * 0.45:
            record["source_channel"] = str(record["source_channel"]).upper()

        if random.random() < knobs["outlier_chance"] * 0.45:
            record["signal_score"] = random.randint(-50, 180)
        else:
            record["signal_score"] = random.randint(5, 95)

        contacts.append(record)
        activity_weights[contact_key] = pick_long_tail_weight(knobs["long_tail_strength"])

    return contacts, activity_weights


def generate_leads(count, contacts, seed_company_ids, seed_owners, knobs, now_dt, history_start, history_end, burst_centers):
    leads = []
    id_start = random.randint(1000, 900000)

    contact_ids = []
    for record in contacts:
        contact_ids.append(record.get("contact_key"))

    for index in range(count):
        lead_key = make_entity_id("ld", id_start, index)
        country = random.choice(COUNTRIES)
        source_channel = choose_source(knobs)

        created_dt, updated_dt, last_touch_dt, last_sync_dt = generate_timestamp_pack(
            now_dt,
            history_start,
            history_end,
            burst_centers,
            knobs,
        )

        linked_contact = None
        if contact_ids and random.random() < knobs["dependency_strength"]:
            linked_contact = random.choice(contact_ids)

        if seed_company_ids and random.random() < 0.40:
            account_ref = random.choice(seed_company_ids)
        else:
            account_ref = f"acct_{random.randint(1,999999):06d}"

        lead_state = random.choice(LEAD_STATES)
        converted = False
        converted_at = None

        if lead_state == "converted":
            converted = True
            converted_at = iso_utc(updated_dt + timedelta(minutes=random.randint(1, 120), seconds=random.randint(0, 59)))

        if random.random() < knobs["silence_chance"] * 0.60:
            lead_state = "stalled"
            converted = False
            converted_at = None

        score_base = random.randint(1, 100)
        if random.random() < knobs["outlier_chance"]:
            score_base = random.choice([0, 1, 2, 140, 170])

        record = {
            "lead_key": lead_key,
            "linked_contact": linked_contact,
            "account_ref": account_ref,
            "source_channel": source_channel,
            "country_code": country,
            "funnel_state": lead_state,
            "interest_score": score_base,
            "conversion_flag": converted,
            "converted_at": converted_at,
            "owner_queue": choose_owner(seed_owners),
            "created_at": iso_utc(created_dt),
            "updated_at": iso_utc(updated_dt),
            "last_touch_at": iso_utc(last_touch_dt),
            "last_synced_at": iso_utc(last_sync_dt),
            "ingest_ref": f"ING-{random.randint(10000, 99999)}",
        }

        if random.random() < 0.28:
            record["engagement_hint"] = random.choice(["web", "email", "field", "partner", "event"])

        apply_optional_noise(record, ["linked_contact", "owner_queue", "ingest_ref", "engagement_hint"], knobs)

        if random.random() < knobs["format_noise_chance"] * 0.40:
            record["source_channel"] = str(record["source_channel"]).title()

        leads.append(record)

    return leads


def long_tail_amount(knobs):
    base = random.uniform(5000.0, 25000.0)
    alpha = 2.8 - (knobs["long_tail_strength"] * 1.6)
    alpha = clamp(alpha, 1.08, 2.8)
    multiplier = random.paretovariate(alpha)
    value = base * multiplier
    return round(clamp(value, 500.0, 2500000.0), 2)


def generate_deals(count, leads, seed_owners, knobs, now_dt, history_start, history_end, burst_centers):
    deals = []
    id_start = random.randint(1000, 900000)

    lead_ids = []
    for record in leads:
        lead_ids.append(record.get("lead_key"))

    for index in range(count):
        deal_key = make_entity_id("dl", id_start, index)

        created_dt, updated_dt, last_touch_dt, last_sync_dt = generate_timestamp_pack(
            now_dt,
            history_start,
            history_end,
            burst_centers,
            knobs,
        )

        linked_lead = None
        if lead_ids and random.random() < knobs["dependency_strength"]:
            linked_lead = random.choice(lead_ids)

        deal_state = random.choice(DEAL_STATES)
        close_at = None
        disappeared_at = None

        if random.random() < 0.28 + knobs["silence_chance"] * 0.35:
            deal_state = "stalled"

        if random.random() < 0.16 + knobs["dependency_strength"] * 0.18:
            deal_state = random.choice(["won", "lost"])
            close_dt = updated_dt + timedelta(minutes=random.randint(10, 300), seconds=random.randint(0, 59))
            if close_dt > now_dt:
                close_dt = now_dt
            close_at = iso_utc(close_dt)

        if random.random() < 0.03 + knobs["outlier_chance"] * 0.18:
            deal_state = "disappeared"
            disappear_dt = updated_dt + timedelta(minutes=random.randint(10, 300), seconds=random.randint(0, 59))
            if disappear_dt > now_dt:
                disappear_dt = now_dt
            disappeared_at = iso_utc(disappear_dt)

        amount_value = long_tail_amount(knobs)
        if random.random() < knobs["outlier_chance"] * 0.45:
            amount_value = round(amount_value * random.uniform(4.0, 10.0), 2)

        probability_score = random.randint(5, 95)
        if deal_state == "won":
            probability_score = random.randint(90, 100)
        elif deal_state in {"lost", "disappeared"}:
            probability_score = random.randint(0, 35)

        record = {
            "deal_key": deal_key,
            "linked_lead": linked_lead,
            "pipeline_state": deal_state,
            "amount_value": amount_value,
            "currency_hint": random.choice(["USD", "USD", "USD", "EUR", "GBP", "AED"]),
            "probability_score": probability_score,
            "owner_queue": choose_owner(seed_owners),
            "created_at": iso_utc(created_dt),
            "updated_at": iso_utc(updated_dt),
            "last_touch_at": iso_utc(last_touch_dt),
            "last_synced_at": iso_utc(last_sync_dt),
            "closed_at": close_at,
            "disappeared_at": disappeared_at,
            "source_channel": choose_source(knobs),
            "ingest_ref": f"ING-{random.randint(10000, 99999)}",
        }

        apply_optional_noise(record, ["linked_lead", "owner_queue", "ingest_ref"], knobs)

        if random.random() < knobs["format_noise_chance"] * 0.40:
            record["currency_hint"] = str(record["currency_hint"]).lower()

        if random.random() < 0.40:
            # Mixed type to mimic real-world inconsistencies.
            if random.random() < 0.50:
                record["probability_score"] = str(record["probability_score"])

        deals.append(record)

    return deals


def weighted_entity_pick(weights_dict):
    keys = list(weights_dict.keys())
    weights = list(weights_dict.values())
    return random.choices(keys, weights=weights, k=1)[0]


def pick_weighted_key(weight_map):
    keys = list(weight_map.keys())
    weights = list(weight_map.values())
    return random.choices(keys, weights=weights, k=1)[0]


def generate_activities(count, contacts, leads, deals, contact_weights, knobs, now_dt, history_start, history_end, burst_centers):
    activities = []
    id_start = random.randint(1000, 900000)

    lead_weights = {}
    for lead in leads:
        lead_key = lead.get("lead_key")
        if lead_key:
            lead_weights[lead_key] = pick_long_tail_weight(knobs["activity_skew"])

    deal_weights = {}
    for deal in deals:
        deal_key = deal.get("deal_key")
        if deal_key:
            deal_weights[deal_key] = pick_long_tail_weight(knobs["activity_skew"])

    entity_type_weights = {
        "contact": 0.44,
        "lead": 0.28,
        "deal": 0.28,
    }

    for index in range(count):
        activity_key = make_entity_id("act", id_start, index)

        created_dt, updated_dt, last_touch_dt, last_sync_dt = generate_timestamp_pack(
            now_dt,
            history_start,
            history_end,
            burst_centers,
            knobs,
        )

        parent_kind = weighted_entity_pick(entity_type_weights)
        parent_key = None

        if parent_kind == "contact" and contact_weights:
            parent_key = pick_weighted_key(contact_weights)
        elif parent_kind == "lead" and lead_weights:
            parent_key = pick_weighted_key(lead_weights)
        elif parent_kind == "deal" and deal_weights:
            parent_key = pick_weighted_key(deal_weights)

        if parent_key is None and contact_weights:
            parent_kind = "contact"
            parent_key = pick_weighted_key(contact_weights)

        happened_at = pick_burst_timestamp(history_start, now_dt, burst_centers, knobs)
        logged_at = random_datetime_between(happened_at, now_dt)

        record = {
            "activity_key": activity_key,
            "parent_kind": parent_kind,
            "parent_key": parent_key,
            "activity_kind": random.choice(ACTIVITY_TYPES),
            "outcome_code": random.choice(["done", "pending", "skipped", "rescheduled"]),
            "happened_at": iso_utc(happened_at),
            "logged_at": iso_utc(logged_at),
            "created_at": iso_utc(created_dt),
            "updated_at": iso_utc(updated_dt),
            "last_touch_at": iso_utc(last_touch_dt),
            "last_synced_at": iso_utc(last_sync_dt),
            "source_channel": choose_source(knobs),
            "impact_score": random.randint(1, 100),
            "ingest_ref": f"ING-{random.randint(10000, 99999)}",
        }

        if random.random() < knobs["outlier_chance"] * 0.50:
            record["impact_score"] = random.randint(130, 240)

        if random.random() < 0.32:
            record["note_blurb"] = random.choice([
                "follow-up needed",
                "pending internal response",
                "customer asked for clarification",
                "timing uncertain",
                "no response yet",
            ])

        apply_optional_noise(record, ["note_blurb", "ingest_ref"], knobs)
        activities.append(record)

    return activities


def summarize_timestamps(entities):
    min_created = None
    max_updated = None

    for entity_rows in entities.values():
        for row in entity_rows:
            created = row.get("created_at")
            updated = row.get("updated_at")

            created_dt = None
            updated_dt = None

            if isinstance(created, str):
                try:
                    created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                except ValueError:
                    created_dt = None

            if isinstance(updated, str):
                try:
                    updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                except ValueError:
                    updated_dt = None

            if created_dt is not None:
                if min_created is None or created_dt < min_created:
                    min_created = created_dt

            if updated_dt is not None:
                if max_updated is None or updated_dt > max_updated:
                    max_updated = updated_dt

    return min_created, max_updated


def write_json(path, payload):
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=True, indent=2)


def write_entity_csv(path, rows):
    all_keys = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                all_keys.append(key)

    with open(path, "w", newline="", encoding="utf-8") as file_handle:
        writer = csv.DictWriter(file_handle, fieldnames=all_keys)
        writer.writeheader()
        for row in rows:
            if isinstance(row, dict):
                writer.writerow(row)


def build_flat_rows(entities):
    flat_rows = []
    for entity_name, rows in entities.items():
        for row in rows:
            if not isinstance(row, dict):
                continue

            entity_key = row.get(f"{entity_name[:-1]}_key")
            if entity_key is None:
                entity_key = row.get("activity_key")

            flat_rows.append(
                {
                    "entity_kind": entity_name,
                    "entity_key": entity_key,
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                    "last_touch_at": row.get("last_touch_at"),
                    "state_marker": row.get("lifecycle_state") or row.get("funnel_state") or row.get("pipeline_state") or row.get("outcome_code"),
                    "value_signal": row.get("signal_score") or row.get("interest_score") or row.get("amount_value") or row.get("impact_score"),
                    "parent_key": row.get("linked_contact") or row.get("linked_lead") or row.get("parent_key"),
                    "source_channel": row.get("source_channel"),
                    "payload_json": json.dumps(row, ensure_ascii=True),
                }
            )
    return flat_rows


def main():
    args = parse_args()

    if args.seed != 0:
        random.seed(args.seed)

    if args.count < 100 or args.count > 500:
        print("count must be between 100 and 500")
        return 1

    base_url = safe_base_url(args.base_url)

    print("Extracting abstract behavior from CSV...")
    profile = extract_behavior_profile(args.behavior_csv)
    knobs = profile_to_generation_knobs(profile)

    company_names = []
    company_ids = []
    owner_ids = []
    seed_mode = "offline"

    if args.no_api_read:
        print("API reads disabled by --no-api-read. Using fallback seed pools.")
    else:
        print("Checking internet API availability...")
        health = fetch_json(base_url + "/health", args.timeout)

        if isinstance(health, dict):
            print("Loading seed context from internet API...")
            company_names, company_ids = load_seed_companies(base_url, args.version, args.timeout)
            owner_ids = load_seed_owners(base_url, args.timeout)
            seed_mode = "internet-api"
        else:
            print("Internet API health check failed. Falling back to local seed pools.")

    if not company_names:
        company_names = ["Northstar Group", "Atlas Systems", "Harbor Partners", "Cedar Labs"]
    if not company_ids:
        company_ids = ["acct_000101", "acct_000202", "acct_000303"]

    out_dir = args.out_dir
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    now_dt = datetime.now(timezone.utc)
    history_start = now_dt - timedelta(days=1460)
    history_end = now_dt - timedelta(days=2)

    burst_centers = []
    burst_count = random.randint(4, 12)
    for _ in range(burst_count):
        burst_centers.append(random_datetime_between(history_start, history_end))

    contact_count, lead_count, deal_count, activity_count = allocate_entity_counts(args.count, knobs)

    print(
        "Entity allocation:",
        f"contacts={contact_count}",
        f"leads={lead_count}",
        f"deals={deal_count}",
        f"activities={activity_count}",
    )

    contacts, contact_weights = generate_contacts(
        contact_count,
        company_names,
        company_ids,
        owner_ids,
        knobs,
        now_dt,
        history_start,
        history_end,
        burst_centers,
    )

    leads = generate_leads(
        lead_count,
        contacts,
        company_ids,
        owner_ids,
        knobs,
        now_dt,
        history_start,
        history_end,
        burst_centers,
    )

    deals = generate_deals(
        deal_count,
        leads,
        owner_ids,
        knobs,
        now_dt,
        history_start,
        history_end,
        burst_centers,
    )

    activities = generate_activities(
        activity_count,
        contacts,
        leads,
        deals,
        contact_weights,
        knobs,
        now_dt,
        history_start,
        history_end,
        burst_centers,
    )

    entities = {
        "contacts": contacts,
        "leads": leads,
        "deals": deals,
        "activities": activities,
    }

    min_created, max_updated = summarize_timestamps(entities)
    if min_created is None or max_updated is None:
        print("Failed to compute temporal bounds from generated records")
        return 1

    started_at_dt = min_created - timedelta(minutes=random.randint(5, 180), seconds=random.randint(1, 59))
    completed_at_dt = max_updated + timedelta(minutes=random.randint(5, 180), seconds=random.randint(1, 59))

    fetched_count = len(contacts) + len(leads) + len(deals) + len(activities)
    extra_total = random.randint(max(8, int(fetched_count * 0.03)), max(15, int(fetched_count * 0.12)))
    api_total_last_seen = fetched_count + extra_total

    payload = {
        "source": base_url,
        "seed_mode": seed_mode,
        "behavior_source_csv": args.behavior_csv,
        "version": args.version,
        "started_at": iso_utc(started_at_dt),
        "completed_at": iso_utc(completed_at_dt),
        "fetched_count": fetched_count,
        "api_total_last_seen": api_total_last_seen,
        "behavior_profile": profile,
        "generation_knobs": knobs,
        "entities": entities,
    }

    prefix = f"{args.output_prefix}_{args.version}"
    json_path = os.path.join(out_dir, f"{prefix}.json")
    contacts_csv = os.path.join(out_dir, f"{prefix}_contacts.csv")
    leads_csv = os.path.join(out_dir, f"{prefix}_leads.csv")
    deals_csv = os.path.join(out_dir, f"{prefix}_deals.csv")
    activities_csv = os.path.join(out_dir, f"{prefix}_activities.csv")
    flat_csv = os.path.join(out_dir, f"{prefix}_flat.csv")

    write_json(json_path, payload)
    write_entity_csv(contacts_csv, contacts)
    write_entity_csv(leads_csv, leads)
    write_entity_csv(deals_csv, deals)
    write_entity_csv(activities_csv, activities)
    write_entity_csv(flat_csv, build_flat_rows(entities))

    print(f"Behavior rows analyzed: {profile.get('rows_analyzed')}")
    print(f"Generated total records: {fetched_count}")
    print(f"Saved JSON: {json_path}")
    print(f"Saved CSV: {flat_csv}")
    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
