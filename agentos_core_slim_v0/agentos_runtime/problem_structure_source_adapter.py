"""Adapter from the existing plural problem runtime to an admission candidate."""

from __future__ import annotations

import json
from typing import Any

from agentos_kernel import (
    PROBLEM_STRUCTURE_SOURCE_SIGNALS,
    ProblemStructureCandidate,
    ProblemStructureSourceSignal,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .problem_definition import EndogenousProblemRuntime


_MESSAGE_TYPES = (
    "PROBLEM_CANDIDATE_SET",
    "PROBLEM_CRITIQUE",
    "RESEARCHABILITY_REPORT",
    "AGENDA_SELECTION_PROPOSAL",
)


class ProblemDefinitionStructureAdapter:
    """Build one strongly bound candidate from an admitted problem-definition snapshot."""

    adapter_id = "endogenous-problem-structure-source-v0-1"

    def __init__(self, runtime: EndogenousProblemRuntime, *, context_key: str) -> None:
        self.runtime = runtime
        self.context_key = context_key

    def build_candidate(
        self,
        *,
        candidate_id: str,
        supersedes_receipt_hash: str = "",
    ) -> ProblemStructureCandidate:
        replay = self.runtime.verify_replay()
        if replay.get("valid") is not True:
            raise ValueError("problem_structure_source_replay_invalid")
        snapshot = self.runtime.snapshot()
        if (
            snapshot.stage != "CANDIDATE"
            or snapshot.candidate_state != "PENDING_AGENDA_REVIEW"
            or snapshot.deliberation_seed is None
            or snapshot.agenda_selection is None
        ):
            raise ValueError("problem_structure_source_candidate_not_ready")
        if tuple(item.message_type for item in snapshot.messages) != _MESSAGE_TYPES:
            raise ValueError("problem_structure_source_message_surface_invalid")
        if len(snapshot.execution_receipts) != 4:
            raise ValueError("problem_structure_source_execution_surface_invalid")
        self._validate_hashes(snapshot.messages, snapshot.execution_receipts, snapshot.deliberation_seed)
        self._validate_receipt_bindings(snapshot.messages, snapshot.execution_receipts)
        seed = snapshot.deliberation_seed
        selected = self._selected_payloads(snapshot.messages, seed.source_problem_id)
        framing, review, researchability = selected
        if (
            framing["question"] != seed.objective
            or framing["research_object"] != seed.research_object
            or tuple(str(item) for item in framing["rival_explanations"]) != seed.rival_explanations
            or researchability["operationalization"] != seed.operationalization
            or tuple(str(item) for item in researchability["required_harnesses"])
            != seed.required_harnesses
        ):
            raise ValueError("problem_structure_source_seed_payload_mismatch")
        evidence_refs = tuple(
            dict.fromkeys(
                (
                    *seed.evidence_refs,
                    *framing["evidence_refs"],
                    *review["evidence_refs"],
                    *researchability["evidence_refs"],
                )
            )
        )
        messages = {item.message_type: item for item in snapshot.messages}
        signals = self._signals(
            framing=framing,
            review=review,
            researchability=researchability,
            messages=messages,
        )
        return ProblemStructureCandidate.create(
            candidate_id=candidate_id,
            source_problem_id=seed.source_problem_id,
            context_key=self.context_key,
            project_scope=seed.project_scope,
            objective=seed.objective,
            source_seed_ref=f"deliberation-seed://{seed.seed_id}/{seed.seed_hash}",
            source_seed_hash=seed.seed_hash,
            evidence_refs=evidence_refs,
            rival_explanations=seed.rival_explanations,
            unresolved_conflicts=tuple(self._stable_text(item) for item in seed.unresolved_conflicts),
            required_harnesses=seed.required_harnesses,
            source_message_hashes=tuple(item.message_hash for item in snapshot.messages),
            source_execution_receipt_hashes=tuple(
                item.receipt_hash for item in snapshot.execution_receipts
            ),
            source_signals=signals,
            supersedes_receipt_hash=supersedes_receipt_hash,
        )

    @staticmethod
    def _validate_hashes(messages, receipts, seed) -> None:
        seed_payload = seed.as_dict()
        seed_hash = seed_payload.pop("seed_hash")
        seed_payload.pop("candidate_state", None)
        seed_payload.pop("execution_authorized", None)
        if hash_payload(seed_payload) != seed_hash:
            raise ValueError("problem_structure_source_seed_hash_invalid")
        for message in messages:
            payload = message.as_dict()
            message_hash = payload.pop("message_hash")
            if hash_payload(payload) != message_hash:
                raise ValueError("problem_structure_source_message_hash_invalid")
        for receipt in receipts:
            payload = receipt.as_dict()
            receipt_hash = payload.pop("receipt_hash")
            payload.pop("errors", None)
            if hash_payload(payload) != receipt_hash:
                raise ValueError("problem_structure_source_execution_receipt_hash_invalid")

    @staticmethod
    def _validate_receipt_bindings(messages, receipts) -> None:
        for message, receipt in zip(messages, receipts, strict=True):
            expected_ref = f"message://{message.message_id}/{message.message_hash}"
            if (
                receipt.status != "COMPLETED"
                or receipt.session_id != message.session_id
                or receipt.agent_id != message.sender_agent_id
                or receipt.role != message.sender_role
                or receipt.message_ref != expected_ref
                or not str(receipt.provider_audit.get("status", "")).startswith("PASS_PROVIDER")
            ):
                raise ValueError("problem_structure_source_execution_receipt_binding_invalid")

    @staticmethod
    def _selected_payloads(messages, problem_id: str) -> tuple[dict[str, Any], ...]:
        by_type = {item.message_type: item.payload for item in messages}

        def selected(container: str, items: str) -> dict[str, Any]:
            values = [
                item
                for item in by_type[container][items]
                if item.get("problem_id") == problem_id
            ]
            if len(values) != 1:
                raise ValueError("problem_structure_source_selected_problem_coverage_invalid")
            return values[0]

        agenda = by_type["AGENDA_SELECTION_PROPOSAL"]
        if agenda.get("decision") != "SELECT" or agenda.get("selected_problem_id") != problem_id:
            raise ValueError("problem_structure_source_agenda_selection_mismatch")
        return (
            selected("PROBLEM_CANDIDATE_SET", "problem_candidates"),
            selected("PROBLEM_CRITIQUE", "candidate_reviews"),
            selected("RESEARCHABILITY_REPORT", "assessments"),
        )

    @staticmethod
    def _signals(*, framing, review, researchability, messages):
        sources = {
            **{
                name: (review, "PROBLEM_CRITIQUE")
                for name in ("premise_risk", "redundancy_risk", "negative_transfer_risk")
            },
            **{
                name: (researchability, "RESEARCHABILITY_REPORT")
                for name in ("falsifiability", "tractability", "normalized_cost")
            },
            **{
                name: (framing, "PROBLEM_CANDIDATE_SET")
                for name in ("novelty", "urgency", "expected_cbit_gain")
            },
        }
        return tuple(
            ProblemStructureSourceSignal.create(
                signal_name=name,
                value=float(sources[name][0][name]),
                evidence_refs=tuple(sources[name][0]["evidence_refs"]),
                source_message_hash=messages[sources[name][1]].message_hash,
            )
            for name in PROBLEM_STRUCTURE_SOURCE_SIGNALS
        )

    @staticmethod
    def _stable_text(value: Any) -> str:
        return value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
