"""Provider-backed coordination proposals with Kernel-owned route application."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from agentos_kernel import (
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
)


COGNITIVE_COORDINATION_VERSION = "cognitive_coordination_runtime_v0_2"

ROLE_TO_STAGE = {
    "HYPOTHESIS_GENERATOR": "GENERATION",
    "ADVERSARIAL_REVIEWER": "REVIEW",
    "REPLICATOR": "REPLICATION",
    "SYNTHESIZER": "SYNTHESIS",
}

_ABLATION_OMITTABLE_ROLES = {"ADVERSARIAL_REVIEWER", "REPLICATOR", "SYNTHESIZER"}
_ROLE_MESSAGE_TYPES = {
    "HYPOTHESIS_GENERATOR": "HYPOTHESIS_PROPOSAL",
    "ADVERSARIAL_REVIEWER": "ADVERSARIAL_REVIEW",
    "REPLICATOR": "REPLICATION_REPORT",
    "SYNTHESIZER": "BOUNDED_SYNTHESIS",
}

_PASS_PROVIDER_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}

_FORBIDDEN_COORDINATOR_KEYS = {
    "accepted",
    "asset_promotion_authorized",
    "chain_of_thought",
    "execution_authorized",
    "final_candidate_state",
    "hidden_reasoning",
    "permission_granted",
    "private_memory",
    "private_note",
    "published",
    "scratchpad",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


def _message_ref(message: CognitiveMessage) -> str:
    return f"message://{message.message_id}/{message.message_hash}"


@dataclass(frozen=True)
class CoordinationProposal:
    proposal_id: str
    session_id: str
    coordinator_agent_id: str
    route_action: str
    target_role: str
    rationale: str
    unresolved_questions: tuple[Any, ...]
    evidence_gaps: tuple[Any, ...]
    conflict_message_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    expected_cbit_gain: float
    stop_condition: str
    created_at: str = field(default_factory=_utc_now)
    proposal_hash: str = ""

    @classmethod
    def create(
        cls,
        *,
        proposal_id: str,
        session_id: str,
        coordinator_agent_id: str,
        payload: dict[str, Any],
    ) -> "CoordinationProposal":
        created_at = _utc_now()
        values = {
            "proposal_id": proposal_id,
            "session_id": session_id,
            "coordinator_agent_id": coordinator_agent_id,
            "route_action": payload["route_action"],
            "target_role": payload["target_role"],
            "rationale": payload["rationale"],
            "unresolved_questions": tuple(payload["unresolved_questions"]),
            "evidence_gaps": tuple(payload["evidence_gaps"]),
            "conflict_message_refs": tuple(payload["conflict_message_refs"]),
            "evidence_refs": tuple(payload["evidence_refs"]),
            "expected_cbit_gain": float(payload["expected_cbit_gain"]),
            "stop_condition": payload["stop_condition"],
            "created_at": created_at,
        }
        return cls(**values, proposal_hash=_hash_payload(values))

    def as_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "session_id": self.session_id,
            "coordinator_agent_id": self.coordinator_agent_id,
            "route_action": self.route_action,
            "target_role": self.target_role,
            "rationale": self.rationale,
            "unresolved_questions": list(self.unresolved_questions),
            "evidence_gaps": list(self.evidence_gaps),
            "conflict_message_refs": list(self.conflict_message_refs),
            "evidence_refs": list(self.evidence_refs),
            "expected_cbit_gain": self.expected_cbit_gain,
            "stop_condition": self.stop_condition,
            "created_at": self.created_at,
            "proposal_hash": self.proposal_hash,
        }


@dataclass(frozen=True)
class KernelCoordinationDecision:
    status: str
    current_stage: str
    next_stage: str
    proposal: CoordinationProposal | None
    receipt: CognitiveExecutionReceipt
    errors: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "current_stage": self.current_stage,
            "next_stage": self.next_stage,
            "proposal": self.proposal.as_dict() if self.proposal else None,
            "receipt": self.receipt.as_dict(),
            "errors": list(self.errors),
        }


class CognitiveCoordinationRuntime:
    """Obtain semantic route advice, then apply deterministic Kernel constraints."""

    module_id = COGNITIVE_COORDINATION_VERSION
    capabilities = ("provider_backed_coordination", "kernel_gated_dynamic_routing")

    def __init__(
        self,
        *,
        coordinator: CognitiveAgent,
        adapter: Any,
        workspace_root: str | Path,
        max_cycles: int = 8,
        max_role_executions_per_role: int = 2,
        authorized_omitted_roles: tuple[str, ...] = (),
        ablation_authorization_ref: str = "",
    ) -> None:
        if coordinator.role != "COORDINATOR":
            raise ValueError("cognitive_coordination_requires_coordinator_role")
        if max_cycles < 1 or max_role_executions_per_role < 1:
            raise ValueError("coordination_budgets_must_be_positive")
        omitted = tuple(authorized_omitted_roles)
        if len(omitted) > 1 or not set(omitted).issubset(_ABLATION_OMITTABLE_ROLES):
            raise ValueError("coordination_ablation_omitted_roles_invalid")
        if omitted and not ablation_authorization_ref.startswith("kernel://"):
            raise ValueError("coordination_role_omission_not_authorized")
        if not omitted and ablation_authorization_ref:
            raise ValueError("coordination_ablation_authorization_without_omission")
        self.coordinator = coordinator
        self.adapter = adapter
        self.max_cycles = max_cycles
        self.max_role_executions_per_role = max_role_executions_per_role
        self.authorized_omitted_roles = omitted
        self.ablation_authorization_ref = ablation_authorization_ref
        self._cycle_count = 0
        self._workspace = PrivateAgentWorkspace(
            workspace_root,
            coordinator.agent_id,
            coordinator.private_memory_namespace,
        )
        self._cognition_layer = ProviderBackedRuntimeCognitionLayer()
        self._proposals: list[CoordinationProposal] = []
        self._receipts: list[CognitiveExecutionReceipt] = []

    @property
    def proposals(self) -> tuple[CoordinationProposal, ...]:
        return tuple(self._proposals)

    @property
    def receipts(self) -> tuple[CognitiveExecutionReceipt, ...]:
        return tuple(self._receipts)

    def coordinate(
        self,
        *,
        session_id: str,
        objective: str,
        project_scope: str,
        frozen_gate_refs: tuple[str, ...],
        evidence_refs: tuple[str, ...],
        evidence_payload: dict[str, Any],
        messages: tuple[CognitiveMessage, ...],
        role_execution_counts: dict[str, int],
        current_stage: str,
        kernel_authorization_ref: str,
    ) -> KernelCoordinationDecision:
        if project_scope not in self.coordinator.descriptor.allowed_evidence_scopes:
            raise ValueError("coordinator_project_scope_not_allowed")
        message_refs = tuple(_message_ref(message) for message in messages)
        allowed_evidence = tuple(dict.fromkeys((*evidence_refs, *frozen_gate_refs, *message_refs)))
        progression_candidates = self._minimal_progression_candidates(messages, role_execution_counts)
        allowed_route_actions = list(
            dict.fromkeys(
                [item["route_action"] for item in progression_candidates]
                + ["REQUEST_EVIDENCE", "STOP_BLOCKED"]
                + (
                    ["RUN_ROLE"]
                    if self._reexecution_targets(messages, role_execution_counts)
                    else []
                )
            )
        )
        allowed_targets = list(
            dict.fromkeys(
                [item["target_role"] for item in progression_candidates]
                + self._reexecution_targets(messages, role_execution_counts)
                + ["NONE"]
            )
        )
        context = CognitiveContextView(
            session_id=session_id,
            objective=objective,
            project_scope=project_scope,
            role=self.coordinator.role,
            context_isolation_key=self.coordinator.descriptor.context_isolation_key,
            private_workspace_descriptor=self._workspace.public_descriptor(),
            frozen_gate_refs=frozen_gate_refs,
            evidence_refs=evidence_refs,
            evidence_payload=dict(evidence_payload),
            input_messages=messages,
            excluded_message_refs=(),
            coordination_state={
                "current_stage": current_stage,
                "available_roles": [role for role in ROLE_TO_STAGE if role not in self.authorized_omitted_roles],
                "authorized_omitted_roles": list(self.authorized_omitted_roles),
                "ablation_authorization_ref": self.ablation_authorization_ref,
                "role_execution_counts": dict(role_execution_counts),
                "max_role_executions_per_role": self.max_role_executions_per_role,
                "completed_message_types": [message.message_type for message in messages],
                "prior_coordination_proposals": [proposal.as_dict() for proposal in self._proposals],
                "prior_coordination_receipts": [
                    {
                        "status": receipt.status,
                        "message_ref": receipt.message_ref,
                        "errors": list(receipt.errors),
                    }
                    for receipt in self._receipts
                ],
                "kernel_minimal_progression_candidates": progression_candidates,
                "admissible_progression_candidates": progression_candidates,
                "allowed_route_actions": allowed_route_actions,
                "kernel_final_state_owner": True,
                "kernel_route_policy": (
                    "negative findings still proceed to bounded synthesis; rerunning a completed role requires a "
                    "public conflict_message_ref; FINALIZE_CANDIDATE asks the Kernel to form a pending candidate and "
                    "does not give the coordinator final-state authority; when it is the sole admissible progression, "
                    "select it; a coordinator proposal never creates accepted or published state"
                ),
            },
        )
        output_schema = self.coordinator.contract.expected_schema()
        output_properties = output_schema["properties"]
        output_properties["rationale"]["minLength"] = 1
        output_properties["stop_condition"]["minLength"] = 1
        output_properties["evidence_refs"].update(
            {
                "minItems": 1,
                "items": {"type": "string", "enum": list(allowed_evidence)},
            }
        )
        output_properties["conflict_message_refs"]["items"] = {
            "type": "string",
            "enum": list(message_refs),
        }
        output_properties["expected_cbit_gain"].update({"minimum": 0, "maximum": 1})
        output_properties["route_action"]["enum"] = allowed_route_actions
        output_properties["target_role"]["enum"] = allowed_targets
        work_order = CognitiveWorkOrder(
            work_order_id=f"{session_id}-coordination-{self._cycle_count + 1}",
            session_id=session_id,
            agent_id=self.coordinator.agent_id,
            role=self.coordinator.role,
            stage="COORDINATION",
            objective=self.coordinator.contract.purpose,
            role_contract_id=self.coordinator.contract.contract_id,
            input_message_refs=message_refs,
            allowed_evidence_refs=allowed_evidence,
            output_schema=output_schema,
            kernel_authorization_ref=kernel_authorization_ref,
        )
        if self._cycle_count >= self.max_cycles:
            receipt = self._make_receipt(
                session_id,
                work_order,
                context,
                status="BLOCKED",
                result=None,
                provider_audit={},
                errors=("coordination_cycle_budget_exhausted",),
            )
            self._receipts.append(receipt)
            return KernelCoordinationDecision(
                "BLOCKED",
                current_stage,
                "",
                None,
                receipt,
                ("coordination_cycle_budget_exhausted",),
            )

        self._cycle_count += 1
        self._workspace.append(
            self.coordinator.agent_id,
            "COORDINATION_WORK_ORDER_RECEIVED",
            {"work_order": work_order.as_dict()},
        )
        try:
            result = self.adapter.invoke(self.coordinator, work_order, context, self._workspace)
        except Exception as exc:
            errors = (f"coordinator_adapter_error:{type(exc).__name__}:{exc}",)
            receipt = self._make_receipt(
                session_id,
                work_order,
                context,
                status="BLOCKED",
                result=None,
                provider_audit={},
                errors=errors,
            )
            self._receipts.append(receipt)
            return KernelCoordinationDecision("BLOCKED", current_stage, "", None, receipt, errors)

        errors, provider_audit = self._validate_result(work_order, result, message_refs)
        proposal = None
        if not errors:
            proposal = CoordinationProposal.create(
                proposal_id=f"{session_id}-coordination-proposal-{self._cycle_count}",
                session_id=session_id,
                coordinator_agent_id=self.coordinator.agent_id,
                payload=result.provider_support_receipt or {},
            )
            errors.extend(self._validate_kernel_route(proposal, current_stage, messages, role_execution_counts))

        receipt = self._make_receipt(
            session_id,
            work_order,
            context,
            status="COMPLETED" if not self._provider_execution_errors(result) else "BLOCKED",
            result=result,
            provider_audit=provider_audit,
            errors=tuple(errors),
            proposal=proposal,
        )
        self._receipts.append(receipt)
        if proposal is not None:
            self._proposals.append(proposal)
        self._workspace.append(
            self.coordinator.agent_id,
            "COORDINATION_DECISION_RECORDED",
            {
                "proposal_hash": proposal.proposal_hash if proposal else "",
                "receipt_hash": receipt.receipt_hash,
                "kernel_route_applied": not errors,
                "errors": errors,
            },
        )
        if errors:
            return KernelCoordinationDecision(
                "BLOCKED",
                current_stage,
                "",
                proposal,
                receipt,
                tuple(dict.fromkeys(errors)),
            )
        return KernelCoordinationDecision(
            "APPLIED",
            current_stage,
            self._next_stage(proposal),
            proposal,
            receipt,
        )

    def _validate_result(
        self,
        work_order: CognitiveWorkOrder,
        result: AgentAdapterResult,
        message_refs: tuple[str, ...],
    ) -> tuple[list[str], dict[str, Any]]:
        errors = self._provider_execution_errors(result)
        payload = result.provider_support_receipt
        if not isinstance(payload, dict):
            errors.append("provider_support_receipt_required")
            return list(dict.fromkeys(errors)), {}
        errors.extend(_validate_schema(work_order.output_schema, payload))
        if isinstance(payload.get("expected_cbit_gain"), (int, float)) and not isinstance(
            payload.get("expected_cbit_gain"), bool
        ) and not math.isfinite(payload["expected_cbit_gain"]):
            errors.append("coordinator_expected_cbit_must_be_finite")
        if not str(payload.get("rationale", "")).strip():
            errors.append("coordinator_rationale_required")
        if not str(payload.get("stop_condition", "")).strip():
            errors.append("coordinator_stop_condition_required")
        if not payload.get("evidence_refs"):
            errors.append("coordinator_evidence_refs_required")
        if _contains_forbidden_key(payload):
            errors.append("coordinator_final_state_authority_forbidden")
        provider_evidence = payload.get("evidence_refs")
        if isinstance(provider_evidence, list) and any(
            ref not in work_order.allowed_evidence_refs for ref in provider_evidence
        ):
            errors.append("coordinator_evidence_ref_not_admitted")
        conflict_refs = payload.get("conflict_message_refs")
        if isinstance(conflict_refs, list) and any(ref not in message_refs for ref in conflict_refs):
            errors.append("coordinator_conflict_message_ref_not_public")
        provider_audit = self._cognition_layer.audit_operation(
            self.coordinator.contract.provider_operation_id,
            {"provider_support_receipt": payload},
        )
        if provider_audit["status"] not in _PASS_PROVIDER_AUDITS:
            errors.append(f"provider_support_audit:{provider_audit['status']}")
        return list(dict.fromkeys(errors)), provider_audit

    def _provider_execution_errors(self, result: AgentAdapterResult) -> list[str]:
        errors = list(result.validation_errors)
        if result.status != "COMPLETED":
            errors.append(f"coordinator_adapter_status:{result.status}")
        if result.status == "COMPLETED" and (
            result.provider_id != self.coordinator.descriptor.provider_id
            or result.model_id != self.coordinator.model_id
        ):
            errors.append("coordinator_provider_binding_mismatch")
        if not result.invocation_receipt_ref:
            errors.append("provider_invocation_receipt_ref_required")
        return list(dict.fromkeys(errors))

    def _validate_kernel_route(
        self,
        proposal: CoordinationProposal,
        current_stage: str,
        messages: tuple[CognitiveMessage, ...],
        role_execution_counts: dict[str, int],
    ) -> list[str]:
        errors: list[str] = []
        message_types = {message.message_type for message in messages}
        action = proposal.route_action
        target = proposal.target_role
        minimal_actions = {
            (item["route_action"], item["target_role"])
            for item in self._minimal_progression_candidates(messages, role_execution_counts)
        }
        if target in self.authorized_omitted_roles:
            errors.append(f"coordination_target_role_omitted:{target}")
            return errors
        if action == "RUN_ROLE":
            if target not in ROLE_TO_STAGE or target == "SYNTHESIZER":
                errors.append("coordination_run_role_target_invalid")
            if current_stage == "INTAKE" and target != "HYPOTHESIS_GENERATOR":
                errors.append("coordination_intake_requires_hypothesis_generator")
            if target in {"ADVERSARIAL_REVIEWER", "REPLICATOR"} and "HYPOTHESIS_PROPOSAL" not in message_types:
                errors.append("coordination_role_prerequisite_missing:HYPOTHESIS_PROPOSAL")
            if proposal.expected_cbit_gain <= 0 and (action, target) not in minimal_actions:
                errors.append("coordination_positive_cbit_required_for_role_execution")
            target_message_type = {
                "HYPOTHESIS_GENERATOR": "HYPOTHESIS_PROPOSAL",
                "ADVERSARIAL_REVIEWER": "ADVERSARIAL_REVIEW",
                "REPLICATOR": "REPLICATION_REPORT",
            }.get(target, "")
            if target_message_type in message_types and not proposal.conflict_message_refs:
                errors.append("coordination_reexecution_requires_public_conflict_ref")
            errors.extend(self._role_budget_errors(target, role_execution_counts))
        elif action == "PROCEED_TO_SYNTHESIS":
            if target != "SYNTHESIZER":
                errors.append("coordination_synthesis_target_invalid")
            required = {
                message_type
                for role, message_type in _ROLE_MESSAGE_TYPES.items()
                if role not in {*self.authorized_omitted_roles, "SYNTHESIZER"}
            }
            if not required.issubset(message_types):
                errors.append("coordination_synthesis_prerequisites_missing")
            if proposal.expected_cbit_gain <= 0 and (action, target) not in minimal_actions:
                errors.append("coordination_positive_cbit_required_for_role_execution")
            errors.extend(self._role_budget_errors("SYNTHESIZER", role_execution_counts))
        elif action == "FINALIZE_CANDIDATE":
            if target != "NONE":
                errors.append("coordination_finalize_target_must_be_none")
            if "SYNTHESIZER" in self.authorized_omitted_roles:
                required = {
                    message_type
                    for role, message_type in _ROLE_MESSAGE_TYPES.items()
                    if role not in self.authorized_omitted_roles
                }
                if not required.issubset(message_types):
                    errors.append("coordination_finalize_unsynthesized_prerequisites_missing")
            elif current_stage != "SYNTHESIS" or "BOUNDED_SYNTHESIS" not in message_types:
                errors.append("coordination_finalize_requires_bounded_synthesis")
        elif action == "REQUEST_EVIDENCE":
            if target != "NONE":
                errors.append("coordination_request_evidence_target_must_be_none")
            errors.append("coordination_additional_evidence_requested")
        elif action == "STOP_BLOCKED":
            if target != "NONE":
                errors.append("coordination_stop_target_must_be_none")
            errors.append("coordination_stop_proposed")
        return list(dict.fromkeys(errors))

    def _role_budget_errors(self, target: str, role_execution_counts: dict[str, int]) -> list[str]:
        if target in ROLE_TO_STAGE and role_execution_counts.get(target, 0) >= self.max_role_executions_per_role:
            return [f"coordination_role_execution_budget_exhausted:{target}"]
        return []

    def _minimal_progression_candidates(
        self,
        messages: tuple[CognitiveMessage, ...],
        role_execution_counts: dict[str, int],
    ) -> list[dict[str, str]]:
        message_types = {message.message_type for message in messages}
        candidates: list[dict[str, str]] = []
        if "HYPOTHESIS_PROPOSAL" not in message_types:
            candidates.append({"route_action": "RUN_ROLE", "target_role": "HYPOTHESIS_GENERATOR"})
            return candidates
        missing_roles = (
            ("ADVERSARIAL_REVIEW", "ADVERSARIAL_REVIEWER"),
            ("REPLICATION_REPORT", "REPLICATOR"),
        )
        for message_type, role in missing_roles:
            if (
                role not in self.authorized_omitted_roles
                and
                message_type not in message_types
                and role_execution_counts.get(role, 0) < self.max_role_executions_per_role
            ):
                candidates.append({"route_action": "RUN_ROLE", "target_role": role})
        if candidates:
            return candidates
        if "SYNTHESIZER" in self.authorized_omitted_roles:
            return [{"route_action": "FINALIZE_CANDIDATE", "target_role": "NONE"}]
        if "BOUNDED_SYNTHESIS" not in message_types:
            return [{"route_action": "PROCEED_TO_SYNTHESIS", "target_role": "SYNTHESIZER"}]
        return [{"route_action": "FINALIZE_CANDIDATE", "target_role": "NONE"}]

    def _reexecution_targets(
        self,
        messages: tuple[CognitiveMessage, ...],
        role_execution_counts: dict[str, int],
    ) -> list[str]:
        message_types = {message.message_type for message in messages}
        targets = []
        for role, message_type in _ROLE_MESSAGE_TYPES.items():
            if role == "SYNTHESIZER" or role in self.authorized_omitted_roles:
                continue
            if (
                message_type in message_types
                and role_execution_counts.get(role, 0) < self.max_role_executions_per_role
            ):
                targets.append(role)
        return targets

    @staticmethod
    def _next_stage(proposal: CoordinationProposal) -> str:
        if proposal.route_action == "RUN_ROLE":
            return ROLE_TO_STAGE[proposal.target_role]
        if proposal.route_action == "PROCEED_TO_SYNTHESIS":
            return "SYNTHESIS"
        if proposal.route_action == "FINALIZE_CANDIDATE":
            return "CANDIDATE"
        return ""

    def _make_receipt(
        self,
        session_id: str,
        work_order: CognitiveWorkOrder,
        context: CognitiveContextView,
        *,
        status: str,
        result: AgentAdapterResult | None,
        provider_audit: dict[str, Any],
        errors: tuple[str, ...],
        proposal: CoordinationProposal | None = None,
    ) -> CognitiveExecutionReceipt:
        return CognitiveExecutionReceipt.create(
            receipt_id=f"coordination-execution-{session_id}-{len(self._receipts) + 1}",
            session_id=session_id,
            work_order_id=work_order.work_order_id,
            agent_id=self.coordinator.agent_id,
            role=self.coordinator.role,
            stage="COORDINATION",
            status=status,
            context_hash=context.context_hash,
            work_order_hash=work_order.work_order_hash,
            provider_id=result.provider_id if result else self.coordinator.descriptor.provider_id,
            model_id=result.model_id if result else self.coordinator.model_id,
            invocation_receipt_ref=result.invocation_receipt_ref if result else "",
            provider_audit=provider_audit,
            provider_invocation_receipt=(result.provider_envelope or {}).get("invocation_receipt", {}) if result else {},
            message_ref=(
                f"coordination://{proposal.proposal_id}/{proposal.proposal_hash}"
                if proposal
                else ""
            ),
            errors=errors,
        )


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, dict):
        if any(str(key).lower() in _FORBIDDEN_COORDINATOR_KEYS for key in value):
            return True
        return any(_contains_forbidden_key(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return False


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
