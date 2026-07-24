"""Project-scoped selection and unassigned-consequence ledger."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentos_kernel.selection_retention_models import (
    ConsequenceBinding,
    ProspectiveSelectionEvent,
    hash_selection_payload,
)

from .deliberation import DeliberationEventStore


@dataclass(frozen=True)
class SelectionRetentionSnapshot:
    runtime_id: str
    project_scope: str
    selections: tuple[ProspectiveSelectionEvent, ...]
    consequences: tuple[ConsequenceBinding, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "selections": [item.as_dict() for item in self.selections],
            "consequences": [item.as_dict() for item in self.consequences],
            "consequence_assignment_default": "UNASSIGNED",
            "retention_write_authority": False,
        }


class SelectionRetentionRepository:
    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        workspace_root: str | Path,
    ) -> None:
        if not project_scope.startswith("project://"):
            raise ValueError("selection_repository_project_scope_invalid")
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._selections: dict[str, ProspectiveSelectionEvent] = {}
        self._consequences: dict[str, ConsequenceBinding] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._store = DeliberationEventStore(
            root / "selection-retention-public", runtime_id
        )
        self._initialize_or_replay()

    def save_selection(self, value: ProspectiveSelectionEvent) -> None:
        if value.project_scope != self.project_scope:
            raise ValueError("selection_repository_scope_mismatch")
        if value.selection_event_id in self._selections:
            raise ValueError("duplicate_selection_event")
        self._selections[value.selection_event_id] = value
        try:
            self._persist(
                "SELECTION_PRECOMMITTED", {"selection": value.as_dict()}
            )
        except Exception:
            self._selections.pop(value.selection_event_id, None)
            raise

    def bind_consequence(self, value: ConsequenceBinding) -> None:
        if value.project_scope != self.project_scope:
            raise ValueError("consequence_repository_scope_mismatch")
        if value.binding_id in self._consequences:
            raise ValueError("duplicate_consequence_binding")
        if not any(
            item.preconsequence_hash == value.selection_event_hash
            for item in self._selections.values()
        ):
            raise ValueError("consequence_selection_not_found")
        self._consequences[value.binding_id] = value
        try:
            self._persist(
                "CONSEQUENCE_BOUND_UNASSIGNED",
                {"consequence": value.as_dict()},
            )
        except Exception:
            self._consequences.pop(value.binding_id, None)
            raise

    def snapshot(self) -> SelectionRetentionSnapshot:
        return SelectionRetentionSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            selections=tuple(self._selections.values()),
            consequences=tuple(self._consequences.values()),
        )

    def verify_replay(self) -> dict[str, Any]:
        event_result = self._store.verify()
        current = self._snapshot_current()
        failures = list(event_result["failures"])
        if not current:
            failures.append("snapshot_state_mismatch")
        return {
            "valid": not failures,
            "event_replay": event_result,
            "snapshot_state_current": current,
            "selection_count": len(self._selections),
            "consequence_count": len(self._consequences),
            "failures": failures,
        }

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._store.append(event_type, payload)
        self._store.write_snapshot(self.snapshot())

    def _initialize_or_replay(self) -> None:
        events = self._store.events()
        if not events:
            self._persist(
                "SELECTION_RETENTION_INITIALIZED",
                {"project_scope": self.project_scope},
            )
            return
        verification = self._store.verify()
        if not verification["valid"]:
            raise ValueError("selection_repository_replay_invalid")
        for event in events:
            event_type = event["event_type"]
            payload = event["payload"]
            if event_type == "SELECTION_PRECOMMITTED":
                selection = self._selection_from_dict(
                    payload["selection"]
                )
                self._selections[selection.selection_event_id] = selection
            elif event_type == "CONSEQUENCE_BOUND_UNASSIGNED":
                consequence = self._consequence_from_dict(
                    payload["consequence"]
                )
                self._consequences[consequence.binding_id] = consequence
            elif event_type != "SELECTION_RETENTION_INITIALIZED":
                raise ValueError(
                    f"selection_repository_event_unknown:{event_type}"
                )
        if not self._snapshot_current():
            raise ValueError("selection_repository_snapshot_mismatch")

    def _snapshot_current(self) -> bool:
        if not self._store.snapshot_path.exists():
            return False
        record = json.loads(
            self._store.snapshot_path.read_text(encoding="utf-8")
        )
        return record.get("snapshot_hash") == hash_selection_payload(
            self.snapshot().as_dict()
        )

    @staticmethod
    def _selection_from_dict(
        payload: dict[str, Any],
    ) -> ProspectiveSelectionEvent:
        values = dict(payload)
        for name in (
            "alternatives",
            "rejected_refs",
            "deferred_refs",
            "evidence_refs",
        ):
            values[name] = tuple(values[name])
        values.pop("consequence_known", None)
        values.pop("retention_authority", None)
        return ProspectiveSelectionEvent(**values)

    @staticmethod
    def _consequence_from_dict(
        payload: dict[str, Any],
    ) -> ConsequenceBinding:
        values = dict(payload)
        values["evidence_refs"] = tuple(values["evidence_refs"])
        values.pop("retention_attribution_authority", None)
        return ConsequenceBinding(**values)
