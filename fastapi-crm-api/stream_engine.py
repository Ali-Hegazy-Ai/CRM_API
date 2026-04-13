"""
Continuous in-memory stream engine for the CRM API.

This module keeps the loaded dataset "live" by incrementally creating and mutating
records in memory. It is intentionally lightweight for serverless runtimes.
"""

import asyncio
import copy
import json
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from data_loader import data_loader


LIVE_VERSION = "v3"
MAX_CHANGE_LOG = 800

# Live data is based on the existing loader cache. We mutate only v3 incrementally.
DATA_STORE: Dict[str, Dict[str, List[Dict[str, Any]]]] = data_loader.cache
CHANGE_LOG: List[Dict[str, Any]] = []


_ENTITY_CONFIG = {
    "customers": {"prefix": "cust_", "id_field": "customer_id", "singular": "customer"},
    "leads": {"prefix": "lead_", "id_field": "lead_id", "singular": "lead"},
    "activities": {"prefix": "act_", "id_field": "activity_id", "singular": "activity"},
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


_TASKS: List[asyncio.Task] = []
_STOP_EVENT = asyncio.Event()
_LOCK = asyncio.Lock()
_EVENT_SEQUENCE = 0

_ID_COUNTERS = {entity: 0 for entity in _ENTITY_CONFIG}
_USED_IDS = {entity: set() for entity in _ENTITY_CONFIG}


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
    return f"{random.choice(_LAST_NAMES)} {random.choice(_COMPANY_SUFFIX)}"


def _random_phone() -> str:
    if random.random() < 0.15:
        return f"+1-{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
    if random.random() < 0.25:
        return f"({random.randint(200, 999)}){random.randint(100, 999)}-{random.randint(1000, 9999)}"
    return f"{random.randint(200, 999)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"


def _invalid_email(base_email: str) -> str:
    options = [
        "",
        "unknown",
        base_email.replace("@", " at "),
        base_email.split("@")[0],
        f"{base_email} ",
    ]
    return random.choice(options)


def _build_email(first_name: str, last_name: str) -> str:
    return f"{first_name.lower()}.{last_name.lower()}@{random.choice(_EMAIL_DOMAINS)}"


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

    prefix_map = {
        "companies": "comp_",
        "contacts": "cont_",
        "customers": "cust_",
        "leads": "lead_",
        "deals": "deal_",
    }
    prefix = prefix_map.get(entity, "badref_")
    return f"{prefix}{random.randint(900000, 999999)}"


def _pick_company_details(broken_rate: float = 0.02) -> Tuple[Optional[str], str]:
    companies = DATA_STORE.get(LIVE_VERSION, {}).get("companies", [])
    if companies and random.random() >= broken_rate:
        company = random.choice(companies)
        company_id = company.get("id") or company.get("company_id")
        company_name = company.get("name") or company.get("legal_name") or _random_company_name()
        return company_id, company_name

    return f"comp_{random.randint(900000, 999999)}", _random_company_name()


def _sync_status_for_source(source: str) -> str:
    if source == "manual_entry":
        return random.choices(["pending", "failed", "synced", "ok"], weights=[0.35, 0.25, 0.25, 0.15], k=1)[0]
    if source in {"pipedrive", "internal_crm"}:
        return random.choices(["synced", "ok", "pending", "failed"], weights=[0.45, 0.2, 0.25, 0.1], k=1)[0]
    return random.choices(["synced", "ok", "pending", "failed"], weights=[0.65, 0.2, 0.12, 0.03], k=1)[0]


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
    prefix = _ENTITY_CONFIG[entity]["prefix"]

    while True:
        _ID_COUNTERS[entity] += 1
        candidate = f"{prefix}{_ID_COUNTERS[entity]:06d}"
        if candidate not in _USED_IDS[entity]:
            _USED_IDS[entity].add(candidate)
            return candidate


def _apply_messiness(record: Dict[str, Any], entity: str, source: str) -> None:
    profile = _source_profile(source)

    optional_fields = {
        "customers": ["external_id", "phone", "owner_id", "source_record_id"],
        "leads": ["campaign", "owner_id", "source_record_id", "phone"],
        "activities": ["notes", "owner_id", "completed_at", "source_record_id"],
    }

    options = optional_fields.get(entity, [])

    if options and random.random() < profile["missing_field"]:
        field_to_drop = random.choice(options)
        if field_to_drop in record:
            record.pop(field_to_drop, None)

    if options and random.random() < profile["null_field"]:
        field_to_null = random.choice(options)
        record[field_to_null] = None

    if "email" in record and isinstance(record.get("email"), str) and random.random() < profile["invalid_email"]:
        record["email"] = _invalid_email(record["email"])

    if random.random() < profile["casing"]:
        for field in ["status", "lead_status", "type", "sync_status"]:
            if field in record and isinstance(record.get(field), str):
                record[field] = _random_case(record[field])

    if "source_system" in record and random.random() < profile["casing"]:
        record["source_system"] = _source_label(source, 1.0)


def _create_customer() -> Dict[str, Any]:
    source = _choose_source()
    profile = _source_profile(source)
    now_value = _now_iso()

    customer_id = _next_primary_id("customers")
    first_name, last_name = _random_name_parts()
    company_id, company_name = _pick_company_details(profile["broken_ref"])

    record = {
        "id": customer_id,
        "customer_id": customer_id,
        "external_id": f"EXT-{random.randint(1000, 9999)}",
        "name": company_name,
        "email": _build_email(first_name, last_name),
        "phone": _random_phone(),
        "status": random.choice(_CUSTOMER_STATUS),
        "company_id": company_id,
        "owner_id": _pick_owner_id(source),
        "created_at": now_value,
        "updated_at": now_value,
        "last_activity_at": now_value,
        "country": random.choice(["US", "usa", "united states", "gb", "eg", "de"]),
        "source_system": _source_label(source, profile["casing"]),
        "source_record_id": f"SRC-{random.randint(10000, 99999)}",
        "sync_status": _sync_status_for_source(source),
        "sync_version": _sync_version(),
        "last_synced_at": _sync_timestamp(profile["stale"]),
    }

    if random.random() < 0.08:
        record["created_date"] = record.pop("created_at")

    _apply_messiness(record, "customers", source)
    return record


def _create_lead() -> Dict[str, Any]:
    source = _choose_source()
    profile = _source_profile(source)
    now_value = _now_iso()

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
        "email": _build_email(first_name, last_name),
        "phone": _random_phone(),
        "company_name": company_name,
        "company_id": company_id,
        "contact_id": _pick_related_id("contacts", profile["broken_ref"]),
        "lead_status": random.choice(_LEAD_STATUS),
        "score": random.randint(1, 100),
        "campaign": random.choice(["webinar", "referral", "paid_search", "event", "outbound"]),
        "owner_id": _pick_owner_id(source),
        "created_at": now_value,
        "updated_at": now_value,
        "source_system": _source_label(source, profile["casing"]),
        "source_record_id": f"SRC-{random.randint(10000, 99999)}",
        "sync_status": _sync_status_for_source(source),
        "sync_version": _sync_version(),
        "last_synced_at": _sync_timestamp(profile["stale"]),
    }

    if random.random() < 0.06:
        record["leadStatus"] = record.pop("lead_status")

    _apply_messiness(record, "leads", source)
    return record


