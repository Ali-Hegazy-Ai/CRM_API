"""
Live mutation engine with persisted CDC event logging for the CRM API.

This module keeps the loaded dataset "live" by incrementally creating and mutating
records in memory, while writing every change to an append-only SQLite event log.
"""

import asyncio
import copy
import json
import os
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from cdc_store import cdc_store
from data_loader import data_loader

try:
    from behavior_extractor import extract_behavior_profile, profile_to_stream_settings
except Exception:  # pragma: no cover - fallback keeps stream engine resilient.
    extract_behavior_profile = None
    profile_to_stream_settings = None


LIVE_VERSION = "v3"
MAX_CHANGE_LOG = 800
MAX_ENTITY_RECORDS = {
    "customers": 3500,
    "leads": 3500,
    "activities": 7000,
}

# Live data is based on the existing loader cache. We mutate only v3 incrementally.
DATA_STORE: Dict[str, Dict[str, List[Dict[str, Any]]]] = data_loader.cache
CHANGE_LOG: List[Dict[str, Any]] = []


_ENTITY_CONFIG = {
    "customers": {"prefix": "cust_", "id_field": "customer_id", "singular": "customer"},
    "leads": {"prefix": "lead_", "id_field": "lead_id", "singular": "lead"},
    "activities": {"prefix": "act_", "id_field": "activity_id", "singular": "activity"},
    "deals": {"prefix": "deal_", "id_field": "deal_id", "singular": "deal"},
}

_SOURCE_WEIGHTS = {
    "salesforce": 0.24,
    "hubspot": 0.20,
    "zoho": 0.16,
    "pipedrive": 0.14,
    "internal_crm": 0.14,
    "manual_entry": 0.12,
}

_SOURCE_PROFILE = {
    "salesforce": {"invalid_email": 0.01, "missing_field": 0.03, "null_field": 0.02, "casing": 0.03, "broken_ref": 0.01, "stale": 0.04},
    "hubspot": {"invalid_email": 0.02, "missing_field": 0.05, "null_field": 0.03, "casing": 0.05, "broken_ref": 0.02, "stale": 0.06},
    "zoho": {"invalid_email": 0.03, "missing_field": 0.07, "null_field": 0.05, "casing": 0.07, "broken_ref": 0.02, "stale": 0.08},
    "pipedrive": {"invalid_email": 0.04, "missing_field": 0.08, "null_field": 0.06, "casing": 0.08, "broken_ref": 0.03, "stale": 0.09},
    "internal_crm": {"invalid_email": 0.05, "missing_field": 0.09, "null_field": 0.07, "casing": 0.08, "broken_ref": 0.03, "stale": 0.10},
    "manual_entry": {"invalid_email": 0.09, "missing_field": 0.16, "null_field": 0.12, "casing": 0.14, "broken_ref": 0.06, "stale": 0.16},
}

_FIRST_NAMES = [
    "Ava", "Mia", "Ethan", "Liam", "Noah", "Emma", "Nora", "Layla", "Omar", "Sami",
    "Ivy", "Luca", "Mason", "James", "Amir", "Maya", "Zara", "Adam", "Hana", "Lina",
]

_LAST_NAMES = [
    "Parker", "Nguyen", "Ali", "Brown", "Santos", "Khan", "Hassan", "Carter", "Lopez", "Murphy",
    "Reyes", "Cole", "Jensen", "Price", "Turner", "Shaw", "Nash", "Wells", "Hayes", "Brooks",
]

_COMPANY_SUFFIX = [
    "Group", "Systems", "Labs", "Partners", "Solutions", "Logistics", "Consulting", "Holdings",
]

_EMAIL_DOMAINS = ["example.com", "company.io", "mailhub.net", "acme.org", "crmco.com"]

_CUSTOMER_STATUS = ["active", "inactive", "churned"]
_LEAD_STATUS = ["new", "contacted", "qualified", "converted", "disqualified"]
_ACTIVITY_STATUS = ["pending", "done", "overdue", "cancelled"]
_ACTIVITY_TYPE = ["call", "email", "meeting", "task", "demo"]
_ACTIVITY_PRIORITY = ["low", "medium", "high", "urgent"]
_DEAL_STAGES = ["prospecting", "qualified", "negotiation", "contract_sent", "won", "lost"]
_DEAL_STATUS = ["open", "won", "lost"]

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y.%m.%d %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]

_COMPANY_POOL = [
    "Apex Technologies",
    "Silver Ventures",
    "Blue Harbor Systems",
    "Summit Analytics",
    "Northstar Dynamics",
    "Cedar Point Labs",
    "Nimbus Industrial",
    "Atlas Retail Group",
    "Beacon Logistics",
    "Evergreen Capital",
]

_ALLOWED_STATUS = {
    "customers": {"active", "inactive", "churned"},
    "leads": {"new", "contacted", "qualified", "converted", "disqualified"},
    "activities": {"pending", "done", "overdue", "cancelled"},
    "deals": {"open", "won", "lost"},
}

_DEFAULT_STATUS = {
    "customers": "active",
    "leads": "new",
    "activities": "pending",
    "deals": "open",
}

_COUNTRY_ALIASES = {
    "us": "US",
    "usa": "US",
    "united states": "US",
    "gb": "GB",
    "uk": "GB",
    "united kingdom": "GB",
    "eg": "EG",
    "egypt": "EG",
    "ae": "AE",
    "uae": "AE",
    "united arab emirates": "AE",
}

_NONSENSE_STRINGS = {
    "phone missing",
    "000-000",
    "000000",
    "0000000000",
    "none",
    "null",
    "n/a",
    "na",
}

_DATE_FIELDS = [
    "created_at",
    "created_date",
    "updated_at",
    "last_activity_at",
    "due_date",
    "completed_at",
    "deleted_at",
    "expected_close_date",
    "last_synced_at",
]


_TASKS: List[asyncio.Task] = []
_STOP_EVENT = asyncio.Event()
_LOCK = asyncio.Lock()
_EVENT_SEQUENCE = 0

_CREATION_PATTERN = {"name": "normal", "remaining": 0, "source": None}
_MUTATION_PATTERN = {"name": "normal", "remaining": 0, "source": None}

LATE_ARRIVAL_CREATE_RATE = 0.18
LATE_UPDATE_PICK_RATE = 0.34
PARTIAL_UPDATE_EVENT_RATE = 0.24
DUPLICATE_EVENT_RATE = 0.10

_ID_COUNTERS = {entity: 0 for entity in _ENTITY_CONFIG}
_USED_IDS = {entity: set() for entity in _ENTITY_CONFIG}

_STREAM_DYNAMICS: Dict[str, float] = {
    "burst_probability": 0.14,
    "silence_probability": 0.08,
    "out_of_order_probability": 0.07,
    "activity_event_probability": 0.28,
    "lead_convert_probability": 0.16,
    "lead_stall_probability": 0.30,
    "deal_stall_probability": 0.28,
    "deal_close_probability": 0.18,
    "deal_disappear_probability": 0.03,
    "burst_batch_min": 2,
    "burst_batch_max": 6,
    "silence_min_seconds": 2.0,
    "silence_max_seconds": 9.0,
}

_STREAM_BEHAVIOR_PROFILE: Dict[str, Any] = {}


def _behavior_csv_candidates() -> List[str]:
    candidates: List[str] = []
    env_path = os.getenv("CRM_BEHAVIOR_CSV")
    if env_path:
        candidates.append(env_path)

    base_dir = os.path.dirname(os.path.dirname(__file__))
    candidates.append(os.path.join(base_dir, "scripts", "exports", "ali.csv"))
    candidates.append(os.path.join(base_dir, "scripts", "exports", "crm_behavioral_v3_flat.csv"))
    candidates.append(os.path.join(base_dir, "scripts", "exports", "customers_realistic_v3.csv"))

    unique: List[str] = []
    seen = set()
    for candidate in candidates:
        normalized = os.path.abspath(candidate)
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
    return unique


