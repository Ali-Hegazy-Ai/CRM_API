import argparse
import json
import re
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path


VERSIONS = ["v1", "v2", "v3"]
ENTITIES = ["customers", "contacts", "leads", "deals", "activities", "notes", "companies"]

REFERENCE_FIELDS = {
    "customers": ["company_id"],
    "contacts": ["company_id", "customer_id"],
    "leads": ["company_id", "contact_id"],
    "deals": ["customer_id", "contact_id", "lead_id", "company_id"],
    "activities": ["customer_id", "contact_id", "lead_id", "deal_id"],
    "notes": ["entity_id", "customer_id", "contact_id", "lead_id", "deal_id", "company_id"],
}

MIN_V3_COUNTS = {
    "customers": 200,
    "contacts": 300,
    "leads": 200,
    "deals": 150,
    "activities": 500,
    "notes": 200,
    "companies": 100,
}

FIELD_DRIFT_KEYS = {
    "email_address",
    "phone_number",
    "Status",
    "firstName",
    "created_date",
    "last_modified",
    "Stage",
}

OPTIONAL_BY_ENTITY = {
    "customers": ["owner_id", "updated_at", "last_activity_at", "source_record_id"],
    "contacts": ["company_id", "customer_id", "updated_at", "owner_id"],
    "leads": ["company_id", "contact_id", "campaign", "updated_at"],
    "deals": ["customer_id", "contact_id", "lead_id", "expected_close_date"],
    "activities": ["notes", "due_date", "completed_at", "updated_at"],
    "notes": ["title", "content", "updated_at", "owner_id"],
    "companies": ["website", "phone", "employee_count", "updated_at"],
}

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
BAD_PHONE_VALUES = {"123", "n/a", "000-000", "+1 ()", "++2012", "phone missing"}

TARGET_BANDS = {
    "missing_optional": (10.0, 20.0),
    "null_non_key": (5.0, 10.0),
    "invalid_email_phone": (5.0, 10.0),
    "inconsistent_casing": (10.0, 20.0),
    "mixed_date_formats": (10.0, 15.0),
    "field_name_drift": (5.0, 10.0),
    "type_inconsistencies": (5.0, 10.0),
    "conflicting_statuses": (3.0, 8.0),
    "orphan_refs": (3.0, 5.0),
    "stale_sync": (5.0, 10.0),
}


class ValidationState:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.stats = defaultdict(int)
        self.relationship_total = 0
        self.relationship_invalid = 0
        self.source_stats = defaultdict(lambda: defaultdict(int))
        self.date_format_stats = Counter()
        self.logical_duplicate_stats = defaultdict(int)

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)


def load_all(data_root, state):
    all_data = {}
    for version in VERSIONS:
        all_data[version] = {}
        for entity in ENTITIES:
            path = data_root / version / f"{entity}.json"
            if not path.exists():
                state.error(f"Missing file: {path}")
                all_data[version][entity] = []
                continue

            try:
                text = path.read_text(encoding="utf-8")
                obj = json.loads(text)
            except Exception as ex:
                state.error(f"Invalid JSON in {path}: {ex}")
                all_data[version][entity] = []
                continue

            if not isinstance(obj, list):
                state.error(f"Not an array in {path}")
                obj = []

            all_data[version][entity] = obj

    return all_data


def check_unique_ids(all_data, state):
    for version in VERSIONS:
        for entity in ENTITIES:
            seen = set()
            arr = all_data[version][entity]
            for idx in range(len(arr)):
                rec = arr[idx]
                rec_id = rec.get("id")
                if not rec_id:
                    state.error(f"{version}/{entity} record {idx} missing id")
                    continue
                if rec_id in seen:
                    state.error(f"Duplicate primary id in {version}/{entity}: {rec_id}")
                seen.add(rec_id)


def check_v3_volume(all_data, state):
    v3 = all_data["v3"]
    for entity, min_count in MIN_V3_COUNTS.items():
        got = len(v3[entity])
        if got < min_count:
            state.error(f"v3/{entity} too small. got={got}, need>={min_count}")


def build_id_pools(version_data):
    pools = {}
    for entity in ENTITIES:
        ids = set()
        arr = version_data[entity]
        for i in range(len(arr)):
            rec_id = arr[i].get("id")
            if rec_id:
                ids.add(rec_id)
        pools[entity] = ids
    return pools


