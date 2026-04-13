import argparse
import copy
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from faker import Faker


VERSIONS = ["v1", "v2", "v3"]
ENTITIES = ["customers", "contacts", "leads", "deals", "activities", "notes", "companies"]

V3_COUNTS = {
    "customers": 260,
    "contacts": 420,
    "leads": 240,
    "deals": 190,
    "activities": 720,
    "notes": 320,
    "companies": 140,
}

SOURCE_SYSTEMS = [
    "salesforce",
    "hubspot",
    "zoho",
    "pipedrive",
    "internal_crm",
    "manual_entry",
]

SOURCE_NAME_VARIANTS = {
    "salesforce": ["salesforce", "SalesForce", "SF"],
    "hubspot": ["hubspot", "HUBSPOT", "HubSpot"],
    "zoho": ["zoho", "ZoHo"],
    "pipedrive": ["pipedrive", "PipeDrive"],
    "internal_crm": ["internal_crm", "InternalCRM", "INTERNAL_CRM"],
    "manual_entry": ["manual_entry", "manual", "MANUAL_ENTRY"],
}

SOURCE_PROFILE = {
    "salesforce": {"missing": 0.72, "null": 0.95, "invalid": 0.80, "casing": 0.42, "date": 0.95, "field": 0.75, "type": 0.90, "conflict": 0.85, "stale": 0.50},
    "hubspot": {"missing": 0.95, "null": 1.10, "invalid": 1.00, "casing": 0.95, "date": 1.05, "field": 1.05, "type": 1.00, "conflict": 1.00, "stale": 0.70},
    "zoho": {"missing": 1.00, "null": 1.15, "invalid": 1.10, "casing": 0.88, "date": 1.20, "field": 1.20, "type": 1.10, "conflict": 1.00, "stale": 0.85},
    "pipedrive": {"missing": 0.92, "null": 1.08, "invalid": 1.10, "casing": 1.10, "date": 1.10, "field": 0.95, "type": 1.10, "conflict": 1.35, "stale": 0.80},
    "internal_crm": {"missing": 0.95, "null": 1.22, "invalid": 1.00, "casing": 0.90, "date": 1.15, "field": 1.00, "type": 1.10, "conflict": 1.15, "stale": 1.10},
    "manual_entry": {"missing": 1.08, "null": 1.45, "invalid": 1.55, "casing": 1.00, "date": 1.25, "field": 1.15, "type": 1.25, "conflict": 1.35, "stale": 0.95},
}

STATUS_VARIANTS = ["active", "active", "inactive", "churned"]
LEAD_STATUS_VARIANTS = ["new", "new", "qualified", "contacted", "junk", "converted"]
DEAL_STAGE_VARIANTS = ["prospecting", "qualified", "negotiation", "won", "lost", "contract_sent"]
ACTIVITY_STATUS_VARIANTS = ["done", "done", "pending", "overdue", "cancelled"]

COUNTRY_VARIANTS = ["usa", "us", "egypt", "eg", "united states", "uae", "gb"]
CURRENCY_VARIANTS = ["usd", "usd", "eur", "egp"]

ENTITY_PREFIX = {
    "customers": "cust",
    "contacts": "cont",
    "leads": "lead",
    "deals": "deal",
    "activities": "act",
    "notes": "note",
    "companies": "comp",
}

REFERENCE_FIELDS = {
    "customers": ["company_id", "owner_id"],
    "contacts": ["company_id", "customer_id", "owner_id"],
    "leads": ["company_id", "contact_id", "owner_id"],
    "deals": ["customer_id", "contact_id", "lead_id", "company_id", "owner_id"],
    "activities": ["customer_id", "contact_id", "lead_id", "deal_id", "owner_id"],
    "notes": ["customer_id", "contact_id", "lead_id", "deal_id", "company_id", "owner_id"],
    "companies": ["owner_id"],
}

OPTIONAL_FIELDS = {
    "customers": ["phone", "phone_number", "owner_id", "updated_at", "last_activity_at", "external_id"],
    "contacts": ["company_id", "customer_id", "phone", "phone_number", "updated_at", "linkedin_url"],
    "leads": ["company_id", "contact_id", "phone", "score", "campaign", "updated_at"],
    "deals": ["customer_id", "contact_id", "lead_id", "expected_close_date", "updated_at", "currency"],
    "activities": ["notes", "due_date", "completed_at", "updated_at"],
    "notes": ["title", "content", "updated_at", "entity_type", "entity_id"],
    "companies": ["website", "phone", "employee_count", "updated_at", "address", "billing_address"],
}