def _load_stream_dynamics_profile() -> None:
    global _STREAM_BEHAVIOR_PROFILE

    if extract_behavior_profile is None or profile_to_stream_settings is None:
        return

    for candidate in _behavior_csv_candidates():
        if not os.path.isfile(candidate):
            continue

        profile = extract_behavior_profile(candidate)
        if not isinstance(profile, dict):
            continue

        settings = profile_to_stream_settings(profile)
        if not isinstance(settings, dict):
            continue

        for key, value in settings.items():
            if isinstance(value, (int, float)):
                _STREAM_DYNAMICS[key] = float(value)

        _STREAM_BEHAVIOR_PROFILE = {
            "csv_path": candidate,
            "profile": profile,
        }
        return


async def _sleep_with_stream_dynamics(base_low: float, base_high: float) -> None:
    if random.random() < _STREAM_DYNAMICS["silence_probability"]:
        await asyncio.sleep(random.uniform(_STREAM_DYNAMICS["silence_min_seconds"], _STREAM_DYNAMICS["silence_max_seconds"]))
        return

    if random.random() < _STREAM_DYNAMICS["burst_probability"]:
        await asyncio.sleep(random.uniform(0.08, 0.35))
        return

    await asyncio.sleep(random.uniform(base_low, base_high))


def _entity_can_grow(entity: str) -> bool:
    limit = MAX_ENTITY_RECORDS.get(entity)
    if limit is None:
        return True

    current_count = len(DATA_STORE.get(LIVE_VERSION, {}).get(entity, []))
    return current_count < limit


def _clamp_probability(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if value > 0:
            return datetime.fromtimestamp(float(value), tz=timezone.utc)
        return None

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    if raw.isdigit():
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)

    try:
        iso_raw = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(iso_raw)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for pattern in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, pattern)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


def _record_age_days(record: Dict[str, Any]) -> int:
    created_value = record.get("created_at")
    if created_value is None:
        created_value = record.get("created_date")
    if created_value is None:
        created_value = record.get("updated_at")

    parsed = _parse_datetime(created_value)
    if parsed is None:
        return 90

    delta = datetime.now(timezone.utc) - parsed
    return max(0, int(delta.total_seconds() / 86400))


def _record_stale_days(record: Dict[str, Any]) -> int:
    last_sync_value = record.get("last_synced_at")
    if last_sync_value is None:
        last_sync_value = record.get("updated_at")

    parsed = _parse_datetime(last_sync_value)
    if parsed is None:
        return 30

    delta = datetime.now(timezone.utc) - parsed
    return max(0, int(delta.total_seconds() / 86400))


def _age_multiplier(age_days: int) -> float:
    if age_days <= 30:
        return 0.75
    if age_days <= 180:
        return 1.0
    if age_days <= 365:
        return 1.22
    if age_days <= 730:
        return 1.45
    return 1.7


def _source_cleanliness(source: str) -> float:
    source_key = source.lower()
    profile_map = {
        "salesforce": 0.75,
        "hubspot": 0.95,
        "zoho": 1.1,
        "pipedrive": 1.15,
        "internal_crm": 1.25,
        "manual_entry": 1.5,
    }
    return profile_map.get(source_key, 1.1)


def _apply_dirty_evolution(record: Dict[str, Any], entity: str, source: str) -> None:
    profile = _source_profile(source)
    age_days = _record_age_days(record)
    stale_days = _record_stale_days(record)

    age_factor = _age_multiplier(age_days)
    stale_factor = 1.0 + min(0.8, stale_days / 220.0)
    source_factor = _source_cleanliness(source)

    decay_optional_fields = {
        "customers": ["external_id", "phone", "owner_id", "source_record_id", "last_activity_at"],
        "leads": ["campaign", "phone", "owner_id", "source_record_id", "contact_id"],
        "activities": ["notes", "owner_id", "completed_at", "source_record_id"],
        "deals": ["expected_close_date", "contact", "owner_id", "source_record_id", "currency"],
    }

    options = decay_optional_fields.get(entity, [])

    missing_chance = _clamp_probability(
        profile["missing_field"] * age_factor * source_factor * 0.45 + (stale_days / 1500.0)
    )
    null_chance = _clamp_probability(
        profile["null_field"] * age_factor * source_factor * 0.55 + (stale_days / 1800.0)
    )
    casing_chance = _clamp_probability(profile["casing"] * age_factor * source_factor * 0.65)
    stale_sync_chance = _clamp_probability(profile["stale"] * stale_factor * source_factor * 0.7)

    if options and random.random() < missing_chance:
        remove_field = random.choice(options)
        record.pop(remove_field, None)

    if options and random.random() < null_chance:
        null_field = random.choice(options)
        record[null_field] = None

    if random.random() < casing_chance:
        for field_name in ["source_system", "type", "priority"]:
            if field_name in record and isinstance(record.get(field_name), str):
                record[field_name] = _random_case(record[field_name])

    if random.random() < stale_sync_chance:
        record["sync_status"] = random.choices(
            ["pending", "failed", "ok", "synced"],
            weights=[0.35, 0.3, 0.2, 0.15],
            k=1,
        )[0]
        record["last_synced_at"] = _past_iso(20, 220)


def _decrement_pattern(pattern: Dict[str, Any]) -> None:
    if pattern["remaining"] > 0:
        pattern["remaining"] -= 1
    if pattern["remaining"] <= 0:
        pattern["name"] = "normal"
        pattern["remaining"] = 0
        pattern["source"] = None


def _maybe_start_creation_pattern() -> None:
    if _CREATION_PATTERN["remaining"] > 0:
        return
    if random.random() >= 0.14:
        return

    mode = random.choices(
        ["lead_campaign_burst", "activity_burst"],
        weights=[0.58, 0.42],
        k=1,
    )[0]
    _CREATION_PATTERN["name"] = mode
    _CREATION_PATTERN["remaining"] = random.randint(3, 7)

    if mode == "lead_campaign_burst":
        _CREATION_PATTERN["source"] = random.choice(["hubspot", "manual_entry", "internal_crm"])
    else:
        _CREATION_PATTERN["source"] = random.choice(["salesforce", "internal_crm", "manual_entry"])


def _maybe_start_mutation_pattern() -> None:
    if _MUTATION_PATTERN["remaining"] > 0:
        return
    if random.random() >= 0.13:
        return

    mode = random.choices(
        ["pipeline_shift", "sync_batch"],
        weights=[0.52, 0.48],
        k=1,
    )[0]
    _MUTATION_PATTERN["name"] = mode
    _MUTATION_PATTERN["remaining"] = random.randint(2, 5)
    _MUTATION_PATTERN["source"] = _choose_source()


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _past_iso(min_days: int = 0, max_days: int = 30) -> str:
    days = random.randint(min_days, max_days)
    seconds = random.randint(0, 86399)
    value = datetime.now(timezone.utc) - timedelta(days=days, seconds=seconds)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _future_iso(min_days: int = 0, max_days: int = 14) -> str:
    days = random.randint(min_days, max_days)
    seconds = random.randint(0, 86399)
    value = datetime.now(timezone.utc) + timedelta(days=days, seconds=seconds)
    return value.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _choose_source() -> str:
    sources = list(_SOURCE_WEIGHTS.keys())
    weights = list(_SOURCE_WEIGHTS.values())
    return random.choices(sources, weights=weights, k=1)[0]


