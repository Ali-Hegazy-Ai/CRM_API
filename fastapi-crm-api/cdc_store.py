"""SQLite-backed append-only CDC event storage for the CRM mock API."""

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y.%m.%d %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_timestamp(value: Any) -> Optional[str]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        if value > 0:
            parsed = datetime.fromtimestamp(float(value), tz=timezone.utc)
            return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        return None

    if not isinstance(value, str):
        return None

    raw = value.strip()
    if not raw:
        return None

    if raw.isdigit():
        parsed = datetime.fromtimestamp(float(raw), tz=timezone.utc)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")

    try:
        iso_raw = raw.replace("Z", "+00:00") if raw.endswith("Z") else raw
        parsed = datetime.fromisoformat(iso_raw)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        else:
            parsed = parsed.astimezone(timezone.utc)
        return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass

    for pattern in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(raw, pattern).replace(tzinfo=timezone.utc)
            return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    return None


class CdcStore:
    """Simple SQLite event log with monotonic integer event IDs."""

    def __init__(self, db_path: Optional[str] = None):
        base_dir = Path(__file__).resolve().parent
        self.db_path = Path(db_path) if db_path else (base_dir / "data" / "cdc_events.sqlite3")
        self._lock = threading.Lock()
        self._connection: Optional[sqlite3.Connection] = None

    def initialize(self) -> None:
        with self._lock:
            if self._connection is not None:
                return

            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._connection.row_factory = sqlite3.Row

            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS cdc_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    payload TEXT NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS current_state (
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_deleted INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY(entity_type, entity_id)
                )
                """
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_cdc_events_timestamp ON cdc_events(timestamp)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_cdc_events_entity_type ON cdc_events(entity_type)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_cdc_events_operation ON cdc_events(operation)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_current_state_entity_type ON current_state(entity_type)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_current_state_updated_at ON current_state(updated_at)"
            )
            self._connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_current_state_is_deleted ON current_state(is_deleted)"
            )
            self._connection.commit()

    def _require_connection(self) -> sqlite3.Connection:
        self.initialize()
        assert self._connection is not None
        return self._connection

    def _normalize_operation(self, operation: str) -> str:
        op = str(operation).strip().lower()
        if op == "activity":
            op = "update"
        if op not in {"create", "update", "delete"}:
            raise ValueError("Invalid operation filter; use create, update, or delete")
        return op

    def _normalize_entity_type(self, entity_type: str) -> str:
        normalized = str(entity_type).strip().lower()
        if not normalized:
            raise ValueError("entity_type is required")
        return normalized

    def _normalize_entity_id(self, entity_id: Any) -> str:
        normalized = "" if entity_id is None else str(entity_id).strip()
        if not normalized:
            raise ValueError("entity_id is required")
        return normalized

    def _parse_cursor(self, since: Optional[str]) -> Tuple[Optional[int], Optional[str]]:
        if since is None:
            return None, None

        raw = str(since).strip()
        if not raw:
            return None, None

        if raw.isdigit():
            return int(raw), None

        parsed = _parse_timestamp(raw)
        if parsed is None:
            raise ValueError("Invalid 'since' value; use event_id or a valid timestamp")
        return None, parsed

    def _row_to_event(self, row: sqlite3.Row) -> Dict[str, Any]:
        payload = {}
        payload_raw = row["payload"]
        if payload_raw:
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload = {}

        event_id = int(row["event_id"])
        entity_type = str(row["entity_type"])
        entity_id = str(row["entity_id"])
        operation = str(row["operation"])
        timestamp = str(row["timestamp"])

        # Keep legacy aliases so old stream endpoints remain backward-compatible.
        return {
            "event_id": event_id,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "operation": operation,
            "timestamp": timestamp,
            "payload": payload,
            "sequence": event_id,
            "event_type": operation,
            "entity": entity_type[:-1] if entity_type.endswith("s") else entity_type,
            "id": entity_id,
            "data": payload,
        }

    def _row_to_current_state(self, row: sqlite3.Row) -> Dict[str, Any]:
        payload: Dict[str, Any] = {}
        payload_raw = row["data"]
        if payload_raw:
            try:
                loaded = json.loads(payload_raw)
                if isinstance(loaded, dict):
                    payload = loaded
                else:
                    payload = {"value": loaded}
            except json.JSONDecodeError:
                payload = {}

        entity_type = str(row["entity_type"])
        entity_id = str(row["entity_id"])
        updated_at = str(row["updated_at"])
        is_deleted = bool(int(row["is_deleted"]))

        if "id" not in payload:
            payload["id"] = entity_id

        return {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "updated_at": updated_at,
            "is_deleted": is_deleted,
            "data": payload,
        }

    def append_event(
        self,
        entity_type: str,
        entity_id: Any,
        operation: str,
        payload: Dict[str, Any],
        timestamp: Optional[str] = None,
    ) -> Dict[str, Any]:
        conn = self._require_connection()

        operation_value = self._normalize_operation(operation)
        ts = _parse_timestamp(timestamp) or _now_iso()
        safe_entity_type = self._normalize_entity_type(entity_type)
        safe_entity_id = self._normalize_entity_id(entity_id)

        payload_value: Dict[str, Any]
        if isinstance(payload, dict):
            payload_value = payload
        else:
            payload_value = {"value": payload}

        payload_json = json.dumps(
            payload_value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

        with self._lock:
            cursor = conn.execute(
                """
                INSERT INTO cdc_events(entity_type, entity_id, operation, timestamp, payload)
                VALUES (?, ?, ?, ?, ?)
                """,
                (safe_entity_type, safe_entity_id, operation_value, ts, payload_json),
            )
            conn.commit()
            new_id = int(cursor.lastrowid)

        return {
            "event_id": new_id,
            "entity_type": safe_entity_type,
            "entity_id": safe_entity_id,
            "operation": operation_value,
            "timestamp": ts,
            "payload": payload_value,
            "sequence": new_id,
            "event_type": operation_value,
            "entity": safe_entity_type[:-1] if safe_entity_type.endswith("s") else safe_entity_type,
            "id": safe_entity_id,
            "data": payload_value,
        }

    def count_current_state(self) -> int:
        conn = self._require_connection()
        with self._lock:
            row = conn.execute("SELECT COUNT(*) AS count_value FROM current_state").fetchone()
        if row is None:
            return 0
        return int(row["count_value"])

    def get_last_event_id(self) -> int:
        conn = self._require_connection()
        with self._lock:
            row = conn.execute("SELECT MAX(event_id) AS last_event_id FROM cdc_events").fetchone()
        if row is None or row["last_event_id"] is None:
            return 0
        return int(row["last_event_id"])

    def upsert_current_state(
        self,
        entity_type: str,
        entity_id: Any,
        data: Dict[str, Any],
        updated_at: Optional[str] = None,
        is_deleted: bool = False,
    ) -> Dict[str, Any]:
        conn = self._require_connection()

        safe_entity_type = self._normalize_entity_type(entity_type)
        safe_entity_id = self._normalize_entity_id(entity_id)
        ts = _parse_timestamp(updated_at) or _now_iso()

        payload_value: Dict[str, Any]
        if isinstance(data, dict):
            payload_value = data
        else:
            payload_value = {"value": data}

        payload_json = json.dumps(
            payload_value,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

        with self._lock:
            conn.execute(
                """
                INSERT INTO current_state(entity_type, entity_id, data, updated_at, is_deleted)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id)
                DO UPDATE SET
                    data = excluded.data,
                    updated_at = excluded.updated_at,
                    is_deleted = excluded.is_deleted
                """,
                (safe_entity_type, safe_entity_id, payload_json, ts, 1 if is_deleted else 0),
            )
            conn.commit()

        return {
            "entity_type": safe_entity_type,
            "entity_id": safe_entity_id,
            "updated_at": ts,
            "is_deleted": bool(is_deleted),
            "data": payload_value,
        }

    def soft_delete(
        self,
        entity_type: str,
        entity_id: Any,
        data: Optional[Dict[str, Any]] = None,
        updated_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self.get_entity(entity_type=entity_type, entity_id=entity_id, include_deleted=True)
        base_payload: Dict[str, Any] = {}
        if existing and isinstance(existing.get("data"), dict):
            base_payload = dict(existing.get("data", {}))
        if isinstance(data, dict):
            base_payload.update(data)

        ts = _parse_timestamp(updated_at) or _now_iso()
        base_payload["is_deleted"] = True
        base_payload["deleted_at"] = ts

        return self.upsert_current_state(
            entity_type=entity_type,
            entity_id=entity_id,
            data=base_payload,
            updated_at=ts,
            is_deleted=True,
        )

    def get_entity(
        self,
        entity_type: str,
        entity_id: Any,
        include_deleted: bool = False,
    ) -> Optional[Dict[str, Any]]:
        conn = self._require_connection()
        safe_entity_type = self._normalize_entity_type(entity_type)
        safe_entity_id = self._normalize_entity_id(entity_id)

        query = "SELECT entity_type, entity_id, data, updated_at, is_deleted FROM current_state WHERE entity_type = ? AND entity_id = ?"
        params: List[Any] = [safe_entity_type, safe_entity_id]
        if not include_deleted:
            query = query + " AND is_deleted = 0"

        with self._lock:
            row = conn.execute(query, params).fetchone()

        if row is None:
            return None
        return self._row_to_current_state(row)

    def list_current_state(
        self,
        entity_type: Optional[str] = None,
        updated_after: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        conn = self._require_connection()
        safe_limit = max(1, min(int(limit), 20000))

        filters = []
        params: List[Any] = []

        if entity_type:
            filters.append("entity_type = ?")
            params.append(self._normalize_entity_type(entity_type))

        parsed_updated_after = _parse_timestamp(updated_after) if updated_after else None
        if updated_after and parsed_updated_after is None:
            raise ValueError("Invalid 'updated_after' value; use a valid timestamp")
        if parsed_updated_after is not None:
            filters.append("updated_at > ?")
            params.append(parsed_updated_after)

        if not include_deleted:
            filters.append("is_deleted = 0")

        query = "SELECT entity_type, entity_id, data, updated_at, is_deleted FROM current_state"
        if len(filters) > 0:
            query = query + " WHERE " + " AND ".join(filters)
        query = query + " ORDER BY updated_at ASC, entity_id ASC LIMIT ?"
        params.append(safe_limit)

        with self._lock:
            rows = conn.execute(query, params).fetchall()

        results = []
        for row in rows:
            results.append(self._row_to_current_state(row))
        return results

    def list_events(
        self,
        since: Optional[str] = None,
        limit: int = 100,
        entity_type: Optional[str] = None,
        operation: Optional[str] = None,
        latest_when_no_since: bool = False,
    ) -> List[Dict[str, Any]]:
        conn = self._require_connection()
        safe_limit = max(1, min(int(limit), 5000))

        since_event_id, since_timestamp = self._parse_cursor(since)

        filters = []
        params: List[Any] = []

        if since_event_id is not None:
            filters.append("event_id > ?")
            params.append(since_event_id)
        elif since_timestamp is not None:
            filters.append("timestamp > ?")
            params.append(since_timestamp)

        if entity_type:
            filters.append("LOWER(entity_type) = ?")
            params.append(str(entity_type).strip().lower())

        if operation:
            filters.append("operation = ?")
            params.append(self._normalize_operation(operation))

        query = "SELECT event_id, entity_type, entity_id, operation, timestamp, payload FROM cdc_events"

        if len(filters) > 0:
            query = query + " WHERE " + " AND ".join(filters)

        use_latest = latest_when_no_since and since_event_id is None and since_timestamp is None
        if use_latest:
            query = query + " ORDER BY event_id DESC LIMIT ?"
        else:
            query = query + " ORDER BY event_id ASC LIMIT ?"
        params.append(safe_limit)

        with self._lock:
            rows = conn.execute(query, params).fetchall()

        events = []
        for row in rows:
            events.append(self._row_to_event(row))

        if use_latest:
            events.reverse()

        return events


cdc_store = CdcStore()