FIELD_DRIFT_MAP = {
    "email": "email_address",
    "phone": "phone_number",
    "status": "Status",
    "first_name": "firstName",
    "last_name": "lastName",
    "created_at": "created_date",
    "updated_at": "last_modified",
}


class IdGenerator:
    def __init__(self):
        self.counters = {}

    def new_id(self, entity_name):
        if entity_name not in self.counters:
            self.counters[entity_name] = 1
        val = self.counters[entity_name]
        self.counters[entity_name] = self.counters[entity_name] + 1
        prefix = ENTITY_PREFIX[entity_name]
        return f"{prefix}_{val:06d}"


def utc_now_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def choose_source_system(rnd):
    picks = [
        ("salesforce", 0.19),
        ("hubspot", 0.18),
        ("zoho", 0.15),
        ("pipedrive", 0.16),
        ("internal_crm", 0.17),
        ("manual_entry", 0.15),
    ]
    x = rnd.random()
    running = 0.0
    source_key = "salesforce"
    for key, weight in picks:
        running = running + weight
        if x <= running:
            source_key = key
            break
    variants = SOURCE_NAME_VARIANTS[source_key]
    p = rnd.random()
    if p < 0.86:
        source_label = variants[0]
    elif p < 0.97:
        source_label = variants[min(1, len(variants) - 1)]
    else:
        source_label = variants[min(2, len(variants) - 1)]
    return source_key, source_label


def get_age_factor(age_days):
    if age_days >= 1200:
        return 1.35
    if age_days >= 850:
        return 1.22
    if age_days >= 450:
        return 1.12
    if age_days >= 180:
        return 1.05
    return 1.00


def get_corruption_profile(source_key, entity_name, age_days, rnd):
    profile = copy.deepcopy(SOURCE_PROFILE[source_key])
    age_factor = get_age_factor(age_days)

    for key in list(profile.keys()):
        profile[key] = profile[key] * age_factor

    # Burst 1: bad manual import wave in a historical window.
    if source_key == "manual_entry" and entity_name in ["contacts", "leads", "notes"] and 300 <= age_days <= 900:
        if rnd.random() < 0.24:
            profile["missing"] = profile["missing"] * 1.10
            profile["null"] = profile["null"] * 1.35
            profile["invalid"] = profile["invalid"] * 1.20

    # Burst 2: zoho migration window with schema and date chaos.
    if source_key == "zoho" and 700 <= age_days <= 1300:
        if rnd.random() < 0.26:
            profile["date"] = profile["date"] * 1.35
            profile["field"] = profile["field"] * 1.15

    # Burst 3: pipedrive status/casing spike.
    if source_key == "pipedrive" and entity_name in ["deals", "activities", "leads"] and 200 <= age_days <= 650:
        if rnd.random() < 0.20:
            profile["conflict"] = profile["conflict"] * 1.22
            profile["casing"] = profile["casing"] * 1.10

    # Burst 4: internal crm sync backlog period.
    if source_key == "internal_crm" and age_days >= 400:
        if rnd.random() < 0.20:
            profile["stale"] = profile["stale"] * 1.15
            profile["date"] = profile["date"] * 1.20

    # Small random bad batch in any source/entity.
    if rnd.random() < 0.03:
        for key in list(profile.keys()):
            profile[key] = profile[key] * 1.08

    return profile


def pick_date_format(dt, rnd, messy_ratio=0.03):
    age_days = (utc_now_naive() - dt).days
    old_bonus = 0.0
    if age_days >= 1200:
        old_bonus = 0.31
    elif age_days >= 850:
        old_bonus = 0.25
    elif age_days >= 500:
        old_bonus = 0.18
    elif age_days >= 250:
        old_bonus = 0.10

    effective_ratio = min(0.73, messy_ratio + old_bonus)
    if rnd.random() > effective_ratio:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    mode_pool = ["slash", "timestamp", "sql"]
    if age_days >= 850:
        mode_pool = ["dot", "dot", "dot", "dot", "dot", "slash"]
    elif age_days >= 500:
        mode_pool = ["dot", "dot", "dot", "dot", "slash", "sql", "timestamp"]
    elif age_days >= 250:
        mode_pool = ["dot", "dot", "dot", "slash", "slash", "sql", "timestamp"]

    mode = rnd.choice(mode_pool)
    if mode == "dot":
        return dt.strftime("%Y.%m.%d %H:%M:%S")
    if mode == "slash":
        return dt.strftime("%m/%d/%Y %H:%M")
    if mode == "timestamp":
        return str(int(dt.timestamp()))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def pick_sync_date_format(dt, rnd, messy_ratio=0.03):
    if rnd.random() > messy_ratio:
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    mode = rnd.choice(["slash", "timestamp", "sql"])
    if mode == "slash":
        return dt.strftime("%m/%d/%Y %H:%M")
    if mode == "timestamp":
        return str(int(dt.timestamp()))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def random_created_updated(rnd):
    now = utc_now_naive()
    created = now - timedelta(days=rnd.randint(30, 1600), hours=rnd.randint(0, 23))
    updated = created + timedelta(days=rnd.randint(0, 600), hours=rnd.randint(0, 23))
    if updated > now:
        updated = now - timedelta(days=rnd.randint(0, 15))
    return created, updated


