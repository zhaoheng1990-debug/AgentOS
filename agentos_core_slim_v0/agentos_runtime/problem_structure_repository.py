"""Persistent ledger and replay for admitted problem structures."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel import (
    ContextualProblemStructure,
    ProblemStructureAdmissionDecision,
    ProblemStructureAdmissionReceipt,
    ProblemStructureCandidate,
    ProblemStructureDimensionAssessment,
    ProblemStructureProviderJudgment,
    ProblemStructureSourceSignal,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .deliberation import DeliberationEventStore
from .problem_structure_contracts import (
    PROBLEM_STRUCTURE_ADMISSION_RUNTIME_VERSION,
    ProblemStructureAdmissionSnapshot,
)


class ProblemStructureRepository:
    """Own append-only admissions, revision ancestry, snapshots, and replay."""

    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._receipts: dict[str, ProblemStructureAdmissionReceipt] = {}
        self._latest: dict[tuple[str, str], str] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(
            root / "problem-structure-admission-public",
            runtime_id,
        )
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def receipt(self, admission_id: str) -> ProblemStructureAdmissionReceipt | None:
        return self._receipts.get(admission_id)

    def receipts(self) -> tuple[ProblemStructureAdmissionReceipt, ...]:
        return tuple(self._receipts[key] for key in sorted(self._receipts))

    def latest(self, *, context_key: str, source_problem_id: str):
        admission_id = self._latest.get((context_key, source_problem_id))
        return self._receipts.get(admission_id) if admission_id else None

    def save(self, receipt: ProblemStructureAdmissionReceipt) -> None:
        admission_id = receipt.decision.admission_id
        if admission_id in self._receipts:
            raise ValueError(f"duplicate_problem_structure_admission:{admission_id}")
        self.validate_candidate_revision(receipt.candidate)
        key = (receipt.candidate.context_key, receipt.candidate.source_problem_id)
        prior = self._latest.get(key)
        self._receipts[admission_id] = receipt
        self._latest[key] = admission_id
        try:
            self._persist("PROBLEM_STRUCTURE_ADMITTED", {"receipt": receipt.as_dict()})
        except Exception:
            self._receipts.pop(admission_id, None)
            if prior:
                self._latest[key] = prior
            else:
                self._latest.pop(key, None)
            raise

    def persist_blocked(self, payload: dict[str, Any]) -> None:
        self._persist("PROBLEM_STRUCTURE_ADMISSION_BLOCKED", payload)

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._persist(event_type, payload)

    def snapshot(self) -> ProblemStructureAdmissionSnapshot:
        return ProblemStructureAdmissionSnapshot(
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
            "failures": failures,
        }

    def validate_candidate_revision(self, candidate: ProblemStructureCandidate) -> None:
        if candidate.project_scope != self.project_scope:
            raise ValueError("problem_structure_repository_scope_mismatch")
        latest = self.latest(
            context_key=candidate.context_key,
            source_problem_id=candidate.source_problem_id,
        )
        if latest is None and candidate.supersedes_receipt_hash:
            raise ValueError("problem_structure_revision_predecessor_missing")
        if latest is not None and not candidate.supersedes_receipt_hash:
            raise ValueError("problem_structure_revision_binding_required")
        if latest is not None and candidate.supersedes_receipt_hash != latest.receipt_hash:
            raise ValueError("problem_structure_revision_predecessor_mismatch")

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self._persist(
                "PROBLEM_STRUCTURE_ADMISSION_INITIALIZED",
                {
                    "project_scope": self.project_scope,
                    "module_id": PROBLEM_STRUCTURE_ADMISSION_RUNTIME_VERSION,
                },
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("problem_structure_admission_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "PROBLEM_STRUCTURE_ADMITTED":
                receipt = self._receipt_from_dict(payload["receipt"])
                admission_id = receipt.decision.admission_id
                if admission_id in self._receipts:
                    raise ValueError("problem_structure_admission_replay_duplicate")
                self.validate_candidate_revision(receipt.candidate)
                self._receipts[admission_id] = receipt
                self._latest[(receipt.candidate.context_key, receipt.candidate.source_problem_id)] = (
                    admission_id
                )
            elif event_type not in {
                "PROBLEM_STRUCTURE_ADMISSION_INITIALIZED",
                "PROBLEM_STRUCTURE_PROVIDER_BLOCKED",
                "PROBLEM_STRUCTURE_ADMISSION_BLOCKED",
            }:
                raise ValueError(f"unknown_problem_structure_admission_event:{event_type}")
        if not self._snapshot_is_current():
            raise ValueError("problem_structure_admission_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        payload = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return payload.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @classmethod
    def _receipt_from_dict(cls, payload: dict[str, Any]) -> ProblemStructureAdmissionReceipt:
        item = dict(payload)
        for key in ("global_policy_authority", "execution_authorized", "production_activation"):
            item.pop(key, None)
        item["candidate"] = cls._candidate_from_dict(item["candidate"])
        item["provider_judgment"] = cls._judgment_from_dict(item["provider_judgment"])
        item["decision"] = cls._decision_from_dict(item["decision"])
        item["problem_structure"] = cls._structure_from_dict(item["problem_structure"])
        return ProblemStructureAdmissionReceipt(**item)

    @staticmethod
    def _candidate_from_dict(payload: dict[str, Any]) -> ProblemStructureCandidate:
        item = dict(payload)
        for key in (
            "evidence_refs",
            "rival_explanations",
            "unresolved_conflicts",
            "required_harnesses",
            "source_message_hashes",
            "source_execution_receipt_hashes",
        ):
            item[key] = tuple(item[key])
        item["source_signals"] = tuple(
            ProblemStructureSourceSignal(
                **{**value, "evidence_refs": tuple(value["evidence_refs"])}
            )
            for value in item["source_signals"]
        )
        return ProblemStructureCandidate(**item)

    @staticmethod
    def _assessment_from_dict(payload: dict[str, Any]) -> ProblemStructureDimensionAssessment:
        item = dict(payload)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        item["source_signal_names"] = tuple(item["source_signal_names"])
        return ProblemStructureDimensionAssessment(**item)

    @classmethod
    def _judgment_from_dict(cls, payload: dict[str, Any]) -> ProblemStructureProviderJudgment:
        item = dict(payload)
        item["dimension_assessments"] = tuple(
            cls._assessment_from_dict(value) for value in item["dimension_assessments"]
        )
        item["evidence_refs"] = tuple(item["evidence_refs"])
        return ProblemStructureProviderJudgment(**item)

    @staticmethod
    def _decision_from_dict(payload: dict[str, Any]) -> ProblemStructureAdmissionDecision:
        item = dict(payload)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        return ProblemStructureAdmissionDecision(**item)

    @staticmethod
    def _structure_from_dict(payload: dict[str, Any]) -> ContextualProblemStructure:
        item = dict(payload)
        item.pop("problem_structure_hash", None)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        return ContextualProblemStructure(**item)