def expected_entity_for_field(field_name):
    mapping = {
        "company_id": "companies",
        "customer_id": "customers",
        "contact_id": "contacts",
        "lead_id": "leads",
        "deal_id": "deals",
    }
    return mapping.get(field_name)


def to_naive_utc(dt):
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def is_invalid_phone(value):
    raw = str(value).strip()
    if raw == "":
        return True

    if raw.lower() in BAD_PHONE_VALUES:
        return True

    digits = ""
    for ch in raw:
        if ch.isdigit():
            digits = digits + ch

    # Allow mixed symbols/extensions as long as there are enough digits.
    if len(digits) < 7:
        return True

    return False


def parse_any_date(value):
    if value is None:
        return None
    if isinstance(value, int):
        try:
            return datetime.fromtimestamp(value, timezone.utc).replace(tzinfo=None)
        except Exception:
            return None
    if isinstance(value, str):
        v = value.strip()
        if v == "":
            return None

        if v.isdigit():
            try:
                return datetime.fromtimestamp(int(v), timezone.utc).replace(tzinfo=None)
            except Exception:
                return None

        layouts = [
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
            "%m/%d/%Y %H:%M",
            "%Y-%m-%d",
            "%m/%d/%Y",
        ]
        for fmt in layouts:
            try:
                return datetime.strptime(v, fmt)
            except Exception:
                pass

        try:
            normalized = v.replace("z", "Z")
            return to_naive_utc(datetime.fromisoformat(normalized.replace("Z", "+00:00")))
        except Exception:
            return None

    return None


def check_relationships(all_data, state):
    for version in VERSIONS:
        pools = build_id_pools(all_data[version])
        for entity in ENTITIES:
            arr = all_data[version][entity]
            rel_fields = REFERENCE_FIELDS.get(entity, [])
            for i in range(len(arr)):
                rec = arr[i]
                for j in range(len(rel_fields)):
                    fld = rel_fields[j]
                    if fld not in rec or rec[fld] in [None, ""]:
                        continue

                    value = rec[fld]
                    if fld == "entity_id":
                        state.relationship_total += 1
                        found = False
                        for target_entity in ENTITIES:
                            if value in pools[target_entity]:
                                found = True
                                break
                        if not found:
                            state.relationship_invalid += 1
                        continue

                    expected = expected_entity_for_field(fld)
                    if not expected:
                        continue

                    state.relationship_total += 1
                    if value not in pools[expected]:
                        state.relationship_invalid += 1


def normalize_source(value):
    if value is None:
        return "missing_source"
    v = str(value).strip().lower()
    mapping = {
        "salesforce": "salesforce",
        "sf": "salesforce",
        "hubspot": "hubspot",
        "zoho": "zoho",
        "pipedrive": "pipedrive",
        "internalcrm": "internal_crm",
        "internal_crm": "internal_crm",
        "manual_entry": "manual_entry",
        "manual": "manual_entry",
    }
    compact = v.replace("_", "")
    if v in mapping:
        return mapping[v]
    if compact in mapping:
        return mapping[compact]
    return v


def detect_date_format(value):
    if value is None:
        return "missing"
    if isinstance(value, int):
        return "unix_int"

    s = str(value).strip()
    if s == "":
        return "missing"
    if s.isdigit():
        return "unix_str"
    upper = s.upper()
    if "T" in upper and upper.endswith("Z"):
        return "iso8601"
    if "/" in s:
        return "slash"
    if "-" in s and ":" in s:
        return "sql"
    return "other"


def check_logical_duplicates(all_data, state):
    for version in VERSIONS:
        for entity in ENTITIES:
            arr = all_data[version][entity]
            state.logical_duplicate_stats["records_total"] += len(arr)

            explicit_dups = 0
            fuzzy_dups = 0
            seen_keys = set()

            for rec in arr:
                if rec.get("duplicate_of"):
                    explicit_dups += 1

                name_val = rec.get("name") or rec.get("company_name") or rec.get("full_name") or rec.get("contact_name")
                email_val = rec.get("email") or rec.get("email_address")
                phone_val = rec.get("phone") or rec.get("phone_number")
                key = None
                if name_val and email_val:
                    key = f"{str(name_val).strip().lower()}|{str(email_val).strip().lower()}"
                elif name_val and phone_val:
                    key = f"{str(name_val).strip().lower()}|{str(phone_val).strip().lower()}"

                if key:
                    if key in seen_keys:
                        fuzzy_dups += 1
                    else:
                        seen_keys.add(key)

            state.logical_duplicate_stats["explicit_duplicate_of"] += explicit_dups
            state.logical_duplicate_stats["fuzzy_duplicate_candidates"] += fuzzy_dups