def ugly_case(value, rnd):
    if not isinstance(value, str):
        return value
    mode = rnd.choice(["upper", "lower", "title", "swap", "mixed"])
    if mode == "upper":
        return value.upper()
    if mode == "lower":
        return value.lower()
    if mode == "title":
        return value.title()
    if mode == "swap":
        return value.swapcase()

    chars = []
    for i in range(len(value)):
        c = value[i]
        if c.isalpha() and rnd.random() < 0.5:
            chars.append(c.upper())
        else:
            chars.append(c.lower())
    return "".join(chars)


def make_source_block(rnd, created, updated, source_key, source_label, profile):
    sync_status_values_map = {
        "salesforce": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "failed"],
        "hubspot": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "ok", "FAILED"],
        "zoho": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "failed", "SYNCED"],
        "pipedrive": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "failed", "ok"],
        "internal_crm": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "failed", "SYNCED"],
        "manual_entry": ["synced", "synced", "synced", "synced", "synced", "synced", "synced", "synced", "pending", "failed", "ok", "SYNCED"],
    }
    sync_status_values = sync_status_values_map[source_key]
    base = {
        "source_system": source_label,
        "source_record_id": f"SRC-{rnd.randint(10000, 99999)}",
        "sync_status": rnd.choice(sync_status_values),
        "sync_version": rnd.choice([1, 2, 3, 4, "3", "4", "v2", "v3"]),
        "last_synced_at": pick_sync_date_format(updated - timedelta(days=rnd.randint(0, 45)), rnd, messy_ratio=min(0.16, 0.006 * profile["date"])),
    }

    if rnd.random() < min(0.18, 0.045 * profile["missing"]):
        base.pop("source_record_id", None)

    if rnd.random() < min(0.010, 0.0020 * profile["stale"]):
        stale_date = created - timedelta(days=rnd.randint(60, 180))
        base["last_synced_at"] = pick_sync_date_format(stale_date, rnd, messy_ratio=0.9)
        base["sync_status"] = rnd.choice(["synced", "SYNCED", "ok"])

    return base


def maybe_soft_delete(rec, rnd, updated, delete_rate=0.10, conflict_rate=0.04):
    if rnd.random() < delete_rate:
        deleted_dt = updated + timedelta(days=rnd.randint(1, 80))
        rec["is_deleted"] = rnd.choice([True, "true", 1])
        rec["deleted_at"] = pick_date_format(deleted_dt, rnd)
    elif rnd.random() < conflict_rate:
        # conflicting status on purpose
        rec["is_deleted"] = False
        rec["deleted_at"] = pick_date_format(updated - timedelta(days=rnd.randint(1, 15)), rnd)


def maybe_invalid_email(rec, rnd, rate=0.09):
    keys = ["email", "email_address"]
    chosen = None
    for i in range(len(keys)):
        if keys[i] in rec:
            chosen = keys[i]
            break
    if chosen is None:
        return
    if rnd.random() < rate:
        bad = ["john@", "no-domain.com", "@@badmail", "mary.gmail.com", ""]
        rec[chosen] = rnd.choice(bad)


def maybe_invalid_phone(rec, rnd, rate=0.09):
    keys = ["phone", "phone_number"]
    chosen = None
    for i in range(len(keys)):
        if keys[i] in rec:
            chosen = keys[i]
            break
    if chosen is None:
        return
    if rnd.random() < rate:
        bad = ["123", "N/A", "000-000", "+1 ()", "++2012", "phone missing"]
        rec[chosen] = rnd.choice(bad)


