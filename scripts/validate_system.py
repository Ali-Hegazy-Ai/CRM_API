import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(PROJECT_ROOT, "fastapi-crm-api")
DB_PATH = os.path.join(API_DIR, "data", "cdc_events.sqlite3")
DEFAULT_BASE_URL = "http://127.0.0.1:8000"

ENDPOINT_KEYS = {
    "customers": "data",
    "contacts": "contacts",
    "leads": "results",
    "deals": "data",
    "activities": "activities",
    "notes": "data",
    "companies": "companies",
}

DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y.%m.%d %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate CRM CDC/runtime system end-to-end.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--startup-timeout", type=int, default=35, help="Server startup timeout in seconds")
    parser.add_argument("--request-timeout", type=float, default=8.0, help="HTTP request timeout in seconds")
    parser.add_argument("--cdc-seconds", type=int, default=20, help="Duration for CDC continuity check")
    parser.add_argument("--force-contention", action="store_true", help="Run optional forced contention scenario")
    parser.add_argument("--contention-seconds", type=int, default=20, help="Duration for forced contention check")
    return parser.parse_args()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def _to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if value <= 0:
            return None
        return datetime.fromtimestamp(float(value), tz=timezone.utc)

    raw = str(value).strip()
    if raw == "":
        return None

    if raw.isdigit():
        return datetime.fromtimestamp(float(raw), tz=timezone.utc)

    iso_raw = raw
    if raw.endswith("Z"):
        iso_raw = raw.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(iso_raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed
    except ValueError:
        pass

    i = 0
    while i < len(DATE_FORMATS):
        try:
            parsed = datetime.strptime(raw, DATE_FORMATS[i]).replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            i = i + 1

    return None


def make_url(base_url: str, path: str, params: Optional[Dict[str, Any]] = None) -> str:
    base = base_url.rstrip("/")
    path_value = path
    if not path_value.startswith("/"):
        path_value = "/" + path_value

    if not params:
        return base + path_value

    filtered: Dict[str, Any] = {}
    for key in params:
        if params[key] is None:
            continue
        filtered[key] = params[key]

    query = urlencode(filtered)
    return base + path_value + "?" + query


def http_get_json(base_url: str, path: str, params: Optional[Dict[str, Any]], timeout: float) -> Dict[str, Any]:
    url = make_url(base_url, path, params)
    request = Request(url, headers={"Accept": "application/json"})

    try:
        response = urlopen(request, timeout=timeout)
    except HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {exc.code} for {url}: {body}")
    except URLError as exc:
        raise RuntimeError(f"Request failed for {url}: {exc}")

    try:
        raw = response.read().decode("utf-8", errors="replace")
        payload = json.loads(raw)
    finally:
        response.close()

    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected JSON object from {url}")

    return payload


def extract_items(endpoint: str, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    key = ENDPOINT_KEYS.get(endpoint, "data")
    value = payload.get(key)
    if isinstance(value, list):
        result: List[Dict[str, Any]] = []
        i = 0
        while i < len(value):
            row = value[i]
            if isinstance(row, dict):
                result.append(row)
            i = i + 1
        return result

    return []


def get_metric_snapshot(base_url: str, timeout: float) -> Dict[str, Any]:
    payload = http_get_json(base_url, "/metrics", None, timeout)
    generator = payload.get("generator", {})
    if not isinstance(generator, dict):
        generator = {}

    return {
        "current_state_count": int(payload.get("current_state_count", 0)),
        "last_event_id": int(payload.get("last_event_id", 0)),
        "cycle_counter": int(generator.get("cycle_counter", 0)),
        "skipped_cycles": int(generator.get("skipped_cycles", 0)),
    }


def wait_for_server(base_url: str, timeout_seconds: int, request_timeout: float) -> bool:
    start_time = time.time()
    while True:
        try:
            payload = http_get_json(base_url, "/health", None, request_timeout)
            if payload.get("status") == "healthy":
                return True
        except Exception:
            pass

        if time.time() - start_time > timeout_seconds:
            return False

        time.sleep(0.4)


def start_server(base_url: str, startup_timeout: int, env_overrides: Dict[str, str], request_timeout: float) -> subprocess.Popen:
    env = os.environ.copy()
    for key in env_overrides:
        env[key] = str(env_overrides[key])

    process = subprocess.Popen(
        [sys.executable, "main.py"],
        cwd=API_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    started = wait_for_server(base_url, startup_timeout, request_timeout)
    if started:
        return process

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=8)

    raise RuntimeError("Server did not become healthy within startup timeout")


def stop_server(process: Optional[subprocess.Popen]) -> None:
    if process is None:
        return

    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=10)
        return
    except subprocess.TimeoutExpired:
        pass

    process.kill()
    process.wait(timeout=10)


def cdc_continuity_check(base_url: str, request_timeout: float, seconds_to_run: int) -> Tuple[bool, Dict[str, Any]]:
    details: Dict[str, Any] = {}

    metrics = get_metric_snapshot(base_url, request_timeout)
    cursor = int(metrics["last_event_id"])
    details["start_event_id"] = cursor

    event_ids: List[int] = []
    iterations = 0
    finish_time = time.time() + float(seconds_to_run)

    while time.time() < finish_time:
        response = http_get_json(
            base_url,
            "/changes",
            {
                "since": str(cursor),
                "limit": 200,
            },
            request_timeout,
        )

        events = response.get("events", [])
        if not isinstance(events, list):
            events = []

        i = 0
        while i < len(events):
            event = events[i]
            if isinstance(event, dict):
                event_id = int(event.get("event_id", 0))
                if event_id > 0:
                    event_ids.append(event_id)
                    cursor = event_id
            i = i + 1

        http_get_json(base_url, "/customers", {"version": "v3", "page": 1, "limit": 20}, request_timeout)
        http_get_json(base_url, "/leads", {"version": "v3", "page": 1, "limit": 20}, request_timeout)

        iterations = iterations + 1
        time.sleep(0.1)

    details["iterations"] = iterations
    details["observed_events"] = len(event_ids)
    details["end_cursor"] = cursor

    duplicate_count = 0
    seen: Dict[int, int] = {}
    i = 0
    while i < len(event_ids):
        value = event_ids[i]
        seen[value] = seen.get(value, 0) + 1
        i = i + 1

    for key in seen:
        if seen[key] > 1:
            duplicate_count = duplicate_count + 1

    gap_count = 0
    max_gap = 0
    i = 1
    while i < len(event_ids):
        gap = event_ids[i] - event_ids[i - 1]
        if gap != 1:
            gap_count = gap_count + 1
            if gap > max_gap:
                max_gap = gap
        i = i + 1

    details["duplicate_ids"] = duplicate_count
    details["non_unit_gaps"] = gap_count
    details["max_gap"] = max_gap

    ok = len(event_ids) > 0 and duplicate_count == 0 and gap_count == 0
    return ok, details


def incremental_endpoints_check(base_url: str, request_timeout: float) -> Tuple[bool, Dict[str, Any]]:
    details: Dict[str, Any] = {}

    since_dt = _now_utc() - timedelta(minutes=20)
    since_text = _to_iso(since_dt)
    details["since"] = since_text

    endpoints = ["customers", "contacts", "leads", "deals", "activities", "notes", "companies"]
    per_endpoint: List[Dict[str, Any]] = []

    all_good = True
    i = 0
    while i < len(endpoints):
        endpoint = endpoints[i]

        payload_false = http_get_json(
            base_url,
            f"/{endpoint}",
            {
                "version": "v3",
                "updated_after": since_text,
                "include_deleted": "false",
                "page": 1,
                "limit": 100,
            },
            request_timeout,
        )
        payload_true = http_get_json(
            base_url,
            f"/{endpoint}",
            {
                "version": "v3",
                "updated_after": since_text,
                "include_deleted": "true",
                "page": 1,
                "limit": 100,
            },
            request_timeout,
        )

        rows_false = extract_items(endpoint, payload_false)
        rows_true = extract_items(endpoint, payload_true)

        include_deleted_ok = len(rows_true) >= len(rows_false)

        sorted_ok = True
        filter_ok = True
        unparsed_count = 0

        parsed_times: List[datetime] = []
        j = 0
        while j < len(rows_true):
            row = rows_true[j]
            updated_at = row.get("updated_at")
            parsed = parse_timestamp(updated_at)
            if parsed is None:
                unparsed_count = unparsed_count + 1
            else:
                parsed_times.append(parsed)
                if parsed <= since_dt:
                    filter_ok = False
            j = j + 1

        j = 1
        while j < len(parsed_times):
            if parsed_times[j] < parsed_times[j - 1]:
                sorted_ok = False
                break
            j = j + 1

        endpoint_ok = include_deleted_ok and sorted_ok and filter_ok
        if not endpoint_ok:
            all_good = False

        per_endpoint.append(
            {
                "endpoint": endpoint,
                "count_excluding_deleted": len(rows_false),
                "count_including_deleted": len(rows_true),
                "include_deleted_not_smaller": include_deleted_ok,
                "sorted_parseable_timestamps": sorted_ok,
                "filter_respected_for_parseable_timestamps": filter_ok,
                "unparsed_timestamp_count": unparsed_count,
            }
        )

        i = i + 1

    customers_page1 = http_get_json(
        base_url,
        "/customers",
        {
            "version": "v3",
            "updated_after": since_text,
            "include_deleted": "true",
            "page": 1,
            "limit": 25,
        },
        request_timeout,
    )
    customers_page2 = http_get_json(
        base_url,
        "/customers",
        {
            "version": "v3",
            "updated_after": since_text,
            "include_deleted": "true",
            "page": 2,
            "limit": 25,
        },
        request_timeout,
    )

    rows_page1 = extract_items("customers", customers_page1)
    rows_page2 = extract_items("customers", customers_page2)

    ids_page1: List[str] = []
    ids_page2: List[str] = []

    i = 0
    while i < len(rows_page1):
        ids_page1.append(str(rows_page1[i].get("id", "")))
        i = i + 1

    i = 0
    while i < len(rows_page2):
        ids_page2.append(str(rows_page2[i].get("id", "")))
        i = i + 1

    overlap = 0
    i = 0
    while i < len(ids_page1):
        if ids_page1[i] in ids_page2:
            overlap = overlap + 1
        i = i + 1

    pagination_ok = overlap == 0
    if not pagination_ok:
        all_good = False

    details["per_endpoint"] = per_endpoint
    details["customer_page_overlap"] = overlap
    details["customer_page1_count"] = len(rows_page1)
    details["customer_page2_count"] = len(rows_page2)

    return all_good, details


def _find_entity_in_incremental_pages(
    base_url: str,
    endpoint: str,
    entity_id: str,
    since_text: str,
    include_deleted: bool,
    request_timeout: float,
    max_pages: int,
) -> Dict[str, Any]:
    page = 1
    while page <= max_pages:
        payload = http_get_json(
            base_url,
            f"/{endpoint}",
            {
                "version": "v3",
                "updated_after": since_text,
                "include_deleted": "true" if include_deleted else "false",
                "page": page,
                "limit": 100,
            },
            request_timeout,
        )

        rows = extract_items(endpoint, payload)
        if len(rows) == 0:
            return {"found": False, "page": -1, "is_deleted": None}

        i = 0
        while i < len(rows):
            row_id = str(rows[i].get("id", ""))
            if row_id == entity_id:
                return {
                    "found": True,
                    "page": page,
                    "is_deleted": rows[i].get("is_deleted"),
                }
            i = i + 1

        page = page + 1

    return {"found": False, "page": -1, "is_deleted": None}


def soft_delete_behavior_check(base_url: str, request_timeout: float) -> Tuple[bool, Dict[str, Any]]:
    details: Dict[str, Any] = {}

    feed = http_get_json(base_url, "/changes", {"operation": "delete", "limit": 20}, request_timeout)
    events = feed.get("events", [])
    if not isinstance(events, list) or len(events) == 0:
        details["error"] = "No delete events found"
        return False, details

    target_event: Optional[Dict[str, Any]] = None
    i = len(events) - 1
    while i >= 0:
        candidate = events[i]
        if isinstance(candidate, dict):
            entity_type = str(candidate.get("entity_type", ""))
            if entity_type in ENDPOINT_KEYS:
                target_event = candidate
                break
        i = i - 1

    if target_event is None:
        details["error"] = "No delete event for supported endpoint types"
        return False, details

    entity_type = str(target_event.get("entity_type", ""))
    entity_id = str(target_event.get("entity_id", ""))
    event_id = int(target_event.get("event_id", 0))
    event_timestamp_raw = target_event.get("timestamp")
    event_timestamp = parse_timestamp(event_timestamp_raw)

    if event_timestamp is None:
        event_timestamp = _now_utc()

    since_dt = event_timestamp - timedelta(minutes=2)
    since_text = _to_iso(since_dt)

    replay = http_get_json(
        base_url,
        "/changes",
        {
            "since": str(max(0, event_id - 1)),
            "limit": 10,
        },
        request_timeout,
    )

    replay_events = replay.get("events", [])
    replay_contains_target = False
    if isinstance(replay_events, list):
        i = 0
        while i < len(replay_events):
            row = replay_events[i]
            if isinstance(row, dict) and int(row.get("event_id", 0)) == event_id:
                replay_contains_target = True
                break
            i = i + 1

    found_true = _find_entity_in_incremental_pages(
        base_url,
        entity_type,
        entity_id,
        since_text,
        True,
        request_timeout,
        30,
    )
    found_false = _find_entity_in_incremental_pages(
        base_url,
        entity_type,
        entity_id,
        since_text,
        False,
        request_timeout,
        30,
    )

    sqlite_deleted = None
    sqlite_updated_at = None

    if os.path.isfile(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT is_deleted, updated_at FROM current_state WHERE entity_type = ? AND entity_id = ?",
                (entity_type, entity_id),
            ).fetchone()
            if row is not None:
                sqlite_deleted = int(row[0])
                sqlite_updated_at = row[1]
        finally:
            conn.close()

    details["entity_type"] = entity_type
    details["entity_id"] = entity_id
    details["event_id"] = event_id
    details["event_timestamp"] = str(event_timestamp_raw)
    details["query_since"] = since_text
    details["found_with_include_deleted"] = bool(found_true.get("found"))
    details["include_deleted_page"] = int(found_true.get("page", -1))
    details["payload_is_deleted"] = found_true.get("is_deleted")
    details["found_without_include_deleted"] = bool(found_false.get("found"))
    details["replay_contains_target_event"] = replay_contains_target
    details["sqlite_is_deleted"] = sqlite_deleted
    details["sqlite_updated_at"] = sqlite_updated_at

    ok = (
        replay_contains_target
        and bool(found_true.get("found"))
        and not bool(found_false.get("found"))
        and sqlite_deleted == 1
    )
    return ok, details


def restart_persistence_check(
    base_url: str,
    request_timeout: float,
    startup_timeout: int,
    running_process: subprocess.Popen,
    normal_env: Dict[str, str],
) -> Tuple[bool, Dict[str, Any], subprocess.Popen]:
    details: Dict[str, Any] = {}

    before_metrics = get_metric_snapshot(base_url, request_timeout)
    details["before_current_state_count"] = before_metrics["current_state_count"]
    details["before_last_event_id"] = before_metrics["last_event_id"]
    details["before_cycle_counter"] = before_metrics["cycle_counter"]

    stop_server(running_process)
    restarted_process = start_server(base_url, startup_timeout, normal_env, request_timeout)

    after_metrics = get_metric_snapshot(base_url, request_timeout)
    details["after_current_state_count"] = after_metrics["current_state_count"]
    details["after_last_event_id"] = after_metrics["last_event_id"]
    details["after_cycle_counter"] = after_metrics["cycle_counter"]

    continuity = http_get_json(
        base_url,
        "/changes",
        {
            "since": str(before_metrics["last_event_id"]),
            "limit": 5,
        },
        request_timeout,
    )

    continuity_events = continuity.get("events", [])
    first_after_restart = None
    if isinstance(continuity_events, list) and len(continuity_events) > 0:
        first_after_restart = int(continuity_events[0].get("event_id", 0))

    duplicate_pairs = -1
    total_rows = -1
    distinct_pairs = -1

    if os.path.isfile(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        try:
            cursor = conn.cursor()
            row1 = cursor.execute("SELECT COUNT(*) FROM current_state").fetchone()
            row2 = cursor.execute(
                "SELECT COUNT(*) FROM (SELECT entity_type, entity_id FROM current_state GROUP BY entity_type, entity_id)"
            ).fetchone()
            if row1 is not None:
                total_rows = int(row1[0])
            if row2 is not None:
                distinct_pairs = int(row2[0])
            if total_rows >= 0 and distinct_pairs >= 0:
                duplicate_pairs = total_rows - distinct_pairs
        finally:
            conn.close()

    details["continuity_first_event_after_restart"] = first_after_restart
    details["current_state_total_rows"] = total_rows
    details["current_state_distinct_pairs"] = distinct_pairs
    details["current_state_duplicate_pairs"] = duplicate_pairs

    continuity_ok = first_after_restart is None or first_after_restart > before_metrics["last_event_id"]

    ok = (
        after_metrics["current_state_count"] > 0
        and after_metrics["last_event_id"] >= before_metrics["last_event_id"]
        and continuity_ok
        and duplicate_pairs == 0
    )

    return ok, details, restarted_process


def force_contention_check(base_url: str, request_timeout: float, seconds_to_run: int) -> Tuple[bool, Dict[str, Any]]:
    details: Dict[str, Any] = {}

    before_metrics = get_metric_snapshot(base_url, request_timeout)

    latencies_ms: List[float] = []
    start = time.time()
    iterations = 0

    while time.time() - start < float(seconds_to_run):
        t0 = time.time()
        http_get_json(base_url, "/health", None, request_timeout)
        elapsed_ms = (time.time() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

        http_get_json(base_url, "/customers", {"version": "v3", "page": 1, "limit": 20}, request_timeout)
        http_get_json(base_url, "/leads", {"version": "v3", "page": 1, "limit": 20}, request_timeout)
        http_get_json(base_url, "/activities", {"version": "v3", "page": 1, "limit": 20}, request_timeout)
        iterations = iterations + 1

    after_metrics = get_metric_snapshot(base_url, request_timeout)

    min_latency = 0.0
    avg_latency = 0.0
    max_latency = 0.0

    if len(latencies_ms) > 0:
        min_latency = min(latencies_ms)
        max_latency = max(latencies_ms)
        avg_latency = sum(latencies_ms) / float(len(latencies_ms))

    skipped_delta = after_metrics["skipped_cycles"] - before_metrics["skipped_cycles"]
    cycle_delta = after_metrics["cycle_counter"] - before_metrics["cycle_counter"]

    details["iterations"] = iterations
    details["duration_seconds"] = round(time.time() - start, 2)
    details["cycle_counter_before"] = before_metrics["cycle_counter"]
    details["cycle_counter_after"] = after_metrics["cycle_counter"]
    details["cycle_delta"] = cycle_delta
    details["skipped_before"] = before_metrics["skipped_cycles"]
    details["skipped_after"] = after_metrics["skipped_cycles"]
    details["skipped_delta"] = skipped_delta
    details["health_latency_min_ms"] = round(min_latency, 2)
    details["health_latency_avg_ms"] = round(avg_latency, 2)
    details["health_latency_max_ms"] = round(max_latency, 2)

    ok = skipped_delta > 0
    return ok, details


def print_result(name: str, ok: bool, details: Dict[str, Any]) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"[{status}] {name}")
    print(json.dumps(details, indent=2, ensure_ascii=True))


def main() -> int:
    args = parse_args()

    normal_env = {
        "GEN_INTERVAL_SECONDS": "1",
        "GEN_MAX_OPS_PER_CYCLE": "12",
    }

    contention_env = {
        "GEN_INTERVAL_SECONDS": "0.1",
        "GEN_MAX_OPS_PER_CYCLE": "50",
        "CRM_ENABLE_LEGACY_STREAM_ENGINE": "1",
    }

    core_results: List[Tuple[str, bool, Dict[str, Any]]] = []
    optional_results: List[Tuple[str, bool, Dict[str, Any]]] = []

    active_process: Optional[subprocess.Popen] = None

    try:
        print("Starting API server for validation...")
        active_process = start_server(args.base_url, args.startup_timeout, normal_env, args.request_timeout)
        print("Server is healthy.")

        print("Running CDC continuity check...")
        cdc_ok, cdc_details = cdc_continuity_check(args.base_url, args.request_timeout, args.cdc_seconds)
        core_results.append(("CDC continuity", cdc_ok, cdc_details))
        print_result("CDC continuity", cdc_ok, cdc_details)

        print("Running incremental endpoint checks...")
        inc_ok, inc_details = incremental_endpoints_check(args.base_url, args.request_timeout)
        core_results.append(("Incremental endpoints", inc_ok, inc_details))
        print_result("Incremental endpoints", inc_ok, inc_details)

        print("Running soft delete behavior check...")
        soft_ok, soft_details = soft_delete_behavior_check(args.base_url, args.request_timeout)
        core_results.append(("Soft delete behavior", soft_ok, soft_details))
        print_result("Soft delete behavior", soft_ok, soft_details)

        print("Running restart persistence check...")
        restart_ok, restart_details, active_process = restart_persistence_check(
            args.base_url,
            args.request_timeout,
            args.startup_timeout,
            active_process,
            normal_env,
        )
        core_results.append(("Restart persistence", restart_ok, restart_details))
        print_result("Restart persistence", restart_ok, restart_details)

        if args.force_contention:
            print("Running forced contention scenario...")
            stop_server(active_process)
            active_process = start_server(args.base_url, args.startup_timeout, contention_env, args.request_timeout)
            contention_ok, contention_details = force_contention_check(
                args.base_url,
                args.request_timeout,
                args.contention_seconds,
            )
            optional_results.append(("Forced contention skip test", contention_ok, contention_details))
            print_result("Forced contention skip test", contention_ok, contention_details)

    except Exception as exc:
        print("[FAIL] Validation runner crashed")
        print(str(exc))
        return 1
    finally:
        stop_server(active_process)

    print("\nValidation summary")
    print("------------------")

    core_passed = True
    i = 0
    while i < len(core_results):
        name, ok, _ = core_results[i]
        print(f"{'PASS' if ok else 'FAIL'} - {name}")
        if not ok:
            core_passed = False
        i = i + 1

    if len(optional_results) > 0:
        print("\nOptional checks")
        print("---------------")
        i = 0
        while i < len(optional_results):
            name, ok, _ = optional_results[i]
            print(f"{'PASS' if ok else 'WARN'} - {name}")
            i = i + 1

    print(f"\nFinished at {_now_iso()}")

    if core_passed:
        print("Core validation passed.")
        return 0

    print("Core validation failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