def _normalize_source(raw_source: Any) -> str:
    if not isinstance(raw_source, str):
        return "internal_crm"

    lowered = raw_source.strip().lower()
    if lowered in _SOURCE_PROFILE:
        return lowered
    return "internal_crm"


def _source_profile(source: str) -> Dict[str, float]:
    return _SOURCE_PROFILE.get(source, _SOURCE_PROFILE["internal_crm"])


def _random_case(value: str) -> str:
    if not value:
        return value
    mode = random.choice(["upper", "lower", "title", "swap"])
    if mode == "upper":
        return value.upper()
    if mode == "lower":
        return value.lower()
    if mode == "title":
        return value.title()
    return "".join(ch.upper() if i % 2 == 0 else ch.lower() for i, ch in enumerate(value))


def _source_label(source: str, casing_rate: float) -> str:
    if random.random() < casing_rate:
        return _random_case(source)
    return source


def _random_name_parts() -> Tuple[str, str]:
    return random.choice(_FIRST_NAMES), random.choice(_LAST_NAMES)


def _random_company_name() -> str:
    if random.random() < 0.85:
        return random.choice(_COMPANY_POOL)
    return f"{random.choice(_LAST_NAMES)} {random.choice(_COMPANY_SUFFIX)}"


def _random_hex_id(length: int = 12) -> str:
    alphabet = "0123456789abcdef"
    return "".join(random.choice(alphabet) for _ in range(length))