def maybe_field_drift(rec, rnd, rate=0.06, dual_rate=0.30):
    if rnd.random() > rate:
        return

    possible = []
    for k, v in FIELD_DRIFT_MAP.items():
        if k in rec:
            possible.append((k, v))
    if len(possible) == 0:
        return

    old_key, new_key = rnd.choice(possible)
    old_val = rec.get(old_key)

    # Transitional schema drift: sometimes both old and new fields coexist.
    if rnd.random() < dual_rate:
        rec[new_key] = old_val
        if isinstance(old_val, str) and rnd.random() < 0.50:
            rec[old_key] = ugly_case(old_val, rnd)
        return

    rec[new_key] = rec.pop(old_key)


def maybe_type_drift(rec, entity_name, rnd, rate_mult=1.0):
    if entity_name == "deals" and "amount" in rec and rnd.random() < min(0.85, 0.28 * rate_mult):
        if isinstance(rec["amount"], (int, float)):
            rec["amount"] = str(rec["amount"])
        else:
            rec["amount"] = rnd.randint(1000, 100000)

    if entity_name == "companies" and "employee_count" in rec and rnd.random() < min(0.85, 0.22 * rate_mult):
        if isinstance(rec["employee_count"], int):
            low = max(1, rec["employee_count"] - rnd.randint(1, 40))
            high = rec["employee_count"] + rnd.randint(30, 300)
            rec["employee_count"] = f"{low}-{high}"
        else:
            rec["employee_count"] = rnd.randint(5, 2000)

    if entity_name == "leads" and "score" in rec and rnd.random() < min(0.85, 0.22 * rate_mult):
        if isinstance(rec["score"], int):
            rec["score"] = str(rec["score"])
        else:
            rec["score"] = rnd.randint(1, 100)


def maybe_missing_and_null(rec, entity_name, rnd, drop_rate=0.07, null_rate=0.17):
    fields = OPTIONAL_FIELDS.get(entity_name, [])
    for i in range(len(fields)):
        fld = fields[i]
        if fld in rec and rnd.random() < drop_rate:
            rec.pop(fld, None)

    nullable = []
    for key in list(rec.keys()):
        if key not in ["id", "created_at", "created_date", "customer_id", "company_id", "contact_id", "deal_id", "lead_id"]:
            nullable.append(key)
    if len(nullable) > 0 and rnd.random() < null_rate:
        target = rnd.choice(nullable)
        rec[target] = None


def maybe_inconsistent_casing(rec, rnd, rate=0.10):
    keys = ["status", "Status", "currency", "country", "source_system", "lead_status", "stage", "Stage"]
    for i in range(len(keys)):
        key = keys[i]
        if key in rec and isinstance(rec[key], str) and rnd.random() < rate:
            rec[key] = ugly_case(rec[key], rnd)


def add_duplicate_logical_records(records, entity_name, id_gen, rnd):
    if len(records) < 20:
        return records

    duplicate_count = int(len(records) * rnd.uniform(0.06, 0.09))
    picks = rnd.sample(records, duplicate_count)

    for i in range(len(picks)):
        src = picks[i]
        dup = copy.deepcopy(src)
        dup["id"] = id_gen.new_id(entity_name)
        dup["duplicate_of"] = src.get("id")

        if "email" in dup and isinstance(dup["email"], str):
            dup["email"] = dup["email"].replace("@", ".dup@")
        if "email_address" in dup and isinstance(dup["email_address"], str):
            dup["email_address"] = dup["email_address"].replace("@", ".old@")
        if "phone" in dup and isinstance(dup["phone"], str):
            dup["phone"] = dup["phone"] + " ext " + str(rnd.randint(10, 99))
        if "updated_at" in dup:
            dup["updated_at"] = pick_date_format(utc_now_naive() - timedelta(days=rnd.randint(1, 90)), rnd)

        records.append(dup)

    return records


def maybe_nested_vs_flat_contact(rec, rnd):
    if rnd.random() < 0.16:
        first = rec.get("first_name") or rec.get("firstName")
        last = rec.get("last_name") or rec.get("lastName")
        email = rec.get("email") or rec.get("email_address")
        rec["contact"] = {
            "first_name": first,
            "last_name": last,
            "email": email,
        }
        if rnd.random() < 0.55:
            rec.pop("first_name", None)
            rec.pop("firstName", None)


def random_owner_id(rnd):
    return rnd.choice([
        "own_001",
        "OWN_002",
        "owner_03",
        "sales_17",
        "rep_99",
        "manual_queue",
    ])


