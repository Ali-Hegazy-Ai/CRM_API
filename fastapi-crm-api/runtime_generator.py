"""Runtime CRM record generator service with non-blocking async cycles."""

import asyncio
import logging
import os
import random
from typing import Any, Dict, Optional

from stream_engine import (
    create_entity,
    delete_entity,
    is_mutation_lock_busy,
    list_entities,
    update_entity,
)

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 5.0
_DEFAULT_MAX_OPS_PER_CYCLE = 6
_MIN_INTERVAL_SECONDS = 0.1
_MAX_INTERVAL_SECONDS = 300.0
_MIN_OPS_PER_CYCLE = 1
_MAX_OPS_PER_CYCLE = 100


def _read_float_env(name: str, default_value: float, min_value: float, max_value: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default_value

    try:
        parsed_value = float(str(raw_value).strip())
    except ValueError:
        return default_value

    if parsed_value < min_value:
        return min_value
    if parsed_value > max_value:
        return max_value
    return parsed_value


def _read_int_env(name: str, default_value: int, min_value: int, max_value: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default_value

    try:
        parsed_value = int(str(raw_value).strip())
    except ValueError:
        return default_value

    if parsed_value < min_value:
        return min_value
    if parsed_value > max_value:
        return max_value
    return parsed_value


def _entity_id_field(entity: str) -> str:
    mapping = {
        "customers": "customer_id",
        "contacts": "contact_id",
        "leads": "lead_id",
        "deals": "deal_id",
        "activities": "activity_id",
        "notes": "note_id",
        "companies": "company_id",
    }
    return mapping.get(entity, "id")


def _extract_entity_id(entity: str, record: Dict[str, Any]) -> Optional[str]:
    value = record.get("id")
    if value is None:
        value = record.get(_entity_id_field(entity))
    if value is None:
        return None

    normalized = str(value).strip()
    if not normalized:
        return None
    return normalized


class RuntimeGeneratorService:
    """Periodic runtime mutation generator for v3 records."""

    def __init__(self) -> None:
        self.interval_seconds = _DEFAULT_INTERVAL_SECONDS
        self.max_ops_per_cycle = _DEFAULT_MAX_OPS_PER_CYCLE
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._cycle_counter = 0
        self._skipped_cycles = 0
        self._last_cycle_stats: Dict[str, Any] = {
            "cycle": -1,
            "skipped": False,
            "create": 0,
            "update": 0,
            "delete": 0,
        }

    def reload_config(self) -> None:
        self.interval_seconds = _read_float_env(
            name="GEN_INTERVAL_SECONDS",
            default_value=_DEFAULT_INTERVAL_SECONDS,
            min_value=_MIN_INTERVAL_SECONDS,
            max_value=_MAX_INTERVAL_SECONDS,
        )
        self.max_ops_per_cycle = _read_int_env(
            name="GEN_MAX_OPS_PER_CYCLE",
            default_value=_DEFAULT_MAX_OPS_PER_CYCLE,
            min_value=_MIN_OPS_PER_CYCLE,
            max_value=_MAX_OPS_PER_CYCLE,
        )

    async def start(self) -> None:
        if self._task and not self._task.done():
            return

        self.reload_config()
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(), name="crm_runtime_generator")

        logger.info(
            "Runtime generator started: interval_seconds=%s max_ops_per_cycle=%s",
            self.interval_seconds,
            self.max_ops_per_cycle,
        )

    async def stop(self) -> None:
        self._stop_event.set()
        running_task = self._task
        self._task = None

        if running_task and not running_task.done():
            running_task.cancel()
            await asyncio.gather(running_task, return_exceptions=True)

    async def _run_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self.interval_seconds)
                await self.run_cycle()
        except asyncio.CancelledError:
            return

    def _choose_operation(self) -> str:
        roll = random.random()
        if roll < 0.70:
            return "update"
        if roll < 0.90:
            return "create"
        return "delete"

    async def _pick_existing_record(self, entity: str) -> Optional[Dict[str, Any]]:
        records = await list_entities(
            entity=entity,
            version="v3",
            include_deleted=False,
            limit=4000,
        )
        if not records:
            return None
        return random.choice(records)

    async def _run_create(self) -> bool:
        entity = random.choices(
            ["customers", "leads", "activities"],
            weights=[0.45, 0.35, 0.20],
            k=1,
        )[0]
        created = await create_entity(entity=entity)
        return created is not None

    async def _run_update(self) -> bool:
        entity = random.choices(
            ["customers", "leads", "deals", "activities"],
            weights=[0.28, 0.28, 0.26, 0.18],
            k=1,
        )[0]

        existing = await self._pick_existing_record(entity)
        if existing is None:
            if entity in {"customers", "leads", "activities"}:
                created = await create_entity(entity=entity)
                return created is not None
            return False

        entity_id = _extract_entity_id(entity, existing)
        if entity_id is None:
            return False

        updated = await update_entity(entity=entity, entity_id=entity_id)
        return updated is not None

    async def _run_delete(self) -> bool:
        entity = random.choices(
            ["customers", "leads", "deals", "activities"],
            weights=[0.22, 0.24, 0.32, 0.22],
            k=1,
        )[0]

        candidates = await list_entities(
            entity=entity,
            version="v3",
            include_deleted=False,
            limit=500,
        )
        if len(candidates) < 5:
            return False

        target = random.choice(candidates)
        entity_id = _extract_entity_id(entity, target)
        if entity_id is None:
            return False

        deleted = await delete_entity(entity=entity, entity_id=entity_id)
        return deleted is not None

    async def run_cycle(self) -> Dict[str, Any]:
        if is_mutation_lock_busy():
            stats = {
                "cycle": self._cycle_counter,
                "skipped": True,
                "reason": "lock_busy",
                "create": 0,
                "update": 0,
                "delete": 0,
            }
            self._cycle_counter = self._cycle_counter + 1
            self._skipped_cycles = self._skipped_cycles + 1
            self._last_cycle_stats = dict(stats)
            return stats

        operation_count = random.randint(1, self.max_ops_per_cycle)
        stats = {
            "cycle": self._cycle_counter,
            "skipped": False,
            "create": 0,
            "update": 0,
            "delete": 0,
        }

        for _ in range(operation_count):
            operation = self._choose_operation()

            if operation == "create":
                ok = await self._run_create()
            elif operation == "update":
                ok = await self._run_update()
            else:
                ok = await self._run_delete()

            if ok:
                stats[operation] = stats[operation] + 1

        self._cycle_counter = self._cycle_counter + 1
        self._last_cycle_stats = dict(stats)

        if stats["create"] > 0 or stats["update"] > 0 or stats["delete"] > 0:
            logger.info(
                "Runtime generator cycle %s: create=%s update=%s delete=%s",
                stats["cycle"],
                stats["create"],
                stats["update"],
                stats["delete"],
            )

        return stats

    def get_config(self) -> Dict[str, Any]:
        return {
            "interval_seconds": self.interval_seconds,
            "max_ops_per_cycle": self.max_ops_per_cycle,
        }

    def get_metrics(self) -> Dict[str, Any]:
        running = self._task is not None and not self._task.done()
        return {
            "running": running,
            "cycle_counter": self._cycle_counter,
            "skipped_cycles": self._skipped_cycles,
            "last_cycle": dict(self._last_cycle_stats),
            "interval_seconds": self.interval_seconds,
            "max_ops_per_cycle": self.max_ops_per_cycle,
        }


_runtime_generator_service = RuntimeGeneratorService()


async def start_runtime_generator() -> None:
    await _runtime_generator_service.start()


async def stop_runtime_generator() -> None:
    await _runtime_generator_service.stop()


def get_runtime_generator_config() -> Dict[str, Any]:
    return _runtime_generator_service.get_config()


def get_runtime_generator_metrics() -> Dict[str, Any]:
    return _runtime_generator_service.get_metrics()