def scan_messiness(all_data, state):
    total_records = 0
    optional_slots_total = 0
    optional_slots_missing = 0

    known_case_values = {
        "status": {"active", "inactive", "churned", "open", "won", "lost", "done", "pending", "overdue", "cancelled", "new", "qualified", "contacted", "converted", "junk"},
        "currency": {"usd", "eur", "egp"},
        "source_system": {"salesforce", "hubspot", "zoho", "pipedrive", "internal_crm", "manual_entry", "manual"},
        "country": {"usa", "us", "egypt", "eg", "united states", "uae", "gb"},
        "stage": {"prospecting", "qualified", "negotiation", "won", "lost", "contract_sent"},
        "lead_status": {"new", "qualified", "contacted", "junk", "converted"},
    }

    null_sensitive_fields = {
        "owner_id",
        "updated_at",
        "status",
        "Status",
        "source_record_id",
        "amount",
        "employee_count",
        "score",
        "company_id",
        "customer_id",
        "contact_id",
        "lead_id",
        "deal_id",
        "email",
        "email_address",
        "phone",
        "phone_number",
    }

    for version in VERSIONS:
        for entity in ENTITIES:
            arr = all_data[version][entity]
            for i in range(len(arr)):
                total_records += 1
                rec = arr[i]
                source = normalize_source(rec.get("source_system"))
                state.source_stats[source]["records"] += 1

                # Missing optional fields (entity-specific)
                missing_signals = OPTIONAL_BY_ENTITY.get(entity, [])
                for k in missing_signals:
                    optional_slots_total += 1
                    state.source_stats[source]["optional_slots_total"] += 1
                    if k not in rec:
                        optional_slots_missing += 1
                        state.source_stats[source]["optional_slots_missing"] += 1

                # Null values in non-key fields
                null_hit = False
                for k, v in rec.items():
                    if k in null_sensitive_fields and v is None:
                        null_hit = True
                        break
                if null_hit:
                    state.stats["null_non_key"] += 1
                    state.source_stats[source]["null_non_key"] += 1

                # Invalid emails / phones
                bad_contact = False
                email_keys = ["email", "email_address"]
                for ek in email_keys:
                    if ek in rec and rec[ek] not in [None, ""]:
                        val = str(rec[ek]).strip()
                        if not EMAIL_REGEX.match(val):
                            bad_contact = True
                phone_keys = ["phone", "phone_number"]
                for pk in phone_keys:
                    if pk in rec and rec[pk] not in [None, ""]:
                        if is_invalid_phone(rec[pk]):
                            bad_contact = True
                if bad_contact:
                    state.stats["invalid_email_phone"] += 1
                    state.source_stats[source]["invalid_email_phone"] += 1

                # Inconsistent casing
                for ck in ["status", "Status", "currency", "source_system", "country", "lead_status", "stage", "Stage"]:
                    if ck in rec and isinstance(rec[ck], str):
                        val = rec[ck]
                        norm = val.strip().lower()
                        canonical_key = ck.lower()
                        if canonical_key == "status":
                            allowed = known_case_values["status"]
                        elif canonical_key == "stage":
                            allowed = known_case_values["stage"]
                        elif canonical_key == "currency":
                            allowed = known_case_values["currency"]
                        elif canonical_key == "source_system":
                            allowed = known_case_values["source_system"]
                        elif canonical_key == "country":
                            allowed = known_case_values["country"]
                        elif canonical_key == "lead_status":
                            allowed = known_case_values["lead_status"]
                        else:
                            allowed = set()

                        if norm in allowed and val != norm:
                            state.stats["inconsistent_casing"] += 1
                            state.source_stats[source]["inconsistent_casing"] += 1
                            break

                # Mixed date formats
                date_vals = []
                for dk in ["created_at", "created_date", "updated_at", "last_synced_at", "deleted_at"]:
                    if dk in rec and rec[dk] not in [None, ""]:
                        date_vals.append(str(rec[dk]))
                        state.date_format_stats[detect_date_format(rec[dk])] += 1

                for dv in date_vals:
                    if "/" in dv or dv.isdigit() or ("T" not in dv and "-" in dv and ":" in dv):
                        state.stats["mixed_date_formats"] += 1
                        state.source_stats[source]["mixed_date_formats"] += 1
                        break

                # Field drift
                drift_hit = False
                for k in rec.keys():
                    if k in FIELD_DRIFT_KEYS:
                        drift_hit = True
                        break
                if drift_hit:
                    state.stats["field_name_drift"] += 1
                    state.source_stats[source]["field_name_drift"] += 1

                # Type inconsistencies
                type_bad = False
                if "amount" in rec and not isinstance(rec["amount"], (int, float)):
                    type_bad = True
                if "employee_count" in rec and not isinstance(rec["employee_count"], int):
                    type_bad = True
                if "score" in rec and not isinstance(rec["score"], int):
                    type_bad = True
                if type_bad:
                    state.stats["type_inconsistencies"] += 1
                    state.source_stats[source]["type_inconsistencies"] += 1

                # Conflicting statuses
                conflict = False
                is_deleted = rec.get("is_deleted")
                deleted_at = rec.get("deleted_at")
                status = rec.get("status") or rec.get("Status")
                if deleted_at and (is_deleted is False or is_deleted == 0):
                    conflict = True
                if deleted_at and isinstance(status, str) and status.lower() in ["active", "open"]:
                    conflict = True
                if conflict:
                    state.stats["conflicting_statuses"] += 1
                    state.source_stats[source]["conflicting_statuses"] += 1

                # Stale or inconsistent sync metadata
                stale = False
                if "sync_status" in rec and "last_synced_at" in rec:
                    sync_status = str(rec.get("sync_status"))
                    last_synced = parse_any_date(rec.get("last_synced_at"))
                    updated = parse_any_date(rec.get("updated_at"))
                    if last_synced is None:
                        stale = True
                    elif updated is not None:
                        delta = (to_naive_utc(updated) - to_naive_utc(last_synced)).days
                        if delta > 60:
                            stale = True
                    if sync_status.lower() in ["synced", "ok"] and stale:
                        state.stats["stale_sync"] += 1
                        state.source_stats[source]["stale_sync"] += 1
                    elif sync_status.lower() in ["failed", "stale"]:
                        state.stats["stale_sync"] += 1
                        state.source_stats[source]["stale_sync"] += 1

    state.stats["total_records"] = total_records
    state.stats["optional_slots_total"] = optional_slots_total
    state.stats["optional_slots_missing"] = optional_slots_missing