def generate_companies(fake, rnd, id_gen, count):
    arr = []
    for _ in range(count):
        cid = id_gen.new_id("companies")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "companies", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        rec = {
            "id": cid,
            "company_id": cid,
            "name": fake.company(),
            "industry": rnd.choice(["SaaS", "Manufacturing", "retail", "FinTech", "HealthCare", "Logistics"]),
            "employee_count": rnd.randint(5, 5000),
            "country": rnd.choice(COUNTRY_VARIANTS),
            "website": fake.url(),
            "phone": fake.phone_number(),
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
        }

        if rnd.random() < 0.40:
            rec["address"] = {
                "line1": fake.street_address(),
                "city": fake.city(),
                "state": fake.state_abbr(),
                "zip": fake.postcode(),
                "country": rnd.choice(COUNTRY_VARIANTS),
            }
        else:
            rec["street"] = fake.street_address()
            rec["city"] = fake.city()
            rec["state"] = fake.state_abbr()
            rec["postal_code"] = fake.postcode()

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        if rnd.random() < 0.09:
            rec["Industry"] = rec.pop("industry")

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_invalid_phone(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_type_drift(rec, "companies", rnd, rate_mult=profile["type"])
        maybe_missing_and_null(rec, "companies", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "companies", id_gen, rnd)


def generate_customers(fake, rnd, id_gen, count, company_ids):
    arr = []
    for _ in range(count):
        cid = id_gen.new_id("customers")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "customers", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])
        chosen_company = rnd.choice(company_ids)

        rec = {
            "id": cid,
            "customer_id": cid,
            "external_id": f"EXT-{rnd.randint(1000, 9999)}",
            "name": fake.company(),
            "email": fake.company_email(),
            "phone": fake.phone_number(),
            "status": rnd.choice(STATUS_VARIANTS),
            "company_id": chosen_company,
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
            "last_activity_at": pick_date_format(updated - timedelta(days=rnd.randint(0, 120)), rnd, messy_ratio=date_ratio),
            "country": rnd.choice(COUNTRY_VARIANTS),
        }

        if rnd.random() < 0.15:
            rec["status"] = rnd.choice(["active", "inactive"])
            rec["is_deleted"] = True

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_invalid_email(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_invalid_phone(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "customers", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "customers", id_gen, rnd)


def generate_contacts(fake, rnd, id_gen, count, customer_ids, company_ids):
    arr = []
    for _ in range(count):
        cid = id_gen.new_id("contacts")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "contacts", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        first = fake.first_name()
        last = fake.last_name()

        rec = {
            "id": cid,
            "contact_id": cid,
            "first_name": first,
            "last_name": last,
            "full_name": first + " " + last,
            "email": fake.email(),
            "phone": fake.phone_number(),
            "job_title": fake.job(),
            "company_id": rnd.choice(company_ids),
            "customer_id": rnd.choice(customer_ids),
            "owner_id": random_owner_id(rnd),
            "status": rnd.choice(STATUS_VARIANTS),
            "linkedin_url": "https://linkedin.com/in/" + fake.user_name(),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
        }

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        if rnd.random() < 0.10:
            rec["firstName"] = rec.pop("first_name")
        if rnd.random() < 0.10:
            rec["lastName"] = rec.pop("last_name")

        maybe_nested_vs_flat_contact(rec, rnd)
        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_invalid_email(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_invalid_phone(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "contacts", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "contacts", id_gen, rnd)


def generate_leads(fake, rnd, id_gen, count, company_ids, contact_ids):
    arr = []
    for _ in range(count):
        lid = id_gen.new_id("leads")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "leads", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        rec = {
            "id": lid,
            "lead_id": lid,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "contact_name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "company_name": fake.company(),
            "company_id": rnd.choice(company_ids),
            "contact_id": rnd.choice(contact_ids),
            "lead_status": rnd.choice(LEAD_STATUS_VARIANTS),
            "score": rnd.randint(1, 100),
            "campaign": rnd.choice(["webinar", "adwords", "referral", "event", "cold_list"]),
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
        }

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        if rnd.random() < 0.12:
            rec["status"] = rnd.choice(["converted", "lost", "new"])

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_invalid_email(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_invalid_phone(rec, rnd, rate=min(0.55, 0.09 * profile["invalid"]))
        maybe_type_drift(rec, "leads", rnd, rate_mult=profile["type"])
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "leads", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "leads", id_gen, rnd)


def generate_deals(fake, rnd, id_gen, count, customer_ids, contact_ids, lead_ids, company_ids):
    arr = []
    for _ in range(count):
        did = id_gen.new_id("deals")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "deals", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        amount = round(rnd.uniform(1500, 240000), 2)
        rec = {
            "id": did,
            "deal_id": did,
            "deal_name": fake.catch_phrase(),
            "amount": amount,
            "currency": rnd.choice(CURRENCY_VARIANTS),
            "probability": rnd.choice([20, 40, 60, 80, 100, "90", "35"]),
            "stage": rnd.choice(DEAL_STAGE_VARIANTS),
            "status": rnd.choice(["open", "Open", "WON", "lost"]),
            "customer_id": rnd.choice(customer_ids),
            "contact_id": rnd.choice(contact_ids),
            "lead_id": rnd.choice(lead_ids),
            "company_id": rnd.choice(company_ids),
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
            "expected_close_date": pick_date_format(updated + timedelta(days=rnd.randint(5, 120)), rnd, messy_ratio=date_ratio),
        }

        if rnd.random() < 0.22:
            rec["contact"] = {
                "id": rec["contact_id"],
                "name": fake.name(),
                "email": fake.email(),
            }

        if rnd.random() < 0.09:
            rec["Stage"] = rec.pop("stage")

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_type_drift(rec, "deals", rnd, rate_mult=profile["type"])
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "deals", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "deals", id_gen, rnd)


def generate_activities(fake, rnd, id_gen, count, customer_ids, contact_ids, lead_ids, deal_ids):
    arr = []
    activity_type_values = ["call", "CALL", "email", "meeting", "task", "demo"]

    for _ in range(count):
        aid = id_gen.new_id("activities")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "activities", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        rec = {
            "id": aid,
            "activity_id": aid,
            "type": rnd.choice(activity_type_values),
            "subject": fake.sentence(nb_words=6),
            "status": rnd.choice(ACTIVITY_STATUS_VARIANTS),
            "priority": rnd.choice(["low", "medium", "HIGH", "urgent"]),
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
            "due_date": pick_date_format(updated + timedelta(days=rnd.randint(0, 20)), rnd, messy_ratio=date_ratio),
            "completed_at": None,
        }

        rel_choice = rnd.choice(["deal", "contact", "lead", "customer"])
        if rel_choice == "deal":
            rec["deal_id"] = rnd.choice(deal_ids)
        elif rel_choice == "contact":
            rec["contact_id"] = rnd.choice(contact_ids)
        elif rel_choice == "lead":
            rec["lead_id"] = rnd.choice(lead_ids)
        else:
            rec["customer_id"] = rnd.choice(customer_ids)

        if rnd.random() < 0.35:
            rec["notes"] = fake.sentence(nb_words=12)

        if rnd.random() < 0.45:
            rec["completed_at"] = pick_date_format(updated - timedelta(days=rnd.randint(0, 5)), rnd, messy_ratio=date_ratio)

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "activities", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "activities", id_gen, rnd)