def _normalize_country_code(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip().lower()
    if not text:
        return None
    return _COUNTRY_ALIASES.get(text)


def _random_phone(country_code: Optional[str] = None) -> Optional[str]:
    code = _normalize_country_code(country_code) or random.choice(["US", "GB", "EG", "AE"])

    if code == "US":
        return f"({random.randint(200, 999)}) {random.randint(100, 999)}-{random.randint(1000, 9999)}"
    if code == "GB":
        return f"+44 {random.randint(1000, 9999)} {random.randint(100000, 999999)}"
    if code == "EG":
        return f"+20 {random.randint(100, 999)} {random.randint(1000000, 9999999)}"
    return f"+971 {random.randint(50, 58)} {random.randint(1000000, 9999999)}"


def _company_domain(company_name: Optional[str]) -> str:
    base = "apextechnologies"
    if isinstance(company_name, str) and company_name.strip():
        cleaned = "".join(ch.lower() for ch in company_name if ch.isalnum())
        if len(cleaned) >= 4:
            base = cleaned
    return f"{base}.com"


def _build_email(first_name: str, last_name: str, company_name: Optional[str] = None) -> str:
    first = "".join(ch.lower() for ch in str(first_name) if ch.isalnum())
    last = "".join(ch.lower() for ch in str(last_name) if ch.isalnum())

    if not first:
        first = "x"
    if not last:
        last = "user"

    local = f"{first[0]}.{last}"
    return f"{local}@{_company_domain(company_name)}"


def _pick_owner_id(source: str) -> Optional[str]:
    if source == "manual_entry" and random.random() < 0.20:
        return None

    owners = data_loader.get_static_data("owners")
    owner_ids = []
    for owner in owners:
        if isinstance(owner, dict):
            owner_id = owner.get("id")
            if owner_id:
                owner_ids.append(owner_id)

    existing_owner_ids = [
        rec.get("owner_id")
        for rec in DATA_STORE.get(LIVE_VERSION, {}).get("customers", [])
        if rec.get("owner_id")
    ]
    owner_ids.extend(existing_owner_ids)

    if not owner_ids:
        return random.choice(["own_001", "OWN_002", "sales_17", "rep_99", "manual_queue"])
    return random.choice(owner_ids)


def _pick_related_id(entity: str, broken_rate: float = 0.02) -> Optional[str]:
    records = DATA_STORE.get(LIVE_VERSION, {}).get(entity, [])
    if records and random.random() >= broken_rate:
        sample = random.choice(records)
        record_id = sample.get("id")
        if record_id:
            return record_id

    return _random_hex_id(12)


def _pick_company_details(broken_rate: float = 0.02) -> Tuple[Optional[str], str]:
    companies = DATA_STORE.get(LIVE_VERSION, {}).get("companies", [])
    if companies and random.random() >= broken_rate:
        company = random.choice(companies)
        company_id = company.get("id") or company.get("company_id")
        company_name = company.get("name") or company.get("legal_name") or _random_company_name()
        return company_id, company_name

    return _random_hex_id(12), _random_company_name()


def _sync_status_for_source(source: str) -> str:
    source_key = _normalize_source(source)
    if source_key == "manual_entry":
        return random.choices(["pending", "failed", "synced", "ok"], weights=[0.35, 0.25, 0.25, 0.15], k=1)[0]
    if source_key in {"pipedrive", "internal_crm"}:
        return random.choices(["synced", "ok", "pending", "failed"], weights=[0.45, 0.2, 0.25, 0.1], k=1)[0]
    return random.choices(["synced", "ok", "pending", "failed"], weights=[0.65, 0.2, 0.12, 0.03], k=1)[0]


def _lead_status_for_source(source: str) -> str:
    source_key = _normalize_source(source)
    if source_key == "manual_entry":
        return random.choices(
            ["new", "contacted", "qualified", "converted", "disqualified"],
            weights=[0.40, 0.28, 0.17, 0.06, 0.09],
            k=1,
        )[0]
    if source_key in {"hubspot", "internal_crm"}:
        return random.choices(
            ["new", "contacted", "qualified", "converted", "disqualified"],
            weights=[0.28, 0.27, 0.25, 0.12, 0.08],
            k=1,
        )[0]
    return random.choices(
        ["new", "contacted", "qualified", "converted", "disqualified"],
        weights=[0.18, 0.24, 0.29, 0.19, 0.10],
        k=1,
    )[0]


def _creation_weights_and_batch() -> Tuple[Dict[str, float], int, Optional[str]]:
    _maybe_start_creation_pattern()

    mode = _CREATION_PATTERN["name"]
    source = _CREATION_PATTERN["source"]

    if mode == "lead_campaign_burst":
        batch = random.randint(2, 5)
        return ({"customers": 0.12, "leads": 0.70, "activities": 0.18}, batch, source)

    if mode == "activity_burst":
        batch = random.randint(2, 4)
        return ({"customers": 0.08, "leads": 0.20, "activities": 0.72}, batch, source)

    batch = 2 if random.random() < 0.16 else 1
    return ({"customers": 0.14, "leads": 0.52, "activities": 0.34}, batch, None)


def _creation_timestamp_for_source(source: str) -> str:
    source_key = _normalize_source(source)

    if random.random() < LATE_ARRIVAL_CREATE_RATE:
        if source_key == "manual_entry":
            return _past_iso(45, 420)
        if source_key == "internal_crm":
            return _past_iso(30, 320)
        if source_key == "hubspot":
            return _past_iso(20, 240)
        return _past_iso(10, 180)

    if source_key == "manual_entry" and random.random() < 0.35:
        return _past_iso(5, 120)
    if source_key == "internal_crm" and random.random() < 0.22:
        return _past_iso(3, 75)
    if source_key == "hubspot" and random.random() < 0.14:
        return _past_iso(2, 30)
    return _now_iso()


def _pick_pattern_filtered_record(
    entity: str,
    source: Optional[str],
    prefer_old: bool = False,
) -> Optional[Dict[str, Any]]:
    records = DATA_STORE.get(LIVE_VERSION, {}).get(entity, [])
    if not records:
        return None

    pool = records

    if source:
        source_key = _normalize_source(source)
        filtered = [
            rec for rec in records
            if _normalize_source(rec.get("source_system")) == source_key
        ]
        if filtered:
            pool = filtered

    if prefer_old and random.random() < LATE_UPDATE_PICK_RATE:
        old_candidates = [
            rec for rec in pool
            if _record_age_days(rec) >= random.randint(120, 540)
        ]
        if old_candidates:
            return random.choice(old_candidates)

    return random.choice(pool)


def _normalize_bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n", ""}:
            return False
    return bool(value)


def _normalize_date_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    parsed = _parse_datetime(value)
    if parsed is None:
        return None

    now_dt = datetime.now(timezone.utc)
    if parsed > now_dt:
        parsed = now_dt

    return parsed.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_phone_value(value: Any, country_hint: Optional[str] = None) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    if text.lower() in _NONSENSE_STRINGS:
        return None

    digits = "".join(ch for ch in text if ch.isdigit())
    if not digits:
        return None

    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"+1-{digits[1:4]}-{digits[4:7]}-{digits[7:11]}"
    if 8 <= len(digits) <= 15:
        return _random_phone(country_hint)

    return None


def _normalize_email_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip().lower()
    if not text:
        return None

    if text in _NONSENSE_STRINGS:
        return None

    if "@" not in text:
        return None

    local, domain = text.split("@", 1)
    local = local.strip()
    domain = domain.strip()

    if not local or not domain:
        return None
    if "." not in domain:
        return None
    if " " in local or " " in domain:
        return None

    return f"{local}@{domain}"


def _sanitize_record(entity: str, record: Dict[str, Any]) -> None:
    if not isinstance(record, dict):
        return

    for key, value in list(record.items()):
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped or stripped.lower() in _NONSENSE_STRINGS:
                record[key] = None
            else:
                record[key] = stripped
        elif isinstance(value, dict):
            for sub_key, sub_value in list(value.items()):
                if isinstance(sub_value, str):
                    sub_text = sub_value.strip()
                    value[sub_key] = sub_text if sub_text else None

    if "country" in record:
        normalized_country = _normalize_country_code(record.get("country"))
        record["country"] = normalized_country or "US"

    for phone_field in ["phone", "phone_number"]:
        if phone_field in record:
            record[phone_field] = _normalize_phone_value(record.get(phone_field), record.get("country"))

    if "email" in record:
        normalized_email = _normalize_email_value(record.get("email"))
        if normalized_email is None:
            first_name = str(record.get("first_name") or "john")
            last_name = str(record.get("last_name") or "smith")
            company_name = record.get("company_name") or record.get("name")
            normalized_email = _build_email(first_name, last_name, str(company_name) if company_name else None)
        record["email"] = normalized_email

    status_values = _ALLOWED_STATUS.get(entity)
    if status_values and "status" in record:
        current_status = str(record.get("status") or "").strip().lower()
        if current_status in status_values:
            record["status"] = current_status
        else:
            record["status"] = _DEFAULT_STATUS.get(entity, "active")

    if entity == "leads":
        for lead_status_field in ["lead_status", "leadStatus"]:
            if lead_status_field in record:
                status_text = str(record.get(lead_status_field) or "").strip().lower()
                if status_text in _ALLOWED_STATUS["leads"]:
                    record[lead_status_field] = status_text
                else:
                    record[lead_status_field] = "new"

    if entity == "deals":
        if "Stage" in record and "stage" not in record:
            record["stage"] = record.pop("Stage")
        if "stage" in record:
            stage_text = str(record.get("stage") or "").strip().lower()
            if stage_text not in _DEAL_STAGES:
                stage_text = "prospecting"
            record["stage"] = stage_text

    if "sync_status" in record and isinstance(record.get("sync_status"), str):
        sync_text = str(record.get("sync_status") or "").strip().lower()
        if sync_text not in {"synced", "ok", "pending", "failed"}:
            sync_text = "pending"
        record["sync_status"] = sync_text

    for date_field in _DATE_FIELDS:
        if date_field in record:
            record[date_field] = _normalize_date_value(record.get(date_field))

    if "is_deleted" in record:
        record["is_deleted"] = _normalize_bool_value(record.get("is_deleted"))
    elif record.get("deleted_at"):
        record["is_deleted"] = True


def _sanitize_live_dataset() -> None:
    version_bucket = DATA_STORE.setdefault(LIVE_VERSION, {})
    for entity_name, records in version_bucket.items():
        if not isinstance(records, list):
            continue
        for record in records:
            if isinstance(record, dict):
                _sanitize_record(entity_name, record)


def _sync_version() -> Any:
    return random.choice([1, 2, 3, 4, "2", "3", "v3"])


def _sync_timestamp(stale_bias: float) -> str:
    if random.random() < stale_bias:
        return _past_iso(10, 180)
    return _past_iso(0, 10)


def _refresh_id_tracking() -> None:
    for entity, config in _ENTITY_CONFIG.items():
        used_ids = set()
        max_counter = 0

        for record in DATA_STORE.get(LIVE_VERSION, {}).get(entity, []):
            record_id = record.get("id")
            if not isinstance(record_id, str):
                continue
            used_ids.add(record_id)

            if record_id.startswith(config["prefix"]):
                tail = record_id[len(config["prefix"]):]
                if tail.isdigit():
                    max_counter = max(max_counter, int(tail))

        _USED_IDS[entity] = used_ids
        _ID_COUNTERS[entity] = max_counter


def _next_primary_id(entity: str) -> str:
    while True:
        candidate = _random_hex_id(12)
        if candidate not in _USED_IDS[entity]:
            _USED_IDS[entity].add(candidate)
            return candidate


def _apply_messiness(record: Dict[str, Any], entity: str, source: str) -> None:
    profile = _source_profile(source)
    source_factor = _source_cleanliness(source)

    optional_fields = {
        "customers": ["external_id", "phone", "owner_id", "source_record_id"],
        "leads": ["campaign", "owner_id", "source_record_id", "phone"],
        "activities": ["notes", "owner_id", "completed_at", "source_record_id"],
        "deals": ["expected_close_date", "owner_id", "source_record_id", "currency"],
    }

    options = optional_fields.get(entity, [])

    if options and random.random() < _clamp_probability(profile["missing_field"] * source_factor * 0.85):
        field_to_drop = random.choice(options)
        if field_to_drop in record:
            record.pop(field_to_drop, None)

    if options and random.random() < _clamp_probability(profile["null_field"] * source_factor * 0.9):
        field_to_null = random.choice(options)
        record[field_to_null] = None

    if "source_system" in record and random.random() < _clamp_probability(profile["casing"] * source_factor):
        record["source_system"] = _source_label(source, 1.0)


def _create_customer(source_override: Optional[str] = None) -> Dict[str, Any]:
    source = _normalize_source(source_override) if source_override else _choose_source()
    profile = _source_profile(source)
    created_value = _creation_timestamp_for_source(source)
    updated_value = _now_iso() if random.random() < 0.72 else created_value

    customer_id = _next_primary_id("customers")
    first_name, last_name = _random_name_parts()
    company_id, company_name = _pick_company_details(profile["broken_ref"])

    record = {
        "id": customer_id,
        "customer_id": customer_id,
        "external_id": f"EXT-{random.randint(1000, 9999)}",
        "name": company_name,
        "email": _build_email(first_name, last_name, company_name),
        "phone": _random_phone("US"),
        "status": random.choice(_CUSTOMER_STATUS),
        "company_id": company_id,
        "owner_id": _pick_owner_id(source),
        "created_at": created_value,
        "updated_at": updated_value,
        "last_activity_at": _past_iso(0, 30) if random.random() < 0.45 else updated_value,
        "country": random.choice(["US", "GB", "EG", "AE"]),
        "source_system": _source_label(source, profile["casing"]),
        "source_record_id": f"SRC-{random.randint(10000, 99999)}",
        "sync_status": _sync_status_for_source(source),
        "sync_version": _sync_version(),
        "last_synced_at": _sync_timestamp(profile["stale"]),
    }

    _apply_messiness(record, "customers", source)
    _sanitize_record("customers", record)
    return record


def _create_lead(source_override: Optional[str] = None) -> Dict[str, Any]:
    source = _normalize_source(source_override) if source_override else _choose_source()
    profile = _source_profile(source)
    created_value = _creation_timestamp_for_source(source)
    updated_value = _now_iso() if random.random() < 0.76 else created_value

    lead_id = _next_primary_id("leads")
    first_name, last_name = _random_name_parts()
    contact_first, contact_last = _random_name_parts()
    company_id, company_name = _pick_company_details(profile["broken_ref"])

    record = {
        "id": lead_id,
        "lead_id": lead_id,
        "first_name": first_name,
        "last_name": last_name,
        "contact_name": f"{contact_first} {contact_last}",
        "email": _build_email(first_name, last_name, company_name),
        "phone": _random_phone("US"),
        "company_name": company_name,
        "company_id": company_id,
        "contact_id": _pick_related_id("contacts", profile["broken_ref"]),
        "lead_status": _lead_status_for_source(source),
        "score": random.randint(1, 100),
        "campaign": random.choice(["webinar", "referral", "paid_search", "event", "outbound"]),
        "owner_id": _pick_owner_id(source),
        "created_at": created_value,
        "updated_at": updated_value,
        "source_system": _source_label(source, profile["casing"]),
        "source_record_id": f"SRC-{random.randint(10000, 99999)}",
        "sync_status": _sync_status_for_source(source),
        "sync_version": _sync_version(),
        "last_synced_at": _sync_timestamp(profile["stale"]),
    }

    _apply_messiness(record, "leads", source)
    _sanitize_record("leads", record)
    return record


def _create_activity(source_override: Optional[str] = None) -> Dict[str, Any]:
    source = _normalize_source(source_override) if source_override else _choose_source()
    profile = _source_profile(source)
    created_value = _creation_timestamp_for_source(source)
    updated_value = _now_iso() if random.random() < 0.8 else created_value

    activity_id = _next_primary_id("activities")
    if source == "manual_entry":
        status = random.choices(_ACTIVITY_STATUS, weights=[0.45, 0.15, 0.3, 0.1], k=1)[0]
    else:
        status = random.choice(_ACTIVITY_STATUS)
    activity_type = random.choice(_ACTIVITY_TYPE)
    due_date = _past_iso(0, 10)

    relation_choices = [
        ("contact_id", "contacts"),
        ("customer_id", "customers"),
        ("lead_id", "leads"),
        ("deal_id", "deals"),
    ]
    relation_field, relation_entity = random.choice(relation_choices)

    record = {
        "id": activity_id,
        "activity_id": activity_id,
        "type": activity_type,
        "subject": random.choice([
            "Follow up with account",
            "Call about renewal",
            "Prepare product demo",
            "Share proposal update",
            "Check implementation timeline",
        ]),
        "status": status,
        "priority": random.choice(_ACTIVITY_PRIORITY),
        "owner_id": _pick_owner_id(source),
        "created_at": created_value,
        "updated_at": updated_value,
        "due_date": due_date,
        "completed_at": updated_value if status == "done" and random.random() < 0.7 else None,
        relation_field: _pick_related_id(relation_entity, profile["broken_ref"]),
        "notes": random.choice([
            "Customer requested pricing clarification.",
            "Waiting on technical feedback.",
            "Left voicemail and sent follow-up email.",
            "Internal handoff needed before next step.",
        ]),
        "source_system": _source_label(source, profile["casing"]),
        "source_record_id": f"SRC-{random.randint(10000, 99999)}",
        "sync_status": _sync_status_for_source(source),
        "sync_version": _sync_version(),
        "last_synced_at": _sync_timestamp(profile["stale"]),
    }

    _apply_messiness(record, "activities", source)
    _sanitize_record("activities", record)
    return record


def _set_update_timestamp(record: Dict[str, Any], source: str) -> None:
    profile = _source_profile(source)
    age_days = _record_age_days(record)
    stale_days = _record_stale_days(record)
    age_factor = _age_multiplier(age_days)
    stale_factor = 1.0 + min(0.8, stale_days / 210.0)

    if random.random() < _clamp_probability(profile["stale"] * 0.22 * age_factor * stale_factor):
        record["updated_at"] = _past_iso(6, 180)
    else:
        record["updated_at"] = _now_iso()


def _pick_deal_stage_field(record: Dict[str, Any]) -> str:
    if "stage" in record:
        return "stage"
    if "Stage" in record:
        return "Stage"
    record["stage"] = random.choice(_DEAL_STAGES)
    return "stage"


def _stage_to_probability(stage: str) -> int:
    table = {
        "prospecting": 20,
        "qualified": 40,
        "negotiation": 65,
        "contract_sent": 80,
        "won": 100,
        "lost": 10,
    }
    return table.get(stage, random.randint(20, 75))


def _apply_pipeline_shift_to_deal(record: Dict[str, Any], source: str, burst_mode: bool = False) -> None:
    stage_field = _pick_deal_stage_field(record)
    current_stage = str(record.get(stage_field) or "prospecting").lower()

    if current_stage in _DEAL_STAGES and random.random() < (0.75 if burst_mode else 0.55):
        stage_index = _DEAL_STAGES.index(current_stage)
        next_index = min(stage_index + random.choice([0, 1, 1, 2]), len(_DEAL_STAGES) - 1)
        next_stage = _DEAL_STAGES[next_index]
    else:
        next_stage = random.choice(_DEAL_STAGES)

    record[stage_field] = next_stage

    if next_stage == "won":
        status_value = "won"
    elif next_stage == "lost":
        status_value = "lost"
    else:
        status_value = "open"

    record["status"] = status_value

    probability = _stage_to_probability(next_stage)
    if random.random() < 0.22:
        record["probability"] = str(probability)
    else:
        record["probability"] = probability


def _mutate_customer(record: Dict[str, Any], source: str) -> None:
    source_factor = _source_cleanliness(source)
    age_factor = _age_multiplier(_record_age_days(record))

    action = random.choices(
        ["status", "email", "sync", "partial", "activity_time"],
        weights=[
            1.0,
            0.9,
            0.9,
            0.65 * source_factor * age_factor,
            1.1,
        ],
        k=1,
    )[0]

    if action == "status":
        record["status"] = random.choice(_CUSTOMER_STATUS)
    elif action == "email":
        first_name, last_name = _random_name_parts()
        company_name = record.get("company_name") or record.get("name")
        record["email"] = _build_email(first_name, last_name, str(company_name) if company_name else None)
    elif action == "sync":
        record["sync_status"] = _sync_status_for_source(source)
        record["last_synced_at"] = _sync_timestamp(_source_profile(source)["stale"])
        record["sync_version"] = _sync_version()
    elif action == "partial":
        field = random.choice(["phone", "owner_id", "external_id", "source_record_id"])
        if random.random() < 0.5:
            record[field] = None
        else:
            record.pop(field, None)
    else:
        if random.random() < 0.25:
            record["last_activity_at"] = _past_iso(20, 180)
        else:
            record["last_activity_at"] = _past_iso(0, 3)

    _apply_dirty_evolution(record, "customers", source)
    _set_update_timestamp(record, source)
    _sanitize_record("customers", record)


def _mutate_lead(record: Dict[str, Any], source: str) -> None:
    source_factor = _source_cleanliness(source)
    age_factor = _age_multiplier(_record_age_days(record))

    action = random.choices(
        ["status", "score", "email", "refs", "partial"],
        weights=[
            1.25,
            0.95,
            0.85,
            0.75,
            0.55 * source_factor * age_factor,
        ],
        k=1,
    )[0]

    if action == "status":
        field_name = "lead_status" if "lead_status" in record else "leadStatus"
        record[field_name] = _lead_status_for_source(source)
    elif action == "score":
        if random.random() < 0.15:
            record["score"] = None
        elif random.random() < 0.30:
            record["score"] = str(random.randint(0, 100))
        else:
            record["score"] = random.randint(0, 100)
    elif action == "email":
        first_name = record.get("first_name") or random.choice(_FIRST_NAMES)
        last_name = record.get("last_name") or random.choice(_LAST_NAMES)
        company_name = record.get("company_name")
        record["email"] = _build_email(str(first_name), str(last_name), str(company_name) if company_name else None)
    elif action == "refs":
        broken = _source_profile(source)["broken_ref"]
        if random.random() < 0.5:
            record["contact_id"] = _pick_related_id("contacts", broken)
        else:
            company_id, company_name = _pick_company_details(broken)
            record["company_id"] = company_id
            record["company_name"] = company_name
    else:
        field = random.choice(["campaign", "owner_id", "phone"])
        if random.random() < 0.5:
            record[field] = None
        else:
            record.pop(field, None)

    _apply_dirty_evolution(record, "leads", source)
    _set_update_timestamp(record, source)
    _sanitize_record("leads", record)


def _mutate_activity(record: Dict[str, Any], source: str) -> None:
    source_factor = _source_cleanliness(source)
    age_factor = _age_multiplier(_record_age_days(record))

    action = random.choices(
        ["status", "type", "schedule", "partial", "refs"],
        weights=[
            0.95,
            0.9,
            1.2,
            0.6 * source_factor * age_factor,
            0.85,
        ],
        k=1,
    )[0]

    if action == "status":
        record["status"] = random.choice(_ACTIVITY_STATUS)
    elif action == "type":
        record["type"] = random.choice(_ACTIVITY_TYPE)
        if random.random() < _source_profile(source)["casing"]:
            record["type"] = _random_case(record["type"])
    elif action == "schedule":
        record["due_date"] = _past_iso(0, 5)
        if record.get("status") == "done" and random.random() < 0.6:
            record["completed_at"] = _past_iso(0, 5)
        elif random.random() < 0.30:
            record["completed_at"] = None
    elif action == "partial":
        field = random.choice(["notes", "owner_id", "completed_at"])
        if random.random() < 0.5:
            record[field] = None
        else:
            record.pop(field, None)
    else:
        relation_options = [
            ("contact_id", "contacts"),
            ("customer_id", "customers"),
            ("lead_id", "leads"),
            ("deal_id", "deals"),
        ]
        relation_field, relation_entity = random.choice(relation_options)
        for field_name, _ in relation_options:
            record.pop(field_name, None)
        record[relation_field] = _pick_related_id(relation_entity, _source_profile(source)["broken_ref"])

    _apply_dirty_evolution(record, "activities", source)
    _set_update_timestamp(record, source)
    _sanitize_record("activities", record)


def _mutate_deal(record: Dict[str, Any], source: str) -> None:
    source_factor = _source_cleanliness(source)
    age_factor = _age_multiplier(_record_age_days(record))

    action = random.choices(
        ["pipeline", "amount", "sync", "partial", "refs"],
        weights=[
            1.25,
            0.75,
            0.8,
            0.55 * source_factor * age_factor,
            0.65,
        ],
        k=1,
    )[0]

    if action == "pipeline":
        _apply_pipeline_shift_to_deal(record, source)
    elif action == "amount":
        base_amount = record.get("amount")
        try:
            amount_value = float(base_amount)
        except (TypeError, ValueError):
            amount_value = random.uniform(12000.0, 250000.0)

        amount_value = round(amount_value * random.uniform(0.82, 1.22), 2)
        if random.random() < 0.28:
            record["amount"] = f"{amount_value:.2f}"
        else:
            record["amount"] = amount_value
    elif action == "sync":
        record["sync_status"] = _sync_status_for_source(source)
        record["last_synced_at"] = _sync_timestamp(_source_profile(source)["stale"])
        record["sync_version"] = _sync_version()
    elif action == "partial":
        field = random.choice(["expected_close_date", "owner_id", "source_record_id", "currency", "probability"])
        if random.random() < 0.5:
            record[field] = None
        else:
            record.pop(field, None)
    else:
        if random.random() < 0.45:
            record["lead_id"] = _pick_related_id("leads", _source_profile(source)["broken_ref"])
        if random.random() < 0.45:
            record["contact_id"] = _pick_related_id("contacts", _source_profile(source)["broken_ref"])
        if random.random() < 0.45:
            record["customer_id"] = _pick_related_id("customers", _source_profile(source)["broken_ref"])

    _apply_dirty_evolution(record, "deals", source)
    _set_update_timestamp(record, source)
    _sanitize_record("deals", record)


def _run_pipeline_shift_batch(source: Optional[str]) -> int:
    updates = 0
    batch_size = random.randint(3, 8)

    for _ in range(batch_size):
        target_entity = random.choices(["leads", "deals"], weights=[0.44, 0.56], k=1)[0]
        record = _pick_pattern_filtered_record(target_entity, source, prefer_old=True)
        if not record:
            continue

        source_key = _normalize_source(record.get("source_system") or source)

        if target_entity == "leads":
            field_name = "lead_status" if "lead_status" in record else "leadStatus"
            record[field_name] = _lead_status_for_source(source_key)
            if random.random() < 0.35:
                record[field_name] = _random_case(record[field_name])
            if random.random() < 0.5:
                record["score"] = random.choice([random.randint(1, 100), str(random.randint(1, 100))])
            _apply_dirty_evolution(record, "leads", source_key)
        else:
            _apply_pipeline_shift_to_deal(record, source_key, burst_mode=True)
            _apply_dirty_evolution(record, "deals", source_key)

        _set_update_timestamp(record, source_key)
        _sanitize_record(target_entity, record)
        _record_change("update", target_entity, record)
        updates += 1

    return updates


def _run_sync_batch(source: Optional[str]) -> int:
    updates = 0
    batch_size = random.randint(4, 12)

    for _ in range(batch_size):
        target_entity = random.choices(
            ["customers", "leads", "activities", "deals"],
            weights=[0.2, 0.25, 0.3, 0.25],
            k=1,
        )[0]
        record = _pick_pattern_filtered_record(target_entity, source, prefer_old=True)
        if not record:
            continue

        source_key = _normalize_source(record.get("source_system") or source)

        if source_key == "salesforce":
            next_sync = random.choices(["synced", "ok", "pending"], weights=[0.72, 0.2, 0.08], k=1)[0]
        elif source_key == "manual_entry":
            next_sync = random.choices(["pending", "failed", "ok", "synced"], weights=[0.4, 0.32, 0.14, 0.14], k=1)[0]
        elif source_key == "internal_crm":
            next_sync = random.choices(["pending", "synced", "failed", "ok"], weights=[0.32, 0.38, 0.18, 0.12], k=1)[0]
        else:
            next_sync = _sync_status_for_source(source_key)

        record["sync_status"] = next_sync
        if next_sync in {"pending", "failed"}:
            record["last_synced_at"] = _past_iso(12, 160)
        else:
            record["last_synced_at"] = _past_iso(0, 8)
        record["sync_version"] = _sync_version()

        _apply_dirty_evolution(record, target_entity, source_key)
        _set_update_timestamp(record, source_key)
        _sanitize_record(target_entity, record)
        _record_change("update", target_entity, record)
        updates += 1

    return updates


def _trim_change_log() -> None:
    overflow = len(CHANGE_LOG) - MAX_CHANGE_LOG
    if overflow > 0:
        del CHANGE_LOG[:overflow]


def _entity_id_field(entity: str) -> str:
    config = _ENTITY_CONFIG.get(entity, {})
    return str(config.get("id_field") or "id")


def _build_partial_event_data(entity: str, record: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(record, dict):
        return {}

    partial: Dict[str, Any] = {}
    id_field = _entity_id_field(entity)

    if "id" in record:
        partial["id"] = copy.deepcopy(record.get("id"))
    if id_field in record:
        partial[id_field] = copy.deepcopy(record.get(id_field))

    preferred_fields = [
        "updated_at",
        "last_synced_at",
        "sync_status",
        "sync_version",
        "status",
        "lead_status",
        "leadStatus",
        "stage",
        "Stage",
        "amount",
        "probability",
        "score",
        "owner_id",
        "source_system",
    ]

    selected: List[str] = []
    for key in preferred_fields:
        if key in record and key not in partial and random.random() < 0.6:
            selected.append(key)
        if len(selected) >= 4:
            break

    remaining = [
        key for key in record.keys()
        if key not in partial and key not in selected
    ]

    while len(selected) < 2 and remaining:
        picked = random.choice(remaining)
        selected.append(picked)
        remaining.remove(picked)

    if remaining:
        extra_count = random.randint(0, min(3, len(remaining)))
        if extra_count > 0:
            selected.extend(random.sample(remaining, extra_count))

    for key in selected:
        partial[key] = copy.deepcopy(record.get(key))

    return partial


def _mutate_duplicate_payload(entity: str, payload: Dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        return

    string_fields = [
        field for field in ["status", "lead_status", "leadStatus", "stage", "Stage", "sync_status", "type", "priority"]
        if field in payload and isinstance(payload.get(field), str)
    ]

    if string_fields and random.random() < 0.7:
        chosen_field = random.choice(string_fields)
        payload[chosen_field] = _random_case(str(payload.get(chosen_field)))

    if "sync_version" in payload and random.random() < 0.5:
        current_sync = payload.get("sync_version")
        if isinstance(current_sync, int):
            payload["sync_version"] = str(current_sync)
        elif isinstance(current_sync, str) and current_sync.isdigit():
            payload["sync_version"] = int(current_sync)

    if "updated_at" in payload and random.random() < 0.7:
        payload["updated_at"] = _now_iso() if random.random() < 0.6 else _past_iso(0, 3)

    if "last_synced_at" in payload and random.random() < 0.5:
        payload["last_synced_at"] = _past_iso(0, 30)

    if "score" in payload and random.random() < 0.35:
        current_score = payload.get("score")
        if isinstance(current_score, int):
            payload["score"] = str(current_score)
        elif isinstance(current_score, str) and current_score.isdigit():
            payload["score"] = int(current_score)

    if "amount" in payload and random.random() < 0.35:
        current_amount = payload.get("amount")
        if isinstance(current_amount, str):
            try:
                payload["amount"] = round(float(current_amount), 2)
            except ValueError:
                pass
        elif isinstance(current_amount, (int, float)):
            payload["amount"] = f"{float(current_amount):.2f}"


def _append_change_event(
    event_type: str,
    entity: str,
    record_id: Any,
    data: Dict[str, Any],
) -> None:
    normalized_event_type = str(event_type).strip().lower()
    if normalized_event_type not in {"create", "update", "delete"}:
        normalized_event_type = "update"

    cdc_store.append_event(
        entity_type=entity,
        entity_id=record_id,
        operation=normalized_event_type,
        payload=copy.deepcopy(data) if isinstance(data, dict) else {"value": data},
        timestamp=_now_iso(),
    )


def _record_change(event_type: str, entity: str, record: Dict[str, Any]) -> None:
    full_data = copy.deepcopy(record) if isinstance(record, dict) else {}
    id_field = _entity_id_field(entity)

    record_id = full_data.get("id")
    if record_id is None and id_field in full_data:
        record_id = full_data.get(id_field)

    normalized_event_type = str(event_type).strip().lower()
    if normalized_event_type not in {"create", "update", "delete"}:
        normalized_event_type = "update"

    _append_change_event(normalized_event_type, entity, record_id, full_data)


async def _creation_loop() -> None:
    try:
        while not _STOP_EVENT.is_set():
            await _sleep_with_stream_dynamics(0.5, 2.0)

            async with _LOCK:
                weights_map, batch_size, source_hint = _creation_weights_and_batch()
                if random.random() < _STREAM_DYNAMICS["burst_probability"]:
                    batch_size = max(
                        batch_size,
                        random.randint(int(_STREAM_DYNAMICS["burst_batch_min"]), int(_STREAM_DYNAMICS["burst_batch_max"])),
                    )
                available_entities = [
                    entity for entity in ["customers", "leads", "activities"]
                    if _entity_can_grow(entity)
                ]
                if not available_entities:
                    _decrement_pattern(_CREATION_PATTERN)
                    continue

                version_bucket = DATA_STORE.setdefault(LIVE_VERSION, {})

                for _ in range(batch_size):
                    current_available = [
                        entity for entity in available_entities
                        if _entity_can_grow(entity)
                    ]
                    if not current_available:
                        break

                    entity = random.choices(
                        current_available,
                        weights=[weights_map.get(item, 0.1) for item in current_available],
                        k=1,
                    )[0]

                    source_override = source_hint if source_hint and random.random() < 0.86 else None

                    if entity == "customers":
                        record = _create_customer(source_override=source_override)
                    elif entity == "leads":
                        record = _create_lead(source_override=source_override)
                    else:
                        record = _create_activity(source_override=source_override)

                    version_bucket.setdefault(entity, []).append(record)
                    _record_change("create", entity, record)

                _decrement_pattern(_CREATION_PATTERN)
    except asyncio.CancelledError:
        return


async def _mutation_loop() -> None:
    try:
        while not _STOP_EVENT.is_set():
            await _sleep_with_stream_dynamics(0.6, 1.9)

            async with _LOCK:
                mutation_iterations = 1
                if random.random() < _STREAM_DYNAMICS["burst_probability"]:
                    mutation_iterations = random.randint(
                        int(_STREAM_DYNAMICS["burst_batch_min"]),
                        int(_STREAM_DYNAMICS["burst_batch_max"]),
                    )

                for _ in range(mutation_iterations):
                    _maybe_start_mutation_pattern()

                    mode = _MUTATION_PATTERN["name"]
                    if mode == "pipeline_shift":
                        _run_pipeline_shift_batch(_MUTATION_PATTERN["source"])
                        _decrement_pattern(_MUTATION_PATTERN)
                        continue
                    if mode == "sync_batch":
                        _run_sync_batch(_MUTATION_PATTERN["source"])
                        _decrement_pattern(_MUTATION_PATTERN)
                        continue

                    entity = random.choices(
                        ["customers", "leads", "activities", "deals"],
                        weights=[0.12, 0.16, 0.42, 0.30],
                        k=1,
                    )[0]

                    record = _pick_pattern_filtered_record(entity, None, prefer_old=True)
                    if not record:
                        continue

                    source = _normalize_source(record.get("source_system"))
                    event_type = "update"

                    if entity == "leads":
                        conversion_roll = random.random()
                        if conversion_roll < _STREAM_DYNAMICS["lead_convert_probability"]:
                            lead_field = "lead_status" if "lead_status" in record else "leadStatus"
                            record[lead_field] = "converted"
                            record["converted_at"] = _now_iso()
                            event_type = "activity"
                        elif conversion_roll < (
                            _STREAM_DYNAMICS["lead_convert_probability"] + _STREAM_DYNAMICS["lead_stall_probability"]
                        ):
                            lead_field = "lead_status" if "lead_status" in record else "leadStatus"
                            record[lead_field] = random.choice(["new", "contacted", "qualified"])
                            record["last_activity_at"] = _past_iso(12, 220)

                    if entity == "deals":
                        deal_roll = random.random()
                        disappear_threshold = _STREAM_DYNAMICS["deal_disappear_probability"]
                        close_threshold = disappear_threshold + _STREAM_DYNAMICS["deal_close_probability"]
                        stall_threshold = close_threshold + _STREAM_DYNAMICS["deal_stall_probability"]

                        if deal_roll < disappear_threshold:
                            record["is_deleted"] = True
                            record["deleted_at"] = _now_iso()
                            stage_field = _pick_deal_stage_field(record)
                            record[stage_field] = "lost"
                            record["status"] = "lost"
                            record["deal_state"] = "disappeared"
                            _set_update_timestamp(record, source)
                            _sanitize_record(entity, record)
                            event_type = "delete"
                            _record_change(event_type, entity, record)
                            continue

                        if deal_roll < close_threshold:
                            stage_field = _pick_deal_stage_field(record)
                            if random.random() < 0.58:
                                record[stage_field] = "won"
                                record["status"] = "won"
                            else:
                                record[stage_field] = "lost"
                                record["status"] = "lost"
                            record["closed_at"] = _now_iso()
                            event_type = "activity"
                        elif deal_roll < stall_threshold:
                            stage_field = _pick_deal_stage_field(record)
                            record[stage_field] = random.choice(["prospecting", "qualified", "negotiation"])
                            record["status"] = "open"
                            record["last_activity_at"] = _past_iso(15, 280)

                    if entity == "customers":
                        _mutate_customer(record, source)
                    elif entity == "leads":
                        _mutate_lead(record, source)
                    elif entity == "activities":
                        _mutate_activity(record, source)
                    else:
                        _mutate_deal(record, source)

                    _record_change(event_type, entity, record)
    except asyncio.CancelledError:
        return


async def start_stream_engine() -> None:
    """Start background generation/mutation tasks (idempotent)."""
    global _TASKS

    _load_stream_dynamics_profile()
    cdc_store.initialize()

    active_tasks = [task for task in _TASKS if not task.done()]
    if active_tasks:
        _TASKS = active_tasks
        return

    DATA_STORE.setdefault(LIVE_VERSION, {})
    for entity in _ENTITY_CONFIG:
        DATA_STORE[LIVE_VERSION].setdefault(entity, [])

    async with _LOCK:
        _sanitize_live_dataset()
        _refresh_id_tracking()
        _CREATION_PATTERN["name"] = "normal"
        _CREATION_PATTERN["remaining"] = 0
        _CREATION_PATTERN["source"] = None
        _MUTATION_PATTERN["name"] = "normal"
        _MUTATION_PATTERN["remaining"] = 0
        _MUTATION_PATTERN["source"] = None

    _STOP_EVENT.clear()
    _TASKS = [
        asyncio.create_task(_creation_loop(), name="crm_stream_creation"),
        asyncio.create_task(_mutation_loop(), name="crm_stream_mutation"),
    ]


async def stop_stream_engine() -> None:
    """Stop background tasks safely during shutdown."""
    global _TASKS

    _STOP_EVENT.set()
    tasks_to_stop = [task for task in _TASKS if not task.done()]
    _TASKS = []

    for task in tasks_to_stop:
        task.cancel()

    if tasks_to_stop:
        await asyncio.gather(*tasks_to_stop, return_exceptions=True)


async def refresh_stream_state() -> None:
    """Refresh internal counters after external reloads."""
    async with _LOCK:
        _sanitize_live_dataset()
        _refresh_id_tracking()


async def get_recent_changes(
    limit: int = 100,
    entity: Optional[str] = None,
    event_type: Optional[str] = None,
    since: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return persisted CDC events with optional filters."""
    normalized_limit = max(1, min(limit, 500))
    normalized_entity = entity.lower() if isinstance(entity, str) and entity else None
    normalized_event_type = event_type.lower() if isinstance(event_type, str) and event_type else None

    operation_filter = None
    if normalized_event_type:
        if normalized_event_type in {"create", "update", "delete"}:
            operation_filter = normalized_event_type
        elif normalized_event_type == "activity":
            operation_filter = "update"
        else:
            raise ValueError("Invalid event_type filter; use create, update, or delete")

    return cdc_store.list_events(
        since=since,
        limit=normalized_limit,
        entity_type=normalized_entity,
        operation=operation_filter,
        latest_when_no_since=True,
    )


async def get_batch_export(
    version: str = LIVE_VERSION,
    include_static: bool = True,
) -> Dict[str, Any]:
    """Return a snapshot export suitable for batch pipeline ingestion tests."""
    target_version = version if version in DATA_STORE else LIVE_VERSION
    entities = ["customers", "contacts", "leads", "deals", "activities", "notes", "companies"]

    async with _LOCK:
        version_bucket = DATA_STORE.get(target_version, {})
        snapshot_data: Dict[str, List[Dict[str, Any]]] = {}
        record_counts: Dict[str, int] = {}

        for entity_name in entities:
            records = version_bucket.get(entity_name, [])
            snapshot_data[entity_name] = copy.deepcopy(records)
            record_counts[entity_name] = len(records)

        export_payload: Dict[str, Any] = {
            "exported_at": _now_iso(),
            "version": target_version,
            "record_counts": record_counts,
            "data": snapshot_data,
        }

        if include_static:
            export_payload["static"] = {
                "owners": copy.deepcopy(data_loader.get_static_data("owners")),
                "pipeline_stages": copy.deepcopy(data_loader.get_static_data("pipeline_stages")),
                "sync_status": copy.deepcopy(data_loader.get_static_data("sync_status")),
            }

    return export_payload


def _format_sse(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
    sequence = event.get("event_id", event.get("sequence", ""))
    event_type = event.get("operation", event.get("event_type", "update"))
    return f"id: {sequence}\nevent: {event_type}\ndata: {payload}\n\n"


async def sse_event_generator(limit: int = 100):
    """
    Yield SSE frames from in-memory change events.

    Emits periodic keep-alive comments while idle.
    """
    initial = await get_recent_changes(limit=limit)
    last_event_id = 0

    for event in initial:
        event_id = int(event.get("event_id", event.get("sequence", 0)))
        last_event_id = max(last_event_id, event_id)
        yield _format_sse(event)

    idle_ticks = 0

    try:
        while True:
            await asyncio.sleep(1.0)

            pending = cdc_store.list_events(
                since=str(last_event_id),
                limit=limit,
                latest_when_no_since=False,
            )

            if pending:
                for event in pending:
                    event_id = int(event.get("event_id", event.get("sequence", 0)))
                    last_event_id = max(last_event_id, event_id)
                    yield _format_sse(event)
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 10:
                    idle_ticks = 0
                    yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        return