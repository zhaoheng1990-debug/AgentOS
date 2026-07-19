"""Persistent selection receipts and replay for contextual organization policy."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AgentDescriptor,
    ContextualOrganizationPolicyDecision,
    ContextualPolicyCandidateEvaluation,
    ContextualProviderPolicyAssessment,
    EnsembleAssignment,
    MatchedPolicyEvidence,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .contextual_policy_contracts import (
    CONTEXTUAL_ORGANIZATION_POLICY_RUNTIME_VERSION,
    ContextualOrganizationPolicySnapshot,
    ContextualOrganizationSelectionReceipt,
    ContextualProviderAdvice,
)
from .deliberation import DeliberationEventStore


class ContextualPolicyRepository:
    """Own hash-chained public selections and deterministic reconstruction."""

    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._selections: dict[str, ContextualOrganizationSelectionReceipt] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "contextual-policy-public", runtime_id)
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def selection(self, selection_id: str) -> ContextualOrganizationSelectionReceipt | None:
        return self._selections.get(selection_id)

    def save_selection(self, receipt: ContextualOrganizationSelectionReceipt) -> None:
        if receipt.selection_id in self._selections:
            raise ValueError(f"duplicate_contextual_policy_selection:{receipt.selection_id}")
        self._selections[receipt.selection_id] = receipt
        self.persist_event("CONTEXTUAL_ORGANIZATION_POLICY_SELECTED", {"selection": receipt.as_dict()})

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def snapshot(self) -> ContextualOrganizationPolicySnapshot:
        return ContextualOrganizationPolicySnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            selections=tuple(self._selections[key] for key in sorted(self._selections)),
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
            "selection_count": len(self._selections),
            "failures": failures,
        }

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self.persist_event(
                "CONTEXTUAL_POLICY_RUNTIME_INITIALIZED",
                {
                    "project_scope": self.project_scope,
                    "module_id": CONTEXTUAL_ORGANIZATION_POLICY_RUNTIME_VERSION,
                },
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("contextual_policy_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "CONTEXTUAL_ORGANIZATION_POLICY_SELECTED":
                receipt = self._receipt_from_dict(payload["selection"])
                if receipt.selection_id in self._selections:
                    raise ValueError("contextual_policy_replay_duplicate_selection")
                self._selections[receipt.selection_id] = receipt
            elif event_type not in {
                "CONTEXTUAL_POLICY_RUNTIME_INITIALIZED",
                "CONTEXTUAL_POLICY_PROVIDER_BLOCKED",
            }:
                raise ValueError(f"unknown_contextual_policy_event_type:{event_type}")
        if not self._snapshot_is_current():
            raise ValueError("contextual_policy_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        record = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return record.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @classmethod
    def _receipt_from_dict(cls, payload: dict[str, Any]) -> ContextualOrganizationSelectionReceipt:
        advice = cls._advice_from_dict(payload["provider_advice"])
        evidence = tuple(cls._evidence_from_dict(item) for item in payload["matched_evidence"])
        decision = cls._decision_from_dict(payload["kernel_decision"])
        assignment = cls._assignment_from_dict(payload.get("assignment"))
        return ContextualOrganizationSelectionReceipt(
            selection_id=payload["selection_id"],
            runtime_id=payload["runtime_id"],
            project_scope=payload["project_scope"],
            context_key=payload["context_key"],
            evidence_tier=payload["evidence_tier"],
            provider_advice=advice,
            matched_evidence=evidence,
            kernel_decision=decision,
            assignment=assignment,
            created_at=payload["created_at"],
            receipt_hash=payload["receipt_hash"],
            candidate_state=payload["candidate_state"],
        )

    @staticmethod
    def _assessment_from_dict(payload: dict[str, Any]) -> ContextualProviderPolicyAssessment:
        item = dict(payload)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        return ContextualProviderPolicyAssessment(**item)

    @classmethod
    def _advice_from_dict(cls, payload: dict[str, Any]) -> ContextualProviderAdvice:
        return ContextualProviderAdvice(
            recommended_policy_id=payload["recommended_policy_id"],
            policy_assessments=tuple(
                cls._assessment_from_dict(item) for item in payload["policy_assessments"]
            ),
            global_uncertainty=payload["global_uncertainty"],
            evidence_refs=tuple(payload["evidence_refs"]),
            provider_invocation_receipt=payload["provider_invocation_receipt"],
            provider_audit=payload["provider_audit"],
            advice_hash=payload["advice_hash"],
        )

    @staticmethod
    def _evidence_from_dict(payload: dict[str, Any]) -> MatchedPolicyEvidence:
        item = dict(payload)
        for name in ("matched_trial_group_ids", "evidence_refs", "record_hashes"):
            item[name] = tuple(item[name])
        return MatchedPolicyEvidence(**item)

    @classmethod
    def _decision_from_dict(cls, payload: dict[str, Any]) -> ContextualOrganizationPolicyDecision:
        item = dict(payload)
        for name in ("global_policy_authority", "production_activation"):
            item.pop(name, None)
        item["selected_roles"] = tuple(item["selected_roles"])
        item["required_roles"] = tuple(item["required_roles"])
        item["evidence_refs"] = tuple(item["evidence_refs"])
        item["candidate_evaluations"] = tuple(
            cls._candidate_evaluation_from_dict(value) for value in item["candidate_evaluations"]
        )
        return ContextualOrganizationPolicyDecision(**item)

    @classmethod
    def _candidate_evaluation_from_dict(
        cls, payload: dict[str, Any]
    ) -> ContextualPolicyCandidateEvaluation:
        item = dict(payload)
        item["roles"] = tuple(item["roles"])
        item["hard_gate_failures"] = tuple(item["hard_gate_failures"])
        item["rank_vector"] = tuple(item["rank_vector"])
        item["provider_assessment"] = cls._assessment_from_dict(item["provider_assessment"])
        return ContextualPolicyCandidateEvaluation(**item)

    @staticmethod
    def _assignment_from_dict(payload: dict[str, Any] | None) -> EnsembleAssignment | None:
        if payload is None:
            return None
        agents = tuple(
            AgentDescriptor(
                agent_id=item["agent_id"],
                role=item["role"],
                capabilities=tuple(item["capabilities"]),
                runner_id=item["runner_id"],
                harness_id=item["harness_id"],
                provider_id=item["provider_id"],
                model_id=item.get("model_id", ""),
                context_isolation_key=item["context_isolation_key"],
                allowed_evidence_scopes=tuple(item["allowed_evidence_scopes"]),
            )
            for item in payload["agents"]
        )
        return EnsembleAssignment(
            team_id=payload["team_id"],
            agents=agents,
            context_isolated=payload["context_isolated"],
            execution_authorized=payload["execution_authorized"],
        )