def generate_notes(fake, rnd, id_gen, count, ids_by_entity):
    arr = []
    note_targets = ["customer", "contact", "lead", "deal", "company"]
    target_pool_map = {
        "customer": "customers",
        "contact": "contacts",
        "lead": "leads",
        "deal": "deals",
        "company": "companies",
    }

    for _ in range(count):
        nid = id_gen.new_id("notes")
        created, updated = random_created_updated(rnd)
        age_days = (utc_now_naive() - created).days
        source_key, source_label = choose_source_system(rnd)
        profile = get_corruption_profile(source_key, "notes", age_days, rnd)
        date_ratio = min(0.16, 0.010 * profile["date"])

        target = rnd.choice(note_targets)
        pool_name = target_pool_map[target]
        pool = ids_by_entity.get(pool_name, [])
        selected_id = rnd.choice(pool)

        rec = {
            "id": nid,
            "note_id": nid,
            "title": fake.sentence(nb_words=5),
            "content": fake.paragraph(nb_sentences=3),
            "entity_type": target,
            "entity_id": selected_id,
            "owner_id": random_owner_id(rnd),
            "created_at": pick_date_format(created, rnd, messy_ratio=date_ratio),
            "updated_at": pick_date_format(updated, rnd, messy_ratio=date_ratio),
        }

        if rnd.random() < 0.14:
            rec["content"] = ""
        if rnd.random() < 0.10:
            rec["title"] = None

        rec.update(make_source_block(rnd, created, updated, source_key, source_label, profile))

        maybe_soft_delete(rec, rnd, updated, delete_rate=min(0.35, 0.10 * profile["conflict"]), conflict_rate=min(0.22, 0.04 * profile["conflict"]))
        maybe_field_drift(rec, rnd, rate=min(0.26, 0.034 * profile["field"]), dual_rate=min(0.52, 0.20 * profile["field"]))
        maybe_missing_and_null(rec, "notes", rnd, drop_rate=min(0.24, 0.044 * profile["missing"]), null_rate=min(0.38, 0.16 * profile["null"]))
        maybe_inconsistent_casing(rec, rnd, rate=min(0.11, 0.028 * profile["casing"]))

        arr.append(rec)

    return add_duplicate_logical_records(arr, "notes", id_gen, rnd)


