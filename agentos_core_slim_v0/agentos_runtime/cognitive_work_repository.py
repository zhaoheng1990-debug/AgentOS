"""Append-only cognitive-work ledger with deterministic replay."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel.cognitive_work_models import (
    CognitiveWorkBudget,
    CognitiveWorkControlDecision,
    CognitiveWorkRoundObservation,
    CognitiveWorkSemanticAssessment,
    hash_payload,
)

from .cognitive_work_contracts import (
    COGNITIVE_WORK_RUNTIME_VERSION,
    CognitiveWorkRoundReceipt,
    CognitiveWorkSnapshot,
)
from .deliberation import DeliberationEventStore


class CognitiveWorkRepository:
    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._receipts: dict[str, CognitiveWorkRoundReceipt] = {}
        self._trajectories: dict[str, list[str]] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "cognitive-work-public", runtime_id)
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def receipts(self, trajectory_id: str = "") -> tuple[CognitiveWorkRoundReceipt, ...]:
        if not trajectory_id:
            return tuple(self._receipts.values())
        return tuple(self._receipts[item] for item in self._trajectories.get(trajectory_id, []))

    def save(self, receipt: CognitiveWorkRoundReceipt) -> None:
        self._validate_new(receipt)
        self._index(receipt)
        try:
            self.persist_event("COGNITIVE_WORK_ROUND_ACCOUNTED", {"receipt": receipt.as_dict()})
        except Exception:
            self._deindex(receipt)
            raise

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def snapshot(self) -> CognitiveWorkSnapshot:
        return CognitiveWorkSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            receipts=self.receipts(),
        )

    def latest_control(self, trajectory_id: str) -> CognitiveWorkControlDecision | None:
        items = self.receipts(trajectory_id)
        return items[-1].kernel_control if items else None

    def verify_replay(self) -> dict[str, Any]:
        event_replay = self._event_store.verify()
        current = self._snapshot_is_current()
        failures = [f"events:{item}" for item in event_replay["failures"]]
        if not current:
            failures.append("snapshot_state_mismatch")
        return {
            "valid": not failures,
            "event_replay": event_replay,
            "snapshot_state_current": current,
            "receipt_count": len(self._receipts),
            "trajectory_count": len(self._trajectories),
            "failures": failures,
        }

    def _validate_new(self, receipt: CognitiveWorkRoundReceipt) -> None:
        if receipt.receipt_id in self._receipts:
            raise ValueError(f"duplicate_cognitive_work_receipt:{receipt.receipt_id}")
        observation = receipt.observation
        if observation.project_scope != self.project_scope:
            raise ValueError("cognitive_work_repository_scope_mismatch")
        prior = self.receipts(observation.trajectory_id)
        if observation.round_index != len(prior) + 1:
            raise ValueError("cognitive_work_repository_round_sequence_invalid")
        if prior and prior[-1].observation.context_key != observation.context_key:
            raise ValueError("cognitive_work_repository_context_changed")
        expected = tuple(item.observation.observation_hash for item in (*prior, receipt))
        if receipt.kernel_control.observation_hashes != expected:
            raise ValueError("cognitive_work_repository_control_lineage_invalid")
        expected_provider = tuple(
            item.provider_invocation_receipt["receipt_hash"] for item in (*prior, receipt)
        )
        if receipt.kernel_control.provider_receipt_hashes != expected_provider:
            raise ValueError("cognitive_work_repository_provider_lineage_invalid")

    def _index(self, receipt: CognitiveWorkRoundReceipt) -> None:
        self._receipts[receipt.receipt_id] = receipt
        self._trajectories.setdefault(receipt.observation.trajectory_id, []).append(receipt.receipt_id)

    def _deindex(self, receipt: CognitiveWorkRoundReceipt) -> None:
        self._receipts.pop(receipt.receipt_id, None)
        ids = self._trajectories.get(receipt.observation.trajectory_id, [])
        if receipt.receipt_id in ids:
            ids.remove(receipt.receipt_id)
        if not ids:
            self._trajectories.pop(receipt.observation.trajectory_id, None)

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self.persist_event(
                "COGNITIVE_WORK_ACCOUNTING_INITIALIZED",
                {"project_scope": self.project_scope, "module_id": COGNITIVE_WORK_RUNTIME_VERSION},
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("cognitive_work_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "COGNITIVE_WORK_ROUND_ACCOUNTED":
                receipt = self._receipt_from_dict(payload["receipt"])
                self._validate_new(receipt)
                self._index(receipt)
            elif event_type not in {
                "COGNITIVE_WORK_ACCOUNTING_INITIALIZED",
                "COGNITIVE_WORK_PROVIDER_BLOCKED",
                "COGNITIVE_WORK_ACCOUNTING_BLOCKED",
            }:
                raise ValueError(f"unknown_cognitive_work_event:{event_type}")
        if not self._snapshot_is_current():
            raise ValueError("cognitive_work_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        payload = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return payload.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @staticmethod
    def _receipt_from_dict(payload: dict[str, Any]) -> CognitiveWorkRoundReceipt:
        item = dict(payload)
        for key in ("baseline_write_authority", "global_memory_write_authority", "production_activation"):
            item.pop(key, None)
        observation = dict(item["observation"])
        observation.pop("observation_hash", None)
        observation.pop("total_tokens", None)
        for key in ("agent_ids", "model_ids", "evidence_refs"):
            observation[key] = tuple(observation[key])
        semantic = dict(item["semantic_assessment"])
        semantic["evidence_refs"] = tuple(semantic["evidence_refs"])
        control = dict(item["kernel_control"])
        for key in ("global_policy_authority", "production_activation"):
            control.pop(key, None)
        control["observation_hashes"] = tuple(control["observation_hashes"])
        control["provider_receipt_hashes"] = tuple(control["provider_receipt_hashes"])
        budget = dict(item["budget"])
        budget.pop("budget_hash", None)
        return CognitiveWorkRoundReceipt(
            **{
                **item,
                "observation": CognitiveWorkRoundObservation(**observation),
                "semantic_assessment": CognitiveWorkSemanticAssessment(**semantic),
                "kernel_control": CognitiveWorkControlDecision(**control),
                "budget": CognitiveWorkBudget(**budget),
            }
        )