def _create_activity() -> Dict[str, Any]:
    source = _choose_source()
    profile = _source_profile(source)
    now_value = _now_iso()

    activity_id = _next_primary_id("activities")
    status = random.choice(_ACTIVITY_STATUS)
    activity_type = random.choice(_ACTIVITY_TYPE)
    due_date = _future_iso(-2, 21)

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
        "created_at": now_value,
        "updated_at": now_value,
        "due_date": due_date,
        "completed_at": now_value if status == "done" and random.random() < 0.7 else None,
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
    return record


def _set_update_timestamp(record: Dict[str, Any], source: str) -> None:
    profile = _source_profile(source)
    if random.random() < profile["stale"] * 0.35:
        record["updated_at"] = _past_iso(15, 120)
    else:
        record["updated_at"] = _now_iso()


def _mutate_customer(record: Dict[str, Any], source: str) -> None:
    action = random.choice(["status", "email", "sync", "partial", "activity_time"])

    if action == "status":
        record["status"] = random.choice(_CUSTOMER_STATUS)
        if random.random() < _source_profile(source)["casing"]:
            record["status"] = _random_case(record["status"])
    elif action == "email":
        first_name, last_name = _random_name_parts()
        if random.random() < _source_profile(source)["invalid_email"]:
            record["email"] = _invalid_email(_build_email(first_name, last_name))
        else:
            record["email"] = _build_email(first_name, last_name)
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

    _set_update_timestamp(record, source)


def _mutate_lead(record: Dict[str, Any], source: str) -> None:
    action = random.choice(["status", "score", "email", "refs", "partial"])

    if action == "status":
        field_name = "lead_status" if "lead_status" in record else "leadStatus"
        record[field_name] = random.choice(_LEAD_STATUS)
        if random.random() < _source_profile(source)["casing"]:
            record[field_name] = _random_case(record[field_name])
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
        clean_email = _build_email(str(first_name), str(last_name))
        if random.random() < _source_profile(source)["invalid_email"]:
            record["email"] = _invalid_email(clean_email)
        else:
            record["email"] = clean_email
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

    _set_update_timestamp(record, source)


def _mutate_activity(record: Dict[str, Any], source: str) -> None:
    action = random.choice(["status", "type", "schedule", "partial", "refs"])

    if action == "status":
        record["status"] = random.choice(_ACTIVITY_STATUS)
        if random.random() < _source_profile(source)["casing"]:
            record["status"] = _random_case(record["status"])
    elif action == "type":
        record["type"] = random.choice(_ACTIVITY_TYPE)
        if random.random() < _source_profile(source)["casing"]:
            record["type"] = _random_case(record["type"])
    elif action == "schedule":
        record["due_date"] = _future_iso(-3, 20)
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

    _set_update_timestamp(record, source)