def print_report(all_data, state, strict_targets=False):
    print("CRM dataset validation report")
    print("=" * 70)

    print("Counts by version/entity")
    for version in VERSIONS:
        print(f"{version}:")
        for entity in ENTITIES:
            print(f"  - {entity}: {len(all_data[version][entity])}")

    print("\nRelationship integrity")
    valid = state.relationship_total - state.relationship_invalid
    if state.relationship_total == 0:
        ratio_bad = 0.0
    else:
        ratio_bad = (state.relationship_invalid / state.relationship_total) * 100.0
    print(f"  checked refs: {state.relationship_total}")
    print(f"  valid refs:   {valid}")
    print(f"  orphan refs:  {state.relationship_invalid} ({ratio_bad:.2f}%)")

    print("\nLogical duplicate indicators")
    total_records = max(1, state.logical_duplicate_stats["records_total"])
    explicit = state.logical_duplicate_stats["explicit_duplicate_of"]
    fuzzy = state.logical_duplicate_stats["fuzzy_duplicate_candidates"]
    print(f"  explicit duplicate_of: {explicit} ({(explicit / total_records) * 100.0:.2f}%)")
    print(f"  fuzzy duplicate candidates: {fuzzy} ({(fuzzy / total_records) * 100.0:.2f}%)")

    total = max(1, state.stats["total_records"])
    optional_total = max(1, state.stats["optional_slots_total"])

    print("\nMessiness ratios across full dataset")
    keys = [
        "missing_optional",
        "null_non_key",
        "invalid_email_phone",
        "inconsistent_casing",
        "mixed_date_formats",
        "field_name_drift",
        "type_inconsistencies",
        "conflicting_statuses",
        "stale_sync",
    ]
    for k in keys:
        if k == "missing_optional":
            pct = (state.stats["optional_slots_missing"] / optional_total) * 100.0
            print(f"  - {k}: {state.stats['optional_slots_missing']} missing slots of {optional_total} ({pct:.2f}%)")
            continue

        pct = (state.stats[k] / total) * 100.0
        print(f"  - {k}: {state.stats[k]} ({pct:.2f}%)")

    print("\nTarget guidance (approximate)")
    print("  - missing_optional: 10-20%")
    print("  - null_non_key: 5-10%")
    print("  - invalid_email_phone: 5-10%")
    print("  - inconsistent_casing: 10-20%")
    print("  - mixed_date_formats: 10-15%")
    print("  - field_name_drift: 5-10%")
    print("  - type_inconsistencies: 5-10%")
    print("  - conflicting_statuses: 3-8%")
    print("  - orphan_refs: 3-5%")
    print("  - stale_sync: 5-10%")

    # Emit explicit warnings when metrics drift outside desired bands.
    actuals = {
        "missing_optional": (state.stats["optional_slots_missing"] / optional_total) * 100.0,
        "null_non_key": (state.stats["null_non_key"] / total) * 100.0,
        "invalid_email_phone": (state.stats["invalid_email_phone"] / total) * 100.0,
        "inconsistent_casing": (state.stats["inconsistent_casing"] / total) * 100.0,
        "mixed_date_formats": (state.stats["mixed_date_formats"] / total) * 100.0,
        "field_name_drift": (state.stats["field_name_drift"] / total) * 100.0,
        "type_inconsistencies": (state.stats["type_inconsistencies"] / total) * 100.0,
        "conflicting_statuses": (state.stats["conflicting_statuses"] / total) * 100.0,
        "orphan_refs": ratio_bad,
        "stale_sync": (state.stats["stale_sync"] / total) * 100.0,
    }
    for metric, bounds in TARGET_BANDS.items():
        low, high = bounds
        value = actuals.get(metric, 0.0)
        if value < low or value > high:
            state.warn(f"{metric} out of target: {value:.2f}% (target {low:.0f}-{high:.0f}%)")

    print("\nDate format distribution")
    total_dates = sum(state.date_format_stats.values())
    if total_dates == 0:
        print("  none")
    else:
        for key in ["iso8601", "sql", "slash", "unix_str", "unix_int", "other", "missing"]:
            count = state.date_format_stats.get(key, 0)
            if count == 0:
                continue
            print(f"  - {key}: {count} ({(count / total_dates) * 100.0:.2f}%)")

    print("\nSource-based messiness")
    source_keys = sorted(state.source_stats.keys())
    for source in source_keys:
        rec_count = state.source_stats[source].get("records", 0)
        if rec_count == 0:
            continue
        src_optional_total = state.source_stats[source].get("optional_slots_total", 0)
        src_optional_missing = state.source_stats[source].get("optional_slots_missing", 0)
        miss = 0.0
        if src_optional_total > 0:
            miss = (src_optional_missing / src_optional_total) * 100.0
        bad_contact = (state.source_stats[source].get("invalid_email_phone", 0) / rec_count) * 100.0
        casing = (state.source_stats[source].get("inconsistent_casing", 0) / rec_count) * 100.0
        stale = (state.source_stats[source].get("stale_sync", 0) / rec_count) * 100.0
        print(f"  - {source}: n={rec_count}, missing={miss:.1f}%, invalid_contact={bad_contact:.1f}%, casing={casing:.1f}%, stale_sync={stale:.1f}%")

    print("\nErrors")
    if len(state.errors) == 0:
        print("  none")
    else:
        for err in state.errors:
            print("  - " + err)

    print("\nWarnings")
    if len(state.warnings) == 0:
        print("  none")
    else:
        for warn in state.warnings:
            print("  - " + warn)

    if len(state.errors) > 0:
        raise SystemExit(1)

    if strict_targets and len(state.warnings) > 0:
        raise SystemExit(2)


def main():
    parser = argparse.ArgumentParser(description="Validate messy CRM JSON datasets.")
    parser.add_argument(
        "--data-root",
        type=str,
        default="fastapi-crm-api/data",
        help="Path that contains v1/v2/v3 folders",
    )
    parser.add_argument(
        "--strict-targets",
        action="store_true",
        help="Exit with code 2 when metrics fall outside target guidance.",
    )
    args = parser.parse_args()

    data_root = Path(args.data_root)
    state = ValidationState()

    all_data = load_all(data_root, state)
    check_unique_ids(all_data, state)
    check_v3_volume(all_data, state)
    check_relationships(all_data, state)
    check_logical_duplicates(all_data, state)
    scan_messiness(all_data, state)
    print_report(all_data, state, strict_targets=args.strict_targets)


if __name__ == "__main__":
    main()
