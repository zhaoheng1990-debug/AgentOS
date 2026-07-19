"""Group problem-definition runtime with provider support and Kernel-owned agenda state."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AgendaCandidate,
    AgendaSelection,
    EndogenousAgendaLoop,
    OpenProblem,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    ProviderBackedRuntimeCognitionLayer,
)

from .cognitive_roles import CognitiveAgent, CognitiveMessage, PrivateAgentWorkspace
from .deliberation import (
    AgentAdapterResult,
    CognitiveContextView,
    CognitiveExecutionReceipt,
    CognitiveWorkOrder,
    DeliberationEventStore,
)


ENDOGENOUS_PROBLEM_RUNTIME_VERSION = "endogenous_problem_runtime_v0_1"

PROBLEM_STAGES = (
    "PROBLEM_FRAMING",
    "PROBLEM_REVIEW",
    "RESEARCHABILITY",
    "AGENDA_SYNTHESIS",
    "CANDIDATE",
    "BLOCKED",
)

_STAGE_ROLE = {
    "PROBLEM_FRAMING": "PROBLEM_FRAMER",
    "PROBLEM_REVIEW": "PROBLEM_CRITIC",
    "RESEARCHABILITY": "RESEARCHABILITY_ASSESSOR",
    "AGENDA_SYNTHESIS": "AGENDA_SYNTHESIZER",
}

_NEXT_STAGE = {
    "PROBLEM_FRAMING": "PROBLEM_REVIEW",
    "PROBLEM_REVIEW": "RESEARCHABILITY",
    "RESEARCHABILITY": "AGENDA_SYNTHESIS",
    "AGENDA_SYNTHESIS": "CANDIDATE",
}

_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}

_AUTHORITY_KEYS = {
    "accepted",
    "asset_promotion_authorized",
    "execution_authorized",
    "final_candidate_state",
    "permission_granted",
    "published",
}

_NESTED_OUTPUT_CONTRACTS = {
    "PROBLEM_FRAMING": {
        "problem_candidates": {
            "minimum_items": 2,
            "item_required_fields": [
                "problem_id",
                "question",
                "research_object",
                "scope",
                "triggering_anomaly",
                "rival_explanations",
                "falsifier",
                "evidence_refs",
                "expected_cbit_gain",
                "urgency",
                "novelty",
            ],
            "unit_interval_fields": ["expected_cbit_gain", "urgency", "novelty"],
        }
    },
    "PROBLEM_REVIEW": {
        "candidate_reviews": {
            "cover_all_generated_problem_ids": True,
            "item_required_fields": [
                "problem_id",
                "premise_risk",
                "redundancy_risk",
                "negative_transfer_risk",
                "challenge",
                "evidence_refs",
            ],
            "unit_interval_fields": ["premise_risk", "redundancy_risk", "negative_transfer_risk"],
        }
    },
    "RESEARCHABILITY": {
        "assessments": {
            "cover_all_generated_problem_ids": True,
            "item_required_fields": [
                "problem_id",
                "operationalization",
                "falsifiability",
                "tractability",
                "normalized_cost",
                "required_harnesses",
                "evidence_refs",
            ],
            "unit_interval_fields": ["falsifiability", "tractability", "normalized_cost"],
        }
    },
    "AGENDA_SYNTHESIS": {
        "selection_rules": [
            "selected_problem_id must be generated, survive critique, and be researchable",
            "rejected_problem_ids must contain every generated id except the selected id",
            "STOP uses selected_problem_id NONE and rejects every generated id",
        ]
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _message_ref(message: CognitiveMessage) -> str:
    return f"message://{message.message_id}/{message.message_hash}"


@dataclass(frozen=True)
class DeliberationSeed:
    seed_id: str
    source_problem_id: str
    objective: str
    research_object: str
    project_scope: str
    evidence_refs: tuple[str, ...]
    rival_explanations: tuple[str, ...]
    operationalization: str
    falsifier: str
    required_harnesses: tuple[str, ...]
    unresolved_conflicts: tuple[Any, ...]
    expected_cbit_gain: float
    agenda_selection_receipt_ref: str
    candidate_state: str = "PENDING_AGENDA_REVIEW"
    execution_authorized: bool = False
    created_at: str = field(default_factory=_utc_now)
    seed_hash: str = ""

    def __post_init__(self) -> None:
        if not all(
            (
                self.seed_id,
                self.source_problem_id,
                self.objective,
                self.research_object,
                self.project_scope,
                self.operationalization,
                self.falsifier,
                self.agenda_selection_receipt_ref,
            )
        ):
            raise ValueError("deliberation_seed_identity_incomplete")
        if not self.evidence_refs:
            raise ValueError("deliberation_seed_evidence_required")
        if self.candidate_state != "PENDING_AGENDA_REVIEW":
            raise ValueError("deliberation_seed_state_must_be_pending_agenda_review")
        if self.execution_authorized:
            raise ValueError("deliberation_seed_cannot_carry_execution_authority")
        if not _is_unit_number(self.expected_cbit_gain):
            raise ValueError("deliberation_seed_expected_cbit_gain_invalid")

    @classmethod
    def create(cls, **values: Any) -> "DeliberationSeed":
        created_at = _utc_now()
        committed = {**values, "created_at": created_at}
        return cls(**values, created_at=created_at, seed_hash=_hash_payload(committed))

    def as_dict(self) -> dict[str, Any]:
        return {
            "seed_id": self.seed_id,
            "source_problem_id": self.source_problem_id,
            "objective": self.objective,
            "research_object": self.research_object,
            "project_scope": self.project_scope,
            "evidence_refs": list(self.evidence_refs),
            "rival_explanations": list(self.rival_explanations),
            "operationalization": self.operationalization,
            "falsifier": self.falsifier,
            "required_harnesses": list(self.required_harnesses),
            "unresolved_conflicts": list(self.unresolved_conflicts),
            "expected_cbit_gain": self.expected_cbit_gain,
            "agenda_selection_receipt_ref": self.agenda_selection_receipt_ref,
            "candidate_state": self.candidate_state,
            "execution_authorized": self.execution_authorized,
            "created_at": self.created_at,
            "seed_hash": self.seed_hash,
        }

    def as_coordination_intake(self) -> dict[str, Any]:
        return {
            "objective": self.objective,
            "project_scope": self.project_scope,
            "evidence_refs": list(self.evidence_refs),
            "evidence_payload": {
                "source_problem_id": self.source_problem_id,
                "research_object": self.research_object,
                "rival_explanations": list(self.rival_explanations),
                "operationalization": self.operationalization,
                "falsifier": self.falsifier,
                "required_harnesses": list(self.required_harnesses),
                "unresolved_conflicts": list(self.unresolved_conflicts),
                "expected_cbit_gain": self.expected_cbit_gain,
                "source_seed_ref": f"deliberation-seed://{self.seed_id}/{self.seed_hash}",
            },
            "candidate_state": self.candidate_state,
            "execution_authorized": False,
        }


@dataclass(frozen=True)
class ProblemDefinitionSnapshot:
    session_id: str
    stage: str
    candidate_state: str
    messages: tuple[CognitiveMessage, ...]
    execution_receipts: tuple[CognitiveExecutionReceipt, ...]
    blocked_stage: str = ""
    agenda_selection: AgendaSelection | None = None
    deliberation_seed: DeliberationSeed | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "stage": self.stage,
            "candidate_state": self.candidate_state,
            "blocked_stage": self.blocked_stage,
            "messages": [message.as_dict() for message in self.messages],
            "execution_receipts": [receipt.as_dict() for receipt in self.execution_receipts],
            "agenda_selection": self.agenda_selection.as_dict() if self.agenda_selection else None,
            "deliberation_seed": self.deliberation_seed.as_dict() if self.deliberation_seed else None,
        }


class EndogenousProblemRuntime:
    """Four independent problem roles that produce a pending deliberation seed."""

    module_id = ENDOGENOUS_PROBLEM_RUNTIME_VERSION
    capabilities = (
        "plural_problem_framing",
        "adversarial_problem_review",
        "independent_researchability_assessment",
        "provider_backed_agenda_selection",
    )

    def __init__(
        self,
        *,
        session_id: str,
        discovery_objective: str,
        project_scope: str,
        evidence_refs: tuple[str, ...],
        evidence_payload: dict[str, Any],
        agents: tuple[CognitiveAgent, ...],
        adapters: dict[str, Any],
        workspace_root: str | Path,
        kernel_authorization_ref: str,
        minimum_priority: float = 0.2,
        invalidated_evidence_refs: tuple[str, ...] = (),
    ) -> None:
        if not all((session_id, discovery_objective, project_scope, kernel_authorization_ref)):
            raise ValueError("problem_runtime_identity_incomplete")
        if not evidence_refs:
            raise ValueError("problem_runtime_evidence_required")
        self.session_id = session_id
        self.discovery_objective = discovery_objective
        self.project_scope = project_scope
        unknown_invalidated = set(invalidated_evidence_refs) - set(evidence_refs)
        if unknown_invalidated:
            raise ValueError("problem_runtime_unknown_invalidated_evidence_ref")
        self.invalidated_evidence_refs = tuple(invalidated_evidence_refs)
        self.evidence_refs = tuple(ref for ref in evidence_refs if ref not in invalidated_evidence_refs)
        if not self.evidence_refs:
            raise ValueError("problem_runtime_no_valid_evidence_after_invalidation")
        self.evidence_payload = dict(evidence_payload)
        self.kernel_authorization_ref = kernel_authorization_ref
        self._agents = {agent.role: agent for agent in agents}
        self._adapters = dict(adapters)
        self._messages: list[CognitiveMessage] = []
        self._receipts: list[CognitiveExecutionReceipt] = []
        self._stage = "PROBLEM_FRAMING"
        self._blocked_stage = ""
        self._candidate_state = "NOT_FORMED"
        self._agenda_selection: AgendaSelection | None = None
        self._deliberation_seed: DeliberationSeed | None = None
        self._cognition_layer = ProviderBackedRuntimeCognitionLayer()
        self._agenda = EndogenousAgendaLoop(minimum_priority=minimum_priority)
        self._validate_team(agents)
        self._workspaces = {
            agent.agent_id: PrivateAgentWorkspace(workspace_root, agent.agent_id, agent.private_memory_namespace)
            for agent in agents
        }
        public_root = Path(workspace_root).resolve().parent / "problem-definition-public"
        self._event_store = DeliberationEventStore(public_root, session_id)
        self._persist(
            "PROBLEM_SESSION_INITIALIZED",
            {
                "discovery_objective_hash": _hash_payload(discovery_objective),
                "seeded_problem_questions": [],
                "kernel_authorization_ref": kernel_authorization_ref,
            },
        )

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def verify_replay(self) -> dict[str, Any]:
        return self._event_store.verify()

    def record_agenda_feedback(self, feedback: Any) -> tuple[str, ...]:
        """Apply a terminal lifecycle receipt to the owning agenda without route selection."""

        if self._agenda_selection is None or self._agenda_selection.decision != "SELECT":
            raise RuntimeError("problem_runtime_has_no_selected_agenda_candidate")
        if feedback.candidate_id != self._agenda_selection.candidate_id:
            raise ValueError("problem_runtime_feedback_candidate_mismatch")
        residual_ids = self._agenda.record_feedback(feedback)
        self._persist(
            "PROBLEM_AGENDA_FEEDBACK_RECORDED",
            {
                "candidate_id": feedback.candidate_id,
                "problem_resolution": feedback.problem_resolution,
                "observed_cbit_gain": feedback.observed_cbit_gain,
                "provider_support_receipt_ref": feedback.provider_support_receipt_ref,
                "residual_problem_ids": list(residual_ids),
            },
        )
        return residual_ids

    def execute_current(self) -> ProblemDefinitionSnapshot:
        if self._stage == "BLOCKED":
            raise RuntimeError("problem_runtime_blocked_use_retry_blocked")
        if self._stage == "CANDIDATE":
            return self.snapshot()
        stage = self._stage
        role = _STAGE_ROLE[stage]
        agent = self._agents[role]
        contract = agent.contract
        workspace = self._workspaces[agent.agent_id]
        input_messages, excluded_refs = self._select_input_messages(contract.allowed_input_message_types)
        input_refs = tuple(_message_ref(message) for message in input_messages)
        allowed_evidence = tuple(dict.fromkeys((*self.evidence_refs, *input_refs)))
        context = CognitiveContextView(
            session_id=self.session_id,
            objective=self.discovery_objective,
            project_scope=self.project_scope,
            role=role,
            context_isolation_key=agent.descriptor.context_isolation_key,
            private_workspace_descriptor=workspace.public_descriptor(),
            frozen_gate_refs=(),
            evidence_refs=self.evidence_refs,
            evidence_payload=self.evidence_payload,
            input_messages=input_messages,
            excluded_message_refs=excluded_refs,
            runtime_state={
                "runtime": "endogenous_problem_definition",
                "current_stage": stage,
                "seeded_problem_questions": [],
                "formal_candidate_state": self._candidate_state,
                "kernel_final_selection_owner": True,
                "invalidated_evidence_refs": list(self.invalidated_evidence_refs),
                "required_project_scope": self.project_scope,
                "allowed_evidence_refs": list(allowed_evidence),
                "nested_output_contract": _NESTED_OUTPUT_CONTRACTS[stage],
            },
        )
        work_order = CognitiveWorkOrder(
            work_order_id=f"{self.session_id}-{stage.lower()}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            agent_id=agent.agent_id,
            role=role,
            stage=stage,
            objective=(
                f"{contract.purpose}; every nested scope field must equal the exact JSON string "
                f"{self.project_scope!r}"
            ),
            role_contract_id=contract.contract_id,
            input_message_refs=input_refs,
            allowed_evidence_refs=allowed_evidence,
            output_schema=self._stage_output_schema(stage, contract.expected_schema()),
            kernel_authorization_ref=self.kernel_authorization_ref,
        )
        workspace.append(agent.agent_id, "PROBLEM_WORK_ORDER_RECEIVED", {"work_order": work_order.as_dict()})
        try:
            result = self._adapters[agent.agent_id].invoke(agent, work_order, context, workspace)
        except Exception as exc:
            return self._block(
                stage,
                agent,
                work_order,
                context,
                None,
                {},
                (f"problem_agent_adapter_error:{type(exc).__name__}:{exc}",),
            )
        errors, provider_audit = self._validate_result(stage, agent, work_order, result)
        if errors:
            return self._block(stage, agent, work_order, context, result, provider_audit, tuple(errors))

        payload = result.provider_support_receipt or {}
        message = CognitiveMessage.create(
            message_id=f"{self.session_id}-{contract.output_message_type.lower()}-{len(self._messages) + 1}",
            session_id=self.session_id,
            sender_agent_id=agent.agent_id,
            sender_role=role,
            message_type=contract.output_message_type,
            payload=payload,
            evidence_refs=tuple(payload["evidence_refs"]),
            parent_message_refs=input_refs,
        )
        receipt = CognitiveExecutionReceipt.create(
            receipt_id=f"problem-execution-{self.session_id}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            work_order_id=work_order.work_order_id,
            agent_id=agent.agent_id,
            role=role,
            stage=stage,
            status="COMPLETED",
            context_hash=context.context_hash,
            work_order_hash=work_order.work_order_hash,
            provider_id=result.provider_id,
            model_id=result.model_id,
            invocation_receipt_ref=result.invocation_receipt_ref,
            provider_audit=provider_audit,
            provider_invocation_receipt=(result.provider_envelope or {}).get("invocation_receipt", {}),
            message_ref=_message_ref(message),
        )
        self._messages.append(message)
        self._receipts.append(receipt)
        workspace.append(
            agent.agent_id,
            "PROBLEM_FORMAL_MESSAGE_EMITTED",
            {"message_ref": receipt.message_ref, "execution_receipt_hash": receipt.receipt_hash},
        )
        self._stage = _NEXT_STAGE[stage]
        if self._stage == "CANDIDATE":
            self._form_agenda_candidate(payload, receipt)
        self._persist(
            "PROBLEM_ROLE_COMPLETED",
            {
                "stage": stage,
                "role": role,
                "message_ref": receipt.message_ref,
                "execution_receipt_hash": receipt.receipt_hash,
                "next_stage": self._stage,
            },
        )
        return self.snapshot()

    def retry_blocked(self) -> ProblemDefinitionSnapshot:
        if self._stage != "BLOCKED" or not self._blocked_stage:
            raise RuntimeError("problem_runtime_not_blocked")
        self._stage = self._blocked_stage
        self._blocked_stage = ""
        return self.execute_current()

    def run_to_candidate(self, *, max_retries_per_stage: int = 0) -> ProblemDefinitionSnapshot:
        if max_retries_per_stage < 0:
            raise ValueError("max_retries_per_stage_must_be_nonnegative")
        retries: dict[str, int] = {}
        while self._stage != "CANDIDATE":
            if self._stage == "BLOCKED":
                stage = self._blocked_stage
                used = retries.get(stage, 0)
                if used >= max_retries_per_stage:
                    break
                retries[stage] = used + 1
                self.retry_blocked()
                continue
            self.execute_current()
        return self.snapshot()

    def snapshot(self) -> ProblemDefinitionSnapshot:
        return ProblemDefinitionSnapshot(
            session_id=self.session_id,
            stage=self._stage,
            candidate_state=self._candidate_state,
            messages=tuple(self._messages),
            execution_receipts=tuple(self._receipts),
            blocked_stage=self._blocked_stage,
            agenda_selection=self._agenda_selection,
            deliberation_seed=self._deliberation_seed,
        )

    def _validate_team(self, agents: tuple[CognitiveAgent, ...]) -> None:
        if set(self._agents) != set(_STAGE_ROLE.values()) or len(agents) != 4:
            raise ValueError("problem_runtime_requires_exactly_four_problem_roles")
        if len({agent.agent_id for agent in agents}) != 4:
            raise ValueError("problem_team_agent_identity_not_isolated")
        if len({agent.descriptor.context_isolation_key for agent in agents}) != 4:
            raise ValueError("problem_team_context_not_isolated")
        if len({agent.private_memory_namespace for agent in agents}) != 4:
            raise ValueError("problem_team_private_memory_not_isolated")
        if len({agent.credit_subject_id for agent in agents}) != 4:
            raise ValueError("problem_team_credit_identity_not_isolated")
        if any(self.project_scope not in agent.descriptor.allowed_evidence_scopes for agent in agents):
            raise ValueError("problem_agent_project_scope_not_allowed")
        if set(self._adapters) != {agent.agent_id for agent in agents}:
            raise ValueError("problem_agent_adapter_binding_incomplete")

    def _stage_output_schema(self, stage: str, base_schema: dict[str, Any]) -> dict[str, Any]:
        schema = json.loads(json.dumps(base_schema))
        properties = schema["properties"]
        string_array = {"type": "array", "items": {"type": "string"}}
        if stage == "PROBLEM_FRAMING":
            properties["problem_candidates"].update(
                {
                    "minItems": 2,
                    "items": {
                        "type": "object",
                        "required": list(_NESTED_OUTPUT_CONTRACTS[stage]["problem_candidates"]["item_required_fields"]),
                        "properties": {
                            "problem_id": {"type": "string"},
                            "question": {"type": "string"},
                            "research_object": {"type": "string"},
                            "scope": {"type": "string", "enum": [self.project_scope]},
                            "triggering_anomaly": {"type": "string"},
                            "rival_explanations": string_array,
                            "falsifier": {"type": "string"},
                            "evidence_refs": {
                                "type": "array",
                                "minItems": 1,
                                "items": {"type": "string", "enum": list(self.evidence_refs)},
                            },
                            "expected_cbit_gain": {"type": "number", "minimum": 0, "maximum": 1},
                            "urgency": {"type": "number", "minimum": 0, "maximum": 1},
                            "novelty": {"type": "number", "minimum": 0, "maximum": 1},
                        },
                    },
                }
            )
            return schema
        candidate_ids = list(self._candidate_map())
        candidate_id = {"type": "string", "enum": candidate_ids}
        if stage == "PROBLEM_REVIEW":
            properties["candidate_reviews"]["items"] = {
                "type": "object",
                "required": list(_NESTED_OUTPUT_CONTRACTS[stage]["candidate_reviews"]["item_required_fields"]),
                "properties": {
                    "problem_id": candidate_id,
                    "premise_risk": {"type": "number", "minimum": 0, "maximum": 1},
                    "redundancy_risk": {"type": "number", "minimum": 0, "maximum": 1},
                    "negative_transfer_risk": {"type": "number", "minimum": 0, "maximum": 1},
                    "challenge": {"type": "string"},
                    "evidence_refs": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "enum": list(self.evidence_refs)},
                    },
                },
            }
            properties["surviving_problem_ids"]["items"] = candidate_id
            return schema
        if stage == "RESEARCHABILITY":
            properties["assessments"]["items"] = {
                "type": "object",
                "required": list(_NESTED_OUTPUT_CONTRACTS[stage]["assessments"]["item_required_fields"]),
                "properties": {
                    "problem_id": candidate_id,
                    "operationalization": {"type": "string"},
                    "falsifiability": {"type": "number", "minimum": 0, "maximum": 1},
                    "tractability": {"type": "number", "minimum": 0, "maximum": 1},
                    "normalized_cost": {"type": "number", "minimum": 0, "maximum": 1},
                    "required_harnesses": string_array,
                    "evidence_refs": {
                        "type": "array",
                        "minItems": 1,
                        "items": {"type": "string", "enum": list(self.evidence_refs)},
                    },
                },
            }
            properties["researchable_problem_ids"]["items"] = candidate_id
            return schema
        properties["selected_problem_id"]["enum"] = [*candidate_ids, "NONE"]
        properties["rejected_problem_ids"]["items"] = candidate_id
        return schema

    def _select_input_messages(
        self,
        allowed_types: tuple[str, ...],
    ) -> tuple[tuple[CognitiveMessage, ...], tuple[str, ...]]:
        selected = tuple(message for message in self._messages if message.message_type in allowed_types)
        excluded = tuple(_message_ref(message) for message in self._messages if message.message_type not in allowed_types)
        return selected, excluded

    def _validate_result(
        self,
        stage: str,
        agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        result: AgentAdapterResult,
    ) -> tuple[list[str], dict[str, Any]]:
        errors = list(result.validation_errors)
        if result.status != "COMPLETED":
            errors.append(f"problem_agent_adapter_status:{result.status}")
        if result.status == "COMPLETED" and (
            result.provider_id != agent.descriptor.provider_id or result.model_id != agent.model_id
        ):
            errors.append("problem_agent_provider_binding_mismatch")
        if not result.invocation_receipt_ref:
            errors.append("provider_invocation_receipt_ref_required")
        payload = result.provider_support_receipt
        if not isinstance(payload, dict):
            errors.append("provider_support_receipt_required")
            return list(dict.fromkeys(errors)), {}
        errors.extend(_validate_schema(work_order.output_schema, payload))
        if not payload.get("evidence_refs"):
            errors.append("problem_provider_evidence_refs_required")
        if _contains_authority_key(payload):
            errors.append("problem_agent_final_state_authority_forbidden")
        provider_evidence = payload.get("evidence_refs")
        if isinstance(provider_evidence, list) and any(
            ref not in work_order.allowed_evidence_refs for ref in provider_evidence
        ):
            errors.append("problem_provider_evidence_ref_not_admitted")
        errors.extend(self._validate_stage_payload(stage, payload, work_order.allowed_evidence_refs))
        provider_audit = self._cognition_layer.audit_operation(
            agent.contract.provider_operation_id,
            {"provider_support_receipt": payload},
        )
        if provider_audit["status"] not in _PASS_PROVIDER_AUDITS:
            errors.append(f"provider_support_audit:{provider_audit['status']}")
        return list(dict.fromkeys(errors)), provider_audit

    def _validate_stage_payload(
        self,
        stage: str,
        payload: dict[str, Any],
        allowed_evidence_refs: tuple[str, ...],
    ) -> list[str]:
        if stage == "PROBLEM_FRAMING":
            return self._validate_framing(payload, allowed_evidence_refs)
        if stage == "PROBLEM_REVIEW":
            return self._validate_review(payload, allowed_evidence_refs)
        if stage == "RESEARCHABILITY":
            return self._validate_researchability(payload, allowed_evidence_refs)
        return self._validate_selection(payload)

    def _validate_framing(
        self,
        payload: dict[str, Any],
        allowed_evidence_refs: tuple[str, ...],
    ) -> list[str]:
        candidates = payload.get("problem_candidates")
        if not isinstance(candidates, list):
            return []
        errors: list[str] = []
        if len(candidates) < 2:
            errors.append("problem_candidate_plurality_required")
        ids: list[str] = []
        questions: list[str] = []
        required = {
            "problem_id",
            "question",
            "research_object",
            "scope",
            "triggering_anomaly",
            "rival_explanations",
            "falsifier",
            "evidence_refs",
            "expected_cbit_gain",
            "urgency",
            "novelty",
        }
        for index, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                errors.append(f"problem_candidate_not_object:{index}")
                continue
            missing = required - set(candidate)
            errors.extend(f"problem_candidate_missing_field:{index}:{name}" for name in sorted(missing))
            problem_id = str(candidate.get("problem_id", ""))
            question = str(candidate.get("question", "")).strip()
            ids.append(problem_id)
            questions.append(question)
            if not re.fullmatch(r"[A-Za-z0-9_.-]+", problem_id):
                errors.append(f"problem_candidate_id_invalid:{index}")
            if not question or question == self.discovery_objective.strip():
                errors.append(f"problem_candidate_question_not_internally_derived:{index}")
            if candidate.get("scope") != self.project_scope:
                errors.append(f"problem_candidate_scope_mismatch:{problem_id}")
            for field_name in ("research_object", "triggering_anomaly", "falsifier"):
                if not str(candidate.get(field_name, "")).strip():
                    errors.append(f"problem_candidate_semantic_field_empty:{problem_id}:{field_name}")
            if not isinstance(candidate.get("rival_explanations"), list):
                errors.append(f"problem_candidate_rivals_not_array:{problem_id}")
            errors.extend(
                _nested_evidence_errors(
                    candidate.get("evidence_refs"),
                    allowed_evidence_refs,
                    f"problem_candidate:{problem_id}",
                )
            )
            for metric in ("expected_cbit_gain", "urgency", "novelty"):
                if not _is_unit_number(candidate.get(metric)):
                    errors.append(f"problem_candidate_metric_invalid:{problem_id}:{metric}")
        if len(set(ids)) != len(ids):
            errors.append("problem_candidate_ids_not_unique")
        if len(set(questions)) != len(questions):
            errors.append("problem_candidate_questions_not_unique")
        return errors

    def _validate_review(
        self,
        payload: dict[str, Any],
        allowed_evidence_refs: tuple[str, ...],
    ) -> list[str]:
        candidate_ids = set(self._candidate_map())
        reviews = payload.get("candidate_reviews")
        if not isinstance(reviews, list):
            return []
        errors: list[str] = []
        review_ids: list[str] = []
        for index, review in enumerate(reviews):
            if not isinstance(review, dict):
                errors.append(f"problem_review_not_object:{index}")
                continue
            problem_id = str(review.get("problem_id", ""))
            review_ids.append(problem_id)
            if problem_id not in candidate_ids:
                errors.append(f"problem_review_unknown_candidate_id:{problem_id}")
            for metric in ("premise_risk", "redundancy_risk", "negative_transfer_risk"):
                if not _is_unit_number(review.get(metric)):
                    errors.append(f"problem_review_metric_invalid:{problem_id}:{metric}")
            if not str(review.get("challenge", "")).strip():
                errors.append(f"problem_review_challenge_required:{problem_id}")
            errors.extend(
                _nested_evidence_errors(
                    review.get("evidence_refs"),
                    allowed_evidence_refs,
                    f"problem_review:{problem_id}",
                )
            )
        if set(review_ids) != candidate_ids:
            errors.append("problem_review_must_cover_all_candidates")
        if len(review_ids) != len(set(review_ids)):
            errors.append("problem_review_candidate_ids_not_unique")
        surviving = payload.get("surviving_problem_ids")
        if isinstance(surviving, list):
            if len(surviving) != len(set(surviving)):
                errors.append("problem_surviving_candidate_ids_not_unique")
            for problem_id in surviving:
                if problem_id not in candidate_ids:
                    errors.append(f"problem_review_unknown_candidate_id:{problem_id}")
        return errors

    def _validate_researchability(
        self,
        payload: dict[str, Any],
        allowed_evidence_refs: tuple[str, ...],
    ) -> list[str]:
        candidate_ids = set(self._candidate_map())
        assessments = payload.get("assessments")
        if not isinstance(assessments, list):
            return []
        errors: list[str] = []
        assessment_ids: list[str] = []
        for index, assessment in enumerate(assessments):
            if not isinstance(assessment, dict):
                errors.append(f"researchability_assessment_not_object:{index}")
                continue
            problem_id = str(assessment.get("problem_id", ""))
            assessment_ids.append(problem_id)
            if problem_id not in candidate_ids:
                errors.append(f"researchability_unknown_candidate_id:{problem_id}")
            if not str(assessment.get("operationalization", "")).strip():
                errors.append(f"researchability_operationalization_required:{problem_id}")
            for metric in ("falsifiability", "tractability", "normalized_cost"):
                if not _is_unit_number(assessment.get(metric)):
                    errors.append(f"researchability_metric_invalid:{problem_id}:{metric}")
            if not isinstance(assessment.get("required_harnesses"), list):
                errors.append(f"researchability_harnesses_not_array:{problem_id}")
            errors.extend(
                _nested_evidence_errors(
                    assessment.get("evidence_refs"),
                    allowed_evidence_refs,
                    f"researchability:{problem_id}",
                )
            )
        if set(assessment_ids) != candidate_ids:
            errors.append("researchability_must_cover_all_candidates")
        if len(assessment_ids) != len(set(assessment_ids)):
            errors.append("researchability_candidate_ids_not_unique")
        researchable = payload.get("researchable_problem_ids")
        if isinstance(researchable, list):
            if len(researchable) != len(set(researchable)):
                errors.append("researchable_candidate_ids_not_unique")
            for problem_id in researchable:
                if problem_id not in candidate_ids:
                    errors.append(f"researchability_unknown_candidate_id:{problem_id}")
                assessment = next(
                    (
                        item
                        for item in assessments
                        if isinstance(item, dict) and item.get("problem_id") == problem_id
                    ),
                    {},
                )
                if not assessment.get("required_harnesses"):
                    errors.append(f"researchable_candidate_harness_required:{problem_id}")
        return errors

    def _validate_selection(self, payload: dict[str, Any]) -> list[str]:
        candidate_ids = set(self._candidate_map())
        surviving = set(self._message_payload("PROBLEM_CRITIQUE").get("surviving_problem_ids", []))
        researchable = set(self._message_payload("RESEARCHABILITY_REPORT").get("researchable_problem_ids", []))
        selected = str(payload.get("selected_problem_id", ""))
        rejected = set(payload.get("rejected_problem_ids", [])) if isinstance(payload.get("rejected_problem_ids"), list) else set()
        errors: list[str] = []
        if not str(payload.get("selection_rationale", "")).strip():
            errors.append("agenda_selection_rationale_required")
        if not str(payload.get("stop_condition", "")).strip():
            errors.append("agenda_stop_condition_required")
        if not _is_unit_number(payload.get("expected_cbit_gain")):
            errors.append("agenda_expected_cbit_gain_invalid")
        if payload.get("decision") == "SELECT":
            if selected not in candidate_ids:
                errors.append("agenda_selection_unknown_candidate")
            if selected not in surviving:
                errors.append("agenda_selection_did_not_survive_critique")
            if selected not in researchable:
                errors.append("agenda_selection_not_researchable")
            if rejected != candidate_ids - {selected}:
                errors.append("agenda_rejected_problem_set_incomplete")
            if selected in candidate_ids and self._problem_priority(selected) < self._agenda.minimum_priority:
                errors.append("agenda_selected_candidate_below_runtime_priority_gate")
        elif payload.get("decision") == "STOP":
            if selected not in {"", "NONE"}:
                errors.append("agenda_stop_selected_problem_must_be_none")
            if rejected != candidate_ids:
                errors.append("agenda_stop_must_reject_all_candidates")
        return errors

    def _problem_priority(self, problem_id: str) -> float:
        candidate = self._candidate_map()[problem_id]
        review = next(
            item
            for item in self._message_payload("PROBLEM_CRITIQUE").get("candidate_reviews", [])
            if item.get("problem_id") == problem_id
        )
        assessment = next(
            item
            for item in self._message_payload("RESEARCHABILITY_REPORT").get("assessments", [])
            if item.get("problem_id") == problem_id
        )
        return round(
            0.35 * float(candidate["expected_cbit_gain"])
            + 0.20 * float(assessment["falsifiability"])
            + 0.15 * float(assessment["tractability"])
            + 0.15 * float(candidate["urgency"])
            + 0.15 * float(candidate["novelty"])
            - 0.25 * float(review["negative_transfer_risk"])
            - 0.15 * float(assessment["normalized_cost"]),
            12,
        )

    def _candidate_map(self) -> dict[str, dict[str, Any]]:
        payload = self._message_payload("PROBLEM_CANDIDATE_SET")
        return {
            str(candidate.get("problem_id")): candidate
            for candidate in payload.get("problem_candidates", [])
            if isinstance(candidate, dict)
        }

    def _message_payload(self, message_type: str) -> dict[str, Any]:
        for message in self._messages:
            if message.message_type == message_type:
                return message.payload
        return {}

    def _form_agenda_candidate(
        self,
        selection_payload: dict[str, Any],
        receipt: CognitiveExecutionReceipt,
    ) -> None:
        candidates = self._candidate_map()
        reviews = {
            str(item.get("problem_id")): item
            for item in self._message_payload("PROBLEM_CRITIQUE").get("candidate_reviews", [])
            if isinstance(item, dict)
        }
        assessments = {
            str(item.get("problem_id")): item
            for item in self._message_payload("RESEARCHABILITY_REPORT").get("assessments", [])
            if isinstance(item, dict)
        }
        support_ref = f"problem-selection://{receipt.receipt_hash}"
        for problem_id, candidate in candidates.items():
            review = reviews[problem_id]
            assessment = assessments[problem_id]
            self._agenda.register_problem(
                OpenProblem(
                    problem_id=problem_id,
                    statement=str(candidate["question"]),
                    research_object=str(candidate["research_object"]),
                    scope=self.project_scope,
                    evidence_refs=tuple(candidate["evidence_refs"]),
                    rival_explanations=tuple(str(item) for item in candidate["rival_explanations"]),
                )
            )
            self._agenda.propose(
                AgendaCandidate(
                    candidate_id=f"agenda-{problem_id}",
                    problem_id=problem_id,
                    proposed_question=str(candidate["question"]),
                    scope=self.project_scope,
                    provider_support_receipt_ref=support_ref,
                    evidence_refs=tuple(candidate["evidence_refs"]),
                    expected_cbit_gain=float(candidate["expected_cbit_gain"]),
                    falsifiability=float(assessment["falsifiability"]),
                    tractability=float(assessment["tractability"]),
                    urgency=float(candidate["urgency"]),
                    novelty=float(candidate["novelty"]),
                    negative_transfer_risk=float(review["negative_transfer_risk"]),
                    normalized_cost=float(assessment["normalized_cost"]),
                )
            )
        if selection_payload["decision"] == "STOP":
            self._agenda_selection = AgendaSelection(
                decision="STOP",
                candidate_id="",
                problem_id="",
                priority_score=0.0,
                reason="provider_backed_group_agenda_stop_passed_kernel_set_gates",
                provider_support_receipt_ref=support_ref,
            )
            self._candidate_state = "NO_AGENDA_CANDIDATE"
            return
        selected_problem_id = str(selection_payload["selected_problem_id"])
        selected_candidate = candidates[selected_problem_id]
        selected_assessment = assessments[selected_problem_id]
        self._agenda_selection = self._agenda.select_candidate(
            f"agenda-{selected_problem_id}",
            support_ref,
        )
        self._deliberation_seed = DeliberationSeed.create(
            seed_id=f"seed-{self.session_id}-{selected_problem_id}",
            source_problem_id=selected_problem_id,
            objective=str(selected_candidate["question"]),
            research_object=str(selected_candidate["research_object"]),
            project_scope=self.project_scope,
            evidence_refs=tuple(selected_candidate["evidence_refs"]),
            rival_explanations=tuple(str(item) for item in selected_candidate["rival_explanations"]),
            operationalization=str(selected_assessment["operationalization"]),
            falsifier=str(selected_candidate["falsifier"]),
            required_harnesses=tuple(str(item) for item in selected_assessment["required_harnesses"]),
            unresolved_conflicts=tuple(selection_payload["unresolved_conflicts"]),
            expected_cbit_gain=float(selection_payload["expected_cbit_gain"]),
            agenda_selection_receipt_ref=support_ref,
        )
        self._candidate_state = "PENDING_AGENDA_REVIEW"

    def _block(
        self,
        stage: str,
        agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        context: CognitiveContextView,
        result: AgentAdapterResult | None,
        provider_audit: dict[str, Any],
        errors: tuple[str, ...],
    ) -> ProblemDefinitionSnapshot:
        receipt = CognitiveExecutionReceipt.create(
            receipt_id=f"problem-execution-{self.session_id}-{len(self._receipts) + 1}",
            session_id=self.session_id,
            work_order_id=work_order.work_order_id,
            agent_id=agent.agent_id,
            role=agent.role,
            stage=stage,
            status="BLOCKED",
            context_hash=context.context_hash,
            work_order_hash=work_order.work_order_hash,
            provider_id=result.provider_id if result else agent.descriptor.provider_id,
            model_id=result.model_id if result else agent.model_id,
            invocation_receipt_ref=result.invocation_receipt_ref if result else "",
            provider_audit=provider_audit,
            provider_invocation_receipt=(result.provider_envelope or {}).get("invocation_receipt", {}) if result else {},
            errors=tuple(dict.fromkeys(errors)),
        )
        self._receipts.append(receipt)
        self._workspaces[agent.agent_id].append(
            agent.agent_id,
            "PROBLEM_EXECUTION_BLOCKED",
            {
                "errors": list(receipt.errors),
                "execution_receipt_hash": receipt.receipt_hash,
                "quarantined_provider_support_receipt": (
                    result.provider_support_receipt
                    if result and isinstance(result.provider_support_receipt, dict)
                    else None
                ),
            },
        )
        self._blocked_stage = stage
        self._stage = "BLOCKED"
        self._persist(
            "PROBLEM_ROLE_BLOCKED",
            {
                "stage": stage,
                "role": agent.role,
                "execution_receipt_hash": receipt.receipt_hash,
                "errors": list(receipt.errors),
            },
        )
        return self.snapshot()

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())


def _contains_authority_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in _AUTHORITY_KEYS for key in value):
            return True
        return any(_contains_authority_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_authority_key(item) for item in value)
    return False


def _is_unit_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and 0.0 <= value <= 1.0
    )


def _nested_evidence_errors(
    values: Any,
    allowed_evidence_refs: tuple[str, ...],
    label: str,
) -> list[str]:
    if not isinstance(values, list) or not values:
        return [f"{label}_evidence_refs_required"]
    return [
        f"problem_candidate_evidence_ref_not_admitted:{ref}"
        if label.startswith("problem_candidate:")
        else f"problem_nested_evidence_ref_not_admitted:{label}:{ref}"
        for ref in values
        if ref not in allowed_evidence_refs
    ]


def _validate_schema(schema: dict[str, Any], payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field_name in schema.get("required", []):
        if field_name not in payload:
            errors.append(f"missing_required_field:{field_name}")
    for field_name, spec in (schema.get("properties") or {}).items():
        if field_name not in payload:
            continue
        value = payload[field_name]
        expected_type = spec.get("type")
        valid_type = {
            "array": isinstance(value, list),
            "object": isinstance(value, dict),
            "string": isinstance(value, str),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "boolean": isinstance(value, bool),
        }.get(expected_type, True)
        if not valid_type:
            errors.append(f"field_type_mismatch:{field_name}:{expected_type}")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"field_enum_mismatch:{field_name}")
    return errors
