"""Persistent feedback receipts and replay for selected policy execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ExecutedProtocolFootprint,
    MatchedPolicyEvidence,
    OrganizationTrialRecord,
    PolicyExecutionBundle,
    PolicyExecutionOutcome,
    SelectionExecutionBudget,
    SelectionExecutionRequest,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .deliberation import DeliberationEventStore
from .selection_feedback_contracts import (
    SELECTION_EXECUTION_FEEDBACK_RUNTIME_VERSION,
    SelectionExecutionFeedbackReceipt,
    SelectionExecutionFeedbackSnapshot,
)


class SelectionFeedbackRepository:
    """Own feedback events, admitted records, snapshots, and reconstruction."""

    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._receipts: dict[str, SelectionExecutionFeedbackReceipt] = {}
        self._trial_keys: set[tuple[str, str, str]] = set()
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "selection-feedback-public", runtime_id)
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def receipt(self, bridge_run_id: str) -> SelectionExecutionFeedbackReceipt | None:
        return self._receipts.get(bridge_run_id)

    def has_trial_group(self, *, context_key: str, evidence_tier: str, trial_group_id: str) -> bool:
        return (context_key, evidence_tier, trial_group_id) in self._trial_keys

    def receipts(self) -> tuple[SelectionExecutionFeedbackReceipt, ...]:
        return tuple(self._receipts[key] for key in sorted(self._receipts))

    def all_records(self) -> tuple[OrganizationTrialRecord, ...]:
        return tuple(record for receipt in self.receipts() for record in receipt.admitted_records)

    def save(self, receipt: SelectionExecutionFeedbackReceipt) -> None:
        run_id = receipt.request.bridge_run_id
        if run_id in self._receipts:
            raise ValueError(f"duplicate_selection_feedback_run:{run_id}")
        trial_key = (
            receipt.request.context_key,
            receipt.request.evidence_tier,
            receipt.request.trial_group_id,
        )
        if trial_key in self._trial_keys:
            raise ValueError("duplicate_selection_feedback_trial_group")
        self._receipts[run_id] = receipt
        self._trial_keys.add(trial_key)
        try:
            self._persist("SELECTION_EXECUTION_FEEDBACK_ADMITTED", {"receipt": receipt.as_dict()})
        except Exception:
            self._receipts.pop(run_id, None)
            self._trial_keys.discard(trial_key)
            raise

    def persist_blocked(self, payload: dict[str, Any]) -> None:
        self._persist("SELECTION_EXECUTION_FEEDBACK_BLOCKED", payload)

    def snapshot(self) -> SelectionExecutionFeedbackSnapshot:
        return SelectionExecutionFeedbackSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            receipts=self.receipts(),
        )

    def verify_replay(self) -> dict[str, Any]:
        event_replay = self._event_store.verify()
        snapshot_current = self._snapshot_is_current()
        failures = [f"events:{item}" for item in event_replay["failures"]]
        if not snapshot_current:
            failures.append("snapshot_state_mismatch")
        return {
            "valid": not failures,
            "event_replay": event_replay,
            "snapshot_state_current": snapshot_current,
            "receipt_count": len(self._receipts),
            "record_count": len(self.all_records()),
            "failures": failures,
        }

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self._persist(
                "SELECTION_EXECUTION_FEEDBACK_INITIALIZED",
                {
                    "project_scope": self.project_scope,
                    "module_id": SELECTION_EXECUTION_FEEDBACK_RUNTIME_VERSION,
                },
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("selection_feedback_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "SELECTION_EXECUTION_FEEDBACK_ADMITTED":
                receipt = self._receipt_from_dict(payload["receipt"])
                run_id = receipt.request.bridge_run_id
                trial_key = (
                    receipt.request.context_key,
                    receipt.request.evidence_tier,
                    receipt.request.trial_group_id,
                )
                if run_id in self._receipts or trial_key in self._trial_keys:
                    raise ValueError("selection_feedback_replay_duplicate_state")
                self._receipts[run_id] = receipt
                self._trial_keys.add(trial_key)
            elif event_type not in {
                "SELECTION_EXECUTION_FEEDBACK_INITIALIZED",
                "SELECTION_EXECUTION_FEEDBACK_BLOCKED",
            }:
                raise ValueError(f"unknown_selection_feedback_event_type:{event_type}")
        if not self._snapshot_is_current():
            raise ValueError("selection_feedback_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        payload = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return payload.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @classmethod
    def _receipt_from_dict(cls, payload: dict[str, Any]) -> SelectionExecutionFeedbackReceipt:
        request = cls._request_from_dict(payload["request"])
        bundle = cls._bundle_from_dict(payload["execution_bundle"])
        records = tuple(cls._record_from_dict(item) for item in payload["admitted_records"])
        evidence = tuple(cls._evidence_from_dict(item) for item in payload["matched_evidence"])
        return SelectionExecutionFeedbackReceipt(
            request=request,
            execution_bundle=bundle,
            admitted_records=records,
            matched_evidence=evidence,
            created_at=payload["created_at"],
            receipt_hash=payload["receipt_hash"],
            candidate_state=payload["candidate_state"],
        )

    @staticmethod
    def _request_from_dict(payload: dict[str, Any]) -> SelectionExecutionRequest:
        item = dict(payload)
        for name in ("selected_agent_ids", "selected_roles", "trial_evidence_refs"):
            item[name] = tuple(item[name])
        item["execution_budget"] = SelectionExecutionBudget(**item["execution_budget"])
        return SelectionExecutionRequest(**item)

    @classmethod
    def _bundle_from_dict(cls, payload: dict[str, Any]) -> PolicyExecutionBundle:
        item = dict(payload)
        item["outcomes"] = tuple(cls._outcome_from_dict(value) for value in item["outcomes"])
        item["executed_protocols"] = tuple(
            ExecutedProtocolFootprint(**value) for value in item["executed_protocols"]
        )
        return PolicyExecutionBundle(**item)

    @staticmethod
    def _outcome_from_dict(payload: dict[str, Any]) -> PolicyExecutionOutcome:
        item = dict(payload)
        for name in ("agent_ids", "roles", "evidence_refs"):
            item[name] = tuple(item[name])
        return PolicyExecutionOutcome(**item)

    @staticmethod
    def _record_from_dict(payload: dict[str, Any]) -> OrganizationTrialRecord:
        item = dict(payload)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        return OrganizationTrialRecord(**item)

    @staticmethod
    def _evidence_from_dict(payload: dict[str, Any]) -> MatchedPolicyEvidence:
        item = dict(payload)
        for name in ("matched_trial_group_ids", "evidence_refs", "record_hashes"):
            item[name] = tuple(item[name])
        return MatchedPolicyEvidence(**item)