def _record_change(event_type: str, entity: str, record: Dict[str, Any]) -> None:
    global _EVENT_SEQUENCE
    _EVENT_SEQUENCE += 1

    event = {
        "sequence": _EVENT_SEQUENCE,
        "event_type": event_type,
        "entity": _ENTITY_CONFIG[entity]["singular"],
        "id": record.get("id"),
        "timestamp": _now_iso(),
        "data": copy.deepcopy(record),
    }

    CHANGE_LOG.append(event)
    overflow = len(CHANGE_LOG) - MAX_CHANGE_LOG
    if overflow > 0:
        del CHANGE_LOG[:overflow]


async def _creation_loop() -> None:
    try:
        while not _STOP_EVENT.is_set():
            await asyncio.sleep(random.uniform(0.5, 2.0))

            batch_size = 2 if random.random() < 0.18 else 1

            async with _LOCK:
                for _ in range(batch_size):
                    entity = random.choices(
                        ["customers", "leads", "activities"],
                        weights=[0.34, 0.33, 0.33],
                        k=1,
                    )[0]

                    if entity == "customers":
                        record = _create_customer()
                    elif entity == "leads":
                        record = _create_lead()
                    else:
                        record = _create_activity()

                    DATA_STORE[LIVE_VERSION].setdefault(entity, []).append(record)
                    _record_change("create", entity, record)
    except asyncio.CancelledError:
        return


async def _mutation_loop() -> None:
    try:
        while not _STOP_EVENT.is_set():
            await asyncio.sleep(random.uniform(0.7, 2.0))

            entity = random.choices(
                ["customers", "leads", "activities"],
                weights=[0.36, 0.33, 0.31],
                k=1,
            )[0]

            async with _LOCK:
                records = DATA_STORE.get(LIVE_VERSION, {}).get(entity, [])
                if not records:
                    continue

                record = random.choice(records)
                source = _normalize_source(record.get("source_system"))
                event_type = "update"

                if random.random() < 0.03:
                    record["is_deleted"] = random.choice([True, 1, "true"])
                    record["deleted_at"] = _now_iso()
                    _set_update_timestamp(record, source)
                    event_type = "delete"
                else:
                    if entity == "customers":
                        _mutate_customer(record, source)
                    elif entity == "leads":
                        _mutate_lead(record, source)
                    else:
                        _mutate_activity(record, source)

                _record_change(event_type, entity, record)
    except asyncio.CancelledError:
        return


async def start_stream_engine() -> None:
    """Start background generation/mutation tasks (idempotent)."""
    global _TASKS

    active_tasks = [task for task in _TASKS if not task.done()]
    if active_tasks:
        _TASKS = active_tasks
        return

    DATA_STORE.setdefault(LIVE_VERSION, {})
    for entity in _ENTITY_CONFIG:
        DATA_STORE[LIVE_VERSION].setdefault(entity, [])

    async with _LOCK:
        _refresh_id_tracking()

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
        _refresh_id_tracking()


async def get_recent_changes(
    limit: int = 100,
    entity: Optional[str] = None,
    event_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return latest change events with optional filters."""
    normalized_limit = max(1, min(limit, 500))
    normalized_entity = entity.lower().rstrip("s") if isinstance(entity, str) and entity else None
    normalized_event_type = event_type.lower() if isinstance(event_type, str) and event_type else None

    async with _LOCK:
        events = list(CHANGE_LOG)

    if normalized_entity:
        events = [event for event in events if str(event.get("entity", "")).lower() == normalized_entity]

    if normalized_event_type:
        events = [event for event in events if str(event.get("event_type", "")).lower() == normalized_event_type]

    return events[-normalized_limit:]


def _format_sse(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, separators=(",", ":"), ensure_ascii=True)
    sequence = event.get("sequence", "")
    event_type = event.get("event_type", "update")
    return f"id: {sequence}\nevent: {event_type}\ndata: {payload}\n\n"


async def sse_event_generator(limit: int = 100):
    """
    Yield SSE frames from in-memory change events.

    Emits periodic keep-alive comments while idle.
    """
    initial = await get_recent_changes(limit=limit)
    last_sequence = 0

    for event in initial:
        sequence = int(event.get("sequence", 0))
        last_sequence = max(last_sequence, sequence)
        yield _format_sse(event)

    idle_ticks = 0

    try:
        while True:
            await asyncio.sleep(1.0)

            async with _LOCK:
                pending = [
                    event
                    for event in CHANGE_LOG
                    if int(event.get("sequence", 0)) > last_sequence
                ]

            if pending:
                for event in pending:
                    sequence = int(event.get("sequence", 0))
                    last_sequence = max(last_sequence, sequence)
                    yield _format_sse(event)
                idle_ticks = 0
            else:
                idle_ticks += 1
                if idle_ticks >= 10:
                    idle_ticks = 0
                    yield ": keep-alive\n\n"
    except asyncio.CancelledError:
        return