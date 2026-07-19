"""Independent cognitive-agent identities, contracts, workspaces, and messages."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import AgentDescriptor


COGNITIVE_ROLE_RUNTIME_VERSION = "cognitive_role_runtime_v0_3"

_PRIVATE_EXPORT_KEYS = {
    "chain_of_thought",
    "hidden_reasoning",
    "private_memory",
    "private_note",
    "scratchpad",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CognitiveRoleContract:
    contract_id: str
    role: str
    stage: str
    purpose: str
    provider_operation_id: str
    allowed_input_message_types: tuple[str, ...]
    output_message_type: str
    required_output_fields: tuple[str, ...]
    output_field_types: tuple[tuple[str, str], ...]
    output_enums: tuple[tuple[str, tuple[str, ...]], ...] = ()
    provider_required: bool = True
    final_state_authority: bool = False

    def __post_init__(self) -> None:
        if not all(
            (
                self.contract_id,
                self.role,
                self.stage,
                self.purpose,
                self.provider_operation_id,
                self.output_message_type,
            )
        ):
            raise ValueError("cognitive_role_contract_incomplete")
        if not self.required_output_fields:
            raise ValueError("cognitive_role_output_contract_required")
        if not self.provider_required:
            raise ValueError("first_stage_cognitive_roles_require_provider_support")
        if self.final_state_authority:
            raise ValueError("cognitive_agent_cannot_own_final_state")
        typed_fields = {name for name, _field_type in self.output_field_types}
        if typed_fields != set(self.required_output_fields):
            raise ValueError("cognitive_role_output_types_must_cover_required_fields")

    def expected_schema(self) -> dict[str, Any]:
        properties = {
            name: {"type": field_type}
            for name, field_type in self.output_field_types
        }
        for name, values in self.output_enums:
            properties[name]["enum"] = list(values)
        return {
            "type": "object",
            "required": list(self.required_output_fields),
            "properties": properties,
        }


_STANDARD_ROLE_CONTRACTS = {
    "HYPOTHESIS_GENERATOR": CognitiveRoleContract(
        contract_id="hypothesis_generator_contract_v0_1",
        role="HYPOTHESIS_GENERATOR",
        stage="GENERATION",
        purpose="generate plural scoped hypotheses, assumptions, rivals, and falsifiers",
        provider_operation_id="group_hypothesis_generation",
        allowed_input_message_types=(),
        output_message_type="HYPOTHESIS_PROPOSAL",
        required_output_fields=(
            "hypotheses",
            "assumptions",
            "rival_explanations",
            "falsifiable_predictions",
            "evidence_refs",
            "confidence",
        ),
        output_field_types=(
            ("hypotheses", "array"),
            ("assumptions", "array"),
            ("rival_explanations", "array"),
            ("falsifiable_predictions", "array"),
            ("evidence_refs", "array"),
            ("confidence", "number"),
        ),
    ),
    "ADVERSARIAL_REVIEWER": CognitiveRoleContract(
        contract_id="adversarial_reviewer_contract_v0_1",
        role="ADVERSARIAL_REVIEWER",
        stage="REVIEW",
        purpose="seek strongest falsifiers, unsupported inference, rivals, and scope violations",
        provider_operation_id="adversarial_epistemic_review",
        allowed_input_message_types=("HYPOTHESIS_PROPOSAL",),
        output_message_type="ADVERSARIAL_REVIEW",
        required_output_fields=(
            "objections",
            "strongest_falsifier",
            "rival_set_coverage",
            "evidence_refs",
            "recommended_epistemic_state",
            "confidence",
        ),
        output_field_types=(
            ("objections", "array"),
            ("strongest_falsifier", "string"),
            ("rival_set_coverage", "number"),
            ("evidence_refs", "array"),
            ("recommended_epistemic_state", "string"),
            ("confidence", "number"),
        ),
        output_enums=(("recommended_epistemic_state", ("FALSIFIED", "PENDING", "SUPPORTED_BOUNDED")),),
    ),
    "REPLICATOR": CognitiveRoleContract(
        contract_id="independent_replicator_contract_v0_1",
        role="REPLICATOR",
        stage="REPLICATION",
        purpose="independently reconstruct evidence and interpret it against frozen gates",
        provider_operation_id="independent_replication_interpretation",
        allowed_input_message_types=("HYPOTHESIS_PROPOSAL",),
        output_message_type="REPLICATION_REPORT",
        required_output_fields=(
            "replication_outcome",
            "gate_results",
            "deviations",
            "evidence_refs",
            "confidence",
        ),
        output_field_types=(
            ("replication_outcome", "string"),
            ("gate_results", "object"),
            ("deviations", "array"),
            ("evidence_refs", "array"),
            ("confidence", "number"),
        ),
        output_enums=(("replication_outcome", ("PASSED", "FAILED", "INCONCLUSIVE")),),
    ),
    "SYNTHESIZER": CognitiveRoleContract(
        contract_id="bounded_synthesizer_contract_v0_1",
        role="SYNTHESIZER",
        stage="SYNTHESIS",
        purpose="form the narrowest synthesis while preserving conflict, minority positions, and uncertainty",
        provider_operation_id="group_synthesis_and_conflict_resolution",
        allowed_input_message_types=(
            "HYPOTHESIS_PROPOSAL",
            "ADVERSARIAL_REVIEW",
            "REPLICATION_REPORT",
        ),
        output_message_type="BOUNDED_SYNTHESIS",
        required_output_fields=(
            "converged_claims",
            "unresolved_conflicts",
            "minority_positions",
            "evidence_refs",
            "uncertainties",
        ),
        output_field_types=(
            ("converged_claims", "array"),
            ("unresolved_conflicts", "array"),
            ("minority_positions", "array"),
            ("evidence_refs", "array"),
            ("uncertainties", "array"),
        ),
    ),
    "COORDINATOR": CognitiveRoleContract(
        contract_id="cognitive_coordinator_contract_v0_2",
        role="COORDINATOR",
        stage="COORDINATION",
        purpose=(
            "select the highest-value admissible next cognitive action from public receipts; continue the minimal "
            "protocol when formal role outputs are present; failed or negative gates require bounded synthesis rather "
            "than blocking synthesis; request evidence only for a concrete blocking gap. FINALIZE_CANDIDATE is a "
            "request for the Kernel to form a pending candidate, not Coordinator-owned final-state authority; choose "
            "it whenever it is the Kernel-admissible progression. Never claim accepted or published state"
        ),
        provider_operation_id="cognitive_deliberation_coordination",
        allowed_input_message_types=(
            "HYPOTHESIS_PROPOSAL",
            "ADVERSARIAL_REVIEW",
            "REPLICATION_REPORT",
            "BOUNDED_SYNTHESIS",
        ),
        output_message_type="COORDINATION_PROPOSAL",
        required_output_fields=(
            "route_action",
            "target_role",
            "rationale",
            "unresolved_questions",
            "evidence_gaps",
            "conflict_message_refs",
            "evidence_refs",
            "expected_cbit_gain",
            "stop_condition",
        ),
        output_field_types=(
            ("route_action", "string"),
            ("target_role", "string"),
            ("rationale", "string"),
            ("unresolved_questions", "array"),
            ("evidence_gaps", "array"),
            ("conflict_message_refs", "array"),
            ("evidence_refs", "array"),
            ("expected_cbit_gain", "number"),
            ("stop_condition", "string"),
        ),
        output_enums=(
            (
                "route_action",
                (
                    "RUN_ROLE",
                    "PROCEED_TO_SYNTHESIS",
                    "FINALIZE_CANDIDATE",
                    "REQUEST_EVIDENCE",
                    "STOP_BLOCKED",
                ),
            ),
            (
                "target_role",
                (
                    "HYPOTHESIS_GENERATOR",
                    "ADVERSARIAL_REVIEWER",
                    "REPLICATOR",
                    "SYNTHESIZER",
                    "NONE",
                ),
            ),
        ),
    ),
    "PROBLEM_FRAMER": CognitiveRoleContract(
        contract_id="problem_framer_contract_v0_1",
        role="PROBLEM_FRAMER",
        stage="PROBLEM_FRAMING",
        purpose="derive plural source-grounded research problems from unresolved evidence without receiving a seeded question",
        provider_operation_id="endogenous_problem_framing",
        allowed_input_message_types=(),
        output_message_type="PROBLEM_CANDIDATE_SET",
        required_output_fields=("problem_candidates", "generation_rationale", "coverage_notes", "evidence_refs"),
        output_field_types=(
            ("problem_candidates", "array"),
            ("generation_rationale", "string"),
            ("coverage_notes", "array"),
            ("evidence_refs", "array"),
        ),
    ),
    "PROBLEM_CRITIC": CognitiveRoleContract(
        contract_id="problem_critic_contract_v0_1",
        role="PROBLEM_CRITIC",
        stage="PROBLEM_REVIEW",
        purpose="challenge problem premises, redundancy, hidden assumptions, and negative-transfer risk",
        provider_operation_id="problem_candidate_adversarial_review",
        allowed_input_message_types=("PROBLEM_CANDIDATE_SET",),
        output_message_type="PROBLEM_CRITIQUE",
        required_output_fields=("candidate_reviews", "surviving_problem_ids", "minority_objections", "evidence_refs"),
        output_field_types=(
            ("candidate_reviews", "array"),
            ("surviving_problem_ids", "array"),
            ("minority_objections", "array"),
            ("evidence_refs", "array"),
        ),
    ),
    "RESEARCHABILITY_ASSESSOR": CognitiveRoleContract(
        contract_id="researchability_assessor_contract_v0_1",
        role="RESEARCHABILITY_ASSESSOR",
        stage="RESEARCHABILITY",
        purpose="independently assess operationalization, falsifiability, tractability, cost, and required Harnesses",
        provider_operation_id="problem_researchability_assessment",
        allowed_input_message_types=("PROBLEM_CANDIDATE_SET",),
        output_message_type="RESEARCHABILITY_REPORT",
        required_output_fields=("assessments", "researchable_problem_ids", "missing_capabilities", "evidence_refs"),
        output_field_types=(
            ("assessments", "array"),
            ("researchable_problem_ids", "array"),
            ("missing_capabilities", "array"),
            ("evidence_refs", "array"),
        ),
    ),
    "AGENDA_SYNTHESIZER": CognitiveRoleContract(
        contract_id="agenda_synthesizer_contract_v0_1",
        role="AGENDA_SYNTHESIZER",
        stage="AGENDA_SYNTHESIS",
        purpose="select or stop from criticized and independently researchable problem candidates while preserving conflicts",
        provider_operation_id="group_agenda_synthesis_and_selection",
        allowed_input_message_types=(
            "PROBLEM_CANDIDATE_SET",
            "PROBLEM_CRITIQUE",
            "RESEARCHABILITY_REPORT",
        ),
        output_message_type="AGENDA_SELECTION_PROPOSAL",
        required_output_fields=(
            "decision",
            "selected_problem_id",
            "selection_rationale",
            "rejected_problem_ids",
            "unresolved_conflicts",
            "evidence_refs",
            "expected_cbit_gain",
            "stop_condition",
        ),
        output_field_types=(
            ("decision", "string"),
            ("selected_problem_id", "string"),
            ("selection_rationale", "string"),
            ("rejected_problem_ids", "array"),
            ("unresolved_conflicts", "array"),
            ("evidence_refs", "array"),
            ("expected_cbit_gain", "number"),
            ("stop_condition", "string"),
        ),
        output_enums=(("decision", ("SELECT", "STOP")),),
    ),
}


def standard_role_contract(role: str) -> CognitiveRoleContract:
    try:
        return _STANDARD_ROLE_CONTRACTS[role]
    except KeyError as exc:
        raise KeyError(f"standard_cognitive_role_not_found:{role}") from exc


@dataclass(frozen=True)
class CognitiveAgent:
    descriptor: AgentDescriptor
    contract: CognitiveRoleContract
    model_id: str
    private_memory_namespace: str
    harness_capabilities: tuple[str, ...]
    credit_subject_id: str

    def __post_init__(self) -> None:
        if self.descriptor.role != self.contract.role:
            raise ValueError("agent_role_contract_mismatch")
        if not all((self.model_id, self.private_memory_namespace, self.credit_subject_id)):
            raise ValueError("cognitive_agent_identity_binding_incomplete")
        if not self.harness_capabilities:
            raise ValueError("cognitive_agent_harness_capabilities_required")
        if not set(self.contract.required_output_fields):
            raise ValueError("cognitive_agent_output_contract_required")

    @property
    def agent_id(self) -> str:
        return self.descriptor.agent_id

    @property
    def role(self) -> str:
        return self.descriptor.role

    @property
    def provider_binding(self) -> str:
        return f"{self.descriptor.provider_id}/{self.model_id}"

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "role_contract_id": self.contract.contract_id,
            "runner_id": self.descriptor.runner_id,
            "harness_id": self.descriptor.harness_id,
            "provider_id": self.descriptor.provider_id,
            "model_id": self.model_id,
            "context_isolation_key": self.descriptor.context_isolation_key,
            "private_memory_namespace": self.private_memory_namespace,
            "harness_capabilities": list(self.harness_capabilities),
            "credit_subject_id": self.credit_subject_id,
            "allowed_evidence_scopes": list(self.descriptor.allowed_evidence_scopes),
            "final_state_authority": False,
        }


class PrivateAgentWorkspace:
    """Durable owner-scoped event log; only the owning agent receives the object."""

    def __init__(self, root: str | Path, owner_agent_id: str, namespace: str) -> None:
        if not owner_agent_id or not re.fullmatch(r"[A-Za-z0-9_.-]+", namespace):
            raise ValueError("private_workspace_identity_invalid")
        self.owner_agent_id = owner_agent_id
        self.namespace = namespace
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = (self.root / namespace / "events.jsonl").resolve()
        if self.root not in self.path.parents:
            raise ValueError("private_workspace_path_escape")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, requesting_agent_id: str, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._assert_owner(requesting_agent_id)
        history = self.history(requesting_agent_id)
        event = {
            "owner_agent_id": self.owner_agent_id,
            "namespace": self.namespace,
            "event_type": event_type,
            "payload": payload,
            "previous_event_hash": history[-1]["event_hash"] if history else "",
            "created_at": _utc_now(),
        }
        event["event_hash"] = _hash_payload(event)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
        return event

    def history(self, requesting_agent_id: str) -> tuple[dict[str, Any], ...]:
        self._assert_owner(requesting_agent_id)
        if not self.path.exists():
            return ()
        return tuple(json.loads(line) for line in self.path.read_text(encoding="utf-8").splitlines() if line)

    def public_descriptor(self) -> dict[str, str]:
        return {
            "owner_agent_id": self.owner_agent_id,
            "namespace": self.namespace,
            "persistence": "owner_scoped_hash_chained_jsonl",
        }

    def _assert_owner(self, requesting_agent_id: str) -> None:
        if requesting_agent_id != self.owner_agent_id:
            raise PermissionError("private_workspace_owner_mismatch")


@dataclass(frozen=True)
class CognitiveMessage:
    message_id: str
    session_id: str
    sender_agent_id: str
    sender_role: str
    message_type: str
    payload: dict[str, Any]
    evidence_refs: tuple[str, ...]
    parent_message_refs: tuple[str, ...] = ()
    created_at: str = field(default_factory=_utc_now)
    message_hash: str = ""

    @classmethod
    def create(
        cls,
        *,
        message_id: str,
        session_id: str,
        sender_agent_id: str,
        sender_role: str,
        message_type: str,
        payload: dict[str, Any],
        evidence_refs: tuple[str, ...],
        parent_message_refs: tuple[str, ...] = (),
    ) -> "CognitiveMessage":
        if _contains_private_export(payload):
            raise ValueError("private_reasoning_export_forbidden")
        if not all((message_id, session_id, sender_agent_id, sender_role, message_type)):
            raise ValueError("formal_cognitive_message_identity_incomplete")
        if not evidence_refs:
            raise ValueError("formal_cognitive_message_evidence_required")
        created_at = _utc_now()
        committed = {
            "message_id": message_id,
            "session_id": session_id,
            "sender_agent_id": sender_agent_id,
            "sender_role": sender_role,
            "message_type": message_type,
            "payload": payload,
            "evidence_refs": list(evidence_refs),
            "parent_message_refs": list(parent_message_refs),
            "created_at": created_at,
        }
        return cls(
            message_id=message_id,
            session_id=session_id,
            sender_agent_id=sender_agent_id,
            sender_role=sender_role,
            message_type=message_type,
            payload=payload,
            evidence_refs=evidence_refs,
            parent_message_refs=parent_message_refs,
            created_at=created_at,
            message_hash=_hash_payload(committed),
        )

    def as_dict(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "sender_agent_id": self.sender_agent_id,
            "sender_role": self.sender_role,
            "message_type": self.message_type,
            "payload": self.payload,
            "evidence_refs": list(self.evidence_refs),
            "parent_message_refs": list(self.parent_message_refs),
            "created_at": self.created_at,
            "message_hash": self.message_hash,
        }


def _contains_private_export(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in _PRIVATE_EXPORT_KEYS for key in value):
            return True
        return any(_contains_private_export(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_private_export(item) for item in value)
    return False
