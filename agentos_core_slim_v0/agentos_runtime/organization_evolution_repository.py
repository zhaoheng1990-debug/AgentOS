"""Hash-chained persistence and restart reconstruction for organization evolution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel.organization_evolution_eval import OrganizationOperatorCredit
from agentos_kernel.organization_evolution_models import ORGANIZATION_EVOLUTION_OPERATOR_IDS, organization_hash

from .deliberation import DeliberationEventStore
from .organization_evolution_contracts import (
    ORGANIZATION_EVOLUTION_RUNTIME_VERSION,
    OrganizationEvolutionSnapshot,
    snapshot_from_dict,
)


_EVENT_TYPES = {
    "ORGANIZATION_EVOLUTION_RUNTIME_INITIALIZED",
    "ORGANIZATION_EVOLUTION_SESSION_STARTED",
    "ORGANIZATION_EVOLUTION_GENERATION_COMPLETED",
    "ORGANIZATION_EVOLUTION_SESSION_STOPPED",
    "ORGANIZATION_EVOLUTION_PROVIDER_BLOCKED",
    "ORGANIZATION_EVOLUTION_RUNTIME_BLOCKED",
}


class OrganizationEvolutionRepository:
    """Own one durable optimization session and its exact replay state."""

    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "organization-evolution-public", runtime_id)
        self._snapshot = OrganizationEvolutionSnapshot(
            runtime_id=runtime_id,
            project_scope=project_scope,
            state="INITIALIZED",
            task=None,
            budget=None,
            fitness=None,
            incumbent=None,
            incumbent_outcome=None,
            generation_receipts=(),
            operator_credits=tuple(OrganizationOperatorCredit(item) for item in ORGANIZATION_EVOLUTION_OPERATOR_IDS),
            spent_provider_calls=0,
            spent_normalized_cost=0.0,
            no_improvement_generations=0,
            stop_reason="",
        )
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def snapshot(self) -> OrganizationEvolutionSnapshot:
        return self._snapshot

    def save(self, event_type: str, snapshot: OrganizationEvolutionSnapshot, details: dict[str, Any] | None = None) -> None:
        if event_type not in _EVENT_TYPES:
            raise ValueError(f"organization_evolution_event_type_invalid:{event_type}")
        if snapshot.runtime_id != self.runtime_id or snapshot.project_scope != self.project_scope:
            raise ValueError("organization_evolution_snapshot_scope_mismatch")
        self._snapshot = snapshot
        self._event_store.append(event_type, {"state": snapshot.as_dict(), "details": details or {}})
        self._event_store.write_snapshot(snapshot)

    def persist_event(self, event_type: str, details: dict[str, Any]) -> None:
        self.save(event_type, self._snapshot, details)

    def verify_replay(self) -> dict[str, Any]:
        event_replay = self._event_store.verify()
        failures = [f"events:{item}" for item in event_replay["failures"]]
        snapshot_current = self._snapshot_is_current()
        if not snapshot_current:
            failures.append("snapshot_state_mismatch")
        return {
            "valid": not failures,
            "event_replay": event_replay,
            "snapshot_state_current": snapshot_current,
            "generation_count": len(self._snapshot.generation_receipts),
            "failures": failures,
        }

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self.save(
                "ORGANIZATION_EVOLUTION_RUNTIME_INITIALIZED",
                self._snapshot,
                {"module_id": ORGANIZATION_EVOLUTION_RUNTIME_VERSION},
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("organization_evolution_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            if event.get("event_type") not in _EVENT_TYPES:
                raise ValueError(f"organization_evolution_replay_event_unknown:{event.get('event_type')}")
            state = (event.get("payload") or {}).get("state")
            if not isinstance(state, dict):
                raise ValueError("organization_evolution_replay_state_missing")
            self._snapshot = snapshot_from_dict(state)
            if self._snapshot.runtime_id != self.runtime_id or self._snapshot.project_scope != self.project_scope:
                raise ValueError("organization_evolution_replay_scope_mismatch")
        if not self._snapshot_is_current():
            raise ValueError("organization_evolution_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        record = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return record.get("snapshot_hash") == organization_hash(self._snapshot.as_dict())