def inject_orphans(data_by_entity, rnd):
    pools = {}
    for entity_name in data_by_entity:
        ids = []
        arr = data_by_entity[entity_name]
        for i in range(len(arr)):
            if "id" in arr[i]:
                ids.append(arr[i]["id"])
        pools[entity_name] = set(ids)

    for entity_name, arr in data_by_entity.items():
        for i in range(len(arr)):
            rec = arr[i]
            for fld in REFERENCE_FIELDS.get(entity_name, []):
                if fld not in rec:
                    continue
                if rnd.random() < 0.014:
                    rec[fld] = "orphan_" + str(rnd.randint(100000, 999999))


def get_expected_entity(field_name):
    mapping = {
        "company_id": "companies",
        "customer_id": "customers",
        "contact_id": "contacts",
        "lead_id": "leads",
        "deal_id": "deals",
    }
    return mapping.get(field_name)


def repair_relationships(data_by_entity, rnd):
    pools = {}
    for entity_name in data_by_entity:
        ids = []
        for rec in data_by_entity[entity_name]:
            rec_id = rec.get("id")
            if rec_id:
                ids.append(rec_id)
        pools[entity_name] = ids

    for entity_name in data_by_entity:
        for rec in data_by_entity[entity_name]:
            for fld in REFERENCE_FIELDS.get(entity_name, []):
                if fld not in rec or rec[fld] in [None, ""]:
                    continue
                if fld == "owner_id":
                    continue

                expected = get_expected_entity(fld)
                if not expected:
                    continue

                current = rec[fld]
                target_pool = pools.get(expected, [])
                if len(target_pool) == 0:
                    continue

                if current not in target_pool:
                    if rnd.random() < 0.90:
                        rec[fld] = rnd.choice(target_pool)


def mutate_for_older_version(records, entity_name, rnd, drop_boost=0.0, age_days=250):
    out = []
    for i in range(len(records)):
        rec = copy.deepcopy(records[i])
        updated_dt = None

        date_messiness = min(0.05, 0.012 + (0.25 * drop_boost))

        if "updated_at" in rec and isinstance(rec["updated_at"], str):
            old_dt = utc_now_naive() - timedelta(days=age_days + rnd.randint(0, 320))
            rec["updated_at"] = pick_date_format(old_dt, rnd, messy_ratio=date_messiness)
            updated_dt = old_dt

        if "created_at" in rec and isinstance(rec["created_at"], str):
            older = utc_now_naive() - timedelta(days=age_days + rnd.randint(300, 1200))
            rec["created_at"] = pick_date_format(older, rnd, messy_ratio=date_messiness)

        if "last_synced_at" in rec:
            if rnd.random() < 0.78:
                sync_old = utc_now_naive() - timedelta(days=rnd.randint(0, 45))
            elif updated_dt is not None and rnd.random() < 0.90:
                sync_old = updated_dt - timedelta(days=rnd.randint(0, 35))
            else:
                sync_old = utc_now_naive() - timedelta(days=age_days + rnd.randint(40, 500))
            rec["last_synced_at"] = pick_sync_date_format(sync_old, rnd, messy_ratio=date_messiness)

        if "sync_status" in rec and rnd.random() < 0.92:
            rec["sync_status"] = rnd.choice(["synced", "synced", "synced", "SYNCED", "ok"])

        fields = OPTIONAL_FIELDS.get(entity_name, [])
        for j in range(len(fields)):
            f = fields[j]
            if f in rec and rnd.random() < min(0.30, 0.06 + (0.55 * drop_boost)):
                rec.pop(f, None)

        if rnd.random() < (0.02 + (0.40 * drop_boost)):
            rec.pop("source_record_id", None)

        if rnd.random() < min(0.34, 0.12 + drop_boost):
            maybe_field_drift(rec, rnd, rate=min(0.20, 0.055 + drop_boost), dual_rate=0.30)

        if rnd.random() < min(0.60, 0.20 + drop_boost):
            maybe_type_drift(rec, entity_name, rnd, rate_mult=1.25 + drop_boost)

        if rnd.random() < min(0.22, 0.06 + drop_boost):
            maybe_inconsistent_casing(rec, rnd, rate=min(0.10, 0.035 + (0.50 * drop_boost)))

        if rnd.random() < min(0.20, 0.06 + drop_boost):
            maybe_missing_and_null(rec, entity_name, rnd, drop_rate=min(0.22, 0.05 + (0.50 * drop_boost)), null_rate=min(0.36, 0.17 + drop_boost))

        # Older snapshots accumulate status drift and conflicting states over time.
        if rnd.random() < min(0.24, 0.09 + drop_boost):
            status_key = None
            if "status" in rec:
                status_key = "status"
            elif "Status" in rec:
                status_key = "Status"
            if status_key:
                rec[status_key] = rnd.choice(["ACTIVE", "active", "Active", "closed", "lost", "pending", "UNKNOWN"])

        if rnd.random() < min(0.014, 0.005 + drop_boost):
            rec["sync_status"] = rnd.choice(["FAILED", "failed", "pending", "synced", "synced", "SYNCED"])

        out.append(rec)

    return out


def build_versions(v3_data, rnd):
    v2 = {}
    v1 = {}

    for entity_name in ENTITIES:
        full = v3_data[entity_name]

        keep_v2 = int(len(full) * rnd.uniform(0.74, 0.84))
        keep_v1 = int(keep_v2 * rnd.uniform(0.65, 0.78))

        sample_v2 = rnd.sample(full, keep_v2)
        sample_v1 = rnd.sample(sample_v2, keep_v1)

        v2[entity_name] = mutate_for_older_version(sample_v2, entity_name, rnd, drop_boost=0.05, age_days=320)
        v1[entity_name] = mutate_for_older_version(sample_v1, entity_name, rnd, drop_boost=0.10, age_days=620)

    repair_relationships(v2, rnd)
    repair_relationships(v1, rnd)
    inject_orphans(v2, rnd)
    inject_orphans(v1, rnd)

    return {"v1": v1, "v2": v2, "v3": v3_data}


def save_data(data_root, versioned_data):
    for version in VERSIONS:
        version_dir = data_root / version
        version_dir.mkdir(parents=True, exist_ok=True)
        for entity_name in ENTITIES:
            out_path = version_dir / f"{entity_name}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(versioned_data[version][entity_name], f, indent=2, ensure_ascii=False)


def summarize(versioned_data):
    print("Generated record counts")
    for version in VERSIONS:
        print("-" * 40)
        print(version)
        for entity_name in ENTITIES:
            print(f"  {entity_name}: {len(versioned_data[version][entity_name])}")


def generate_dataset(seed, target_root):
    rnd = random.Random(seed)
    fake = Faker()
    fake.seed_instance(seed)
    id_gen = IdGenerator()

    companies = generate_companies(fake, rnd, id_gen, V3_COUNTS["companies"])
    company_ids = [r["id"] for r in companies]

    customers = generate_customers(fake, rnd, id_gen, V3_COUNTS["customers"], company_ids)
    customer_ids = [r["id"] for r in customers]

    contacts = generate_contacts(fake, rnd, id_gen, V3_COUNTS["contacts"], customer_ids, company_ids)
    contact_ids = [r["id"] for r in contacts]

    leads = generate_leads(fake, rnd, id_gen, V3_COUNTS["leads"], company_ids, contact_ids)
    lead_ids = [r["id"] for r in leads]

    deals = generate_deals(fake, rnd, id_gen, V3_COUNTS["deals"], customer_ids, contact_ids, lead_ids, company_ids)
    deal_ids = [r["id"] for r in deals]

    activities = generate_activities(fake, rnd, id_gen, V3_COUNTS["activities"], customer_ids, contact_ids, lead_ids, deal_ids)

    ids_by_entity = {
        "customers": customer_ids,
        "contacts": contact_ids,
        "leads": lead_ids,
        "deals": deal_ids,
        "companies": company_ids,
    }
    notes = generate_notes(fake, rnd, id_gen, V3_COUNTS["notes"], ids_by_entity)

    v3_data = {
        "customers": customers,
        "contacts": contacts,
        "leads": leads,
        "deals": deals,
        "activities": activities,
        "notes": notes,
        "companies": companies,
    }

    inject_orphans(v3_data, rnd)

    versioned = build_versions(v3_data, rnd)
    save_data(target_root, versioned)
    summarize(versioned)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate intentionally messy CRM datasets for v1/v2/v3.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--data-root",
        type=str,
        default="fastapi-crm-api/data",
        help="Target data folder that contains v1/v2/v3",
    )

    args = parser.parse_args()
    data_root = Path(args.data_root)
    generate_dataset(args.seed, data_root)
