"""Provider-backed semantic proposals for bounded organization evolution."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderBackedRuntimeCognitionLayer, ProviderCognitiveTask, ProviderTaskRouter
from agentos_kernel.organization_capability_models import AgentCapabilityEvidence, OrganizationCapabilityPolicy
from agentos_kernel.organization_evolution_eval import OrganizationOperatorCredit
from agentos_kernel.organization_evolution_models import (
    OrganizationEvolutionBudget,
    OrganizationEvolutionTask,
    OrganizationGenome,
    OrganizationMutationProposal,
    organization_hash,
)
from agentos_kernel.provider_cognition_layer import (
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
)
from agentos_kernel.provider_execution_plane import STATUS_COMPLETED

from .organization_evolution_operators import OrganizationEvolutionOperatorRegistry


_PASS_AUDITS = {
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
}


class OrganizationEvolutionProviderAdvisor:
    """Propose mutations without selection, execution, or retention authority."""

    def __init__(
        self,
        *,
        runtime_id: str,
        provider_router: ProviderTaskRouter,
        operator_registry: OrganizationEvolutionOperatorRegistry,
        event_sink: Callable[[str, dict[str, Any]], None],
        capability_evidence: tuple[AgentCapabilityEvidence, ...] = (),
        capability_policy: OrganizationCapabilityPolicy | None = None,
    ) -> None:
        self.runtime_id = runtime_id
        self.provider_router = provider_router
        self.operator_registry = operator_registry
        self.event_sink = event_sink
        self.capability_evidence = capability_evidence
        self.capability_policy = capability_policy
        self._cognition = ProviderBackedRuntimeCognitionLayer()

    def propose(
        self,
        *,
        generation_id: str,
        task: OrganizationEvolutionTask,
        incumbent: OrganizationGenome,
        budget: OrganizationEvolutionBudget,
        operator_ids: tuple[str, ...],
        credits: tuple[OrganizationOperatorCredit, ...],
        max_candidates: int,
    ) -> tuple[OrganizationMutationProposal, ...]:
        provider_task = ProviderCognitiveTask(
            task_id=f"{generation_id}-organization-evolution",
            task_kind="organization_evolution_proposal",
            objective=(
                "Propose bounded organization mutations for the frozen task and incumbent. Use only supplied "
                "operators, role contracts, and evidence references. Prefer mutations supported by task structure "
                "and operator credit, while preserving diversity. Do not select a winner, claim execution authority, "
                "or predict hidden Harness outcomes."
            ),
            inputs={
                "task": task.as_dict(),
                "incumbent_genome": incumbent.as_dict(),
                "allowed_operators": self.operator_registry.operator_surface(operator_ids),
                "role_contract_catalog": {
                    role_id: list(contracts)
                    for role_id, contracts in self.operator_registry.role_contract_catalog.items()
                },
                "operator_credit": [item.as_dict() for item in credits],
                "hard_budget": budget.as_dict(),
                "max_candidates": max_candidates,
                **self._capability_inputs(task),
            },
            allowed_evidence=list(task.evidence_refs),
            expected_schema=self.provider_schema(),
            budget={"max_candidates": max_candidates},
            failure_semantics="block_generation_without_provider_supported_mutation_proposals",
        )
        envelope = self.provider_router.route(provider_task)
        if envelope.status != STATUS_COMPLETED or not envelope.semantic_result_present:
            self.event_sink(
                "ORGANIZATION_EVOLUTION_PROVIDER_BLOCKED",
                {
                    "generation_id": generation_id,
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise RuntimeError(f"organization_evolution_provider_blocked:{envelope.status}")
        payload = dict(envelope.normalized_result or {})
        audit = self._cognition.audit_operation(
            "organization_evolution_proposal",
            {
                "provider_support_receipt": payload,
                "provider_support_receipt_hash": organization_hash(payload),
            },
        )
        errors = self._payload_errors(payload, task, operator_ids, max_candidates)
        if audit.get("status") not in _PASS_AUDITS:
            errors.append(f"organization_evolution_provider_audit_failed:{audit.get('status')}")
        if errors:
            self.event_sink(
                "ORGANIZATION_EVOLUTION_PROVIDER_BLOCKED",
                {
                    "generation_id": generation_id,
                    "errors": errors,
                    "provider_audit": audit,
                    "invocation_receipt": envelope.invocation_receipt.as_dict(),
                },
            )
            raise ValueError(";".join(errors))
        invocation = envelope.invocation_receipt.as_dict()
        return tuple(
            OrganizationMutationProposal.create(
                proposal_id=item["proposal_id"],
                parent_genome_hash=incumbent.genome_hash,
                operator_id=item["operator_id"],
                parameters=dict(item["parameters"]),
                rationale=item["rationale"],
                evidence_refs=tuple(item["evidence_refs"]),
                provider_invocation_receipt=invocation,
            )
            for item in payload["proposals"]
        )

    def _capability_inputs(self, task: OrganizationEvolutionTask) -> dict[str, Any]:
        registry = self.operator_registry.agent_registry
        if registry is None:
            return {}
        allowed_evidence = set(task.evidence_refs)
        return {
            "agent_registry": [
                {
                    "agent_id": item.agent_id,
                    "role": item.role,
                    "capabilities": list(item.capabilities),
                    "runner_id": item.runner_id,
                    "harness_id": item.harness_id,
                    "provider_id": item.provider_id,
                    "model_id": item.model_id,
                    "context_isolation_key": item.context_isolation_key,
                    "allowed_evidence_scopes": list(item.allowed_evidence_scopes),
                    "enabled": item.enabled,
                }
                for item in registry.registered_agents()
                if task.project_scope in item.allowed_evidence_scopes or "*" in item.allowed_evidence_scopes
            ],
            "role_contract_capabilities": {
                key: list(value) for key, value in self.operator_registry.role_contract_capabilities.items()
            },
            "capability_evidence": [
                item.as_dict() for item in self.capability_evidence
                if item.project_scope == task.project_scope
                and set(item.evidence_refs).issubset(allowed_evidence)
            ],
            "capability_policy": self.capability_policy.as_dict() if self.capability_policy else {},
        }

    @staticmethod
    def _payload_errors(
        payload: dict[str, Any],
        task: OrganizationEvolutionTask,
        operator_ids: tuple[str, ...],
        max_candidates: int,
    ) -> list[str]:
        errors: list[str] = []
        proposals = payload.get("proposals")
        if not isinstance(proposals, list) or not proposals or len(proposals) > max_candidates:
            return ["organization_evolution_provider_proposal_count_invalid"]
        seen_ids: set[str] = set()
        allowed_evidence = set(task.evidence_refs)
        allowed_operators = set(operator_ids)
        authority_keys = {"accepted", "authorized", "winner", "final_state", "production_activation"}
        for item in proposals:
            if not isinstance(item, dict):
                errors.append("organization_evolution_provider_proposal_invalid")
                continue
            proposal_id = item.get("proposal_id")
            if not isinstance(proposal_id, str) or not proposal_id or proposal_id in seen_ids:
                errors.append("organization_evolution_provider_proposal_id_invalid")
            else:
                seen_ids.add(proposal_id)
            if item.get("operator_id") not in allowed_operators:
                errors.append("organization_evolution_provider_operator_forbidden")
            if not isinstance(item.get("parameters"), dict) or not item["parameters"]:
                errors.append("organization_evolution_provider_parameters_invalid")
            if not isinstance(item.get("rationale"), str) or not item["rationale"].strip():
                errors.append("organization_evolution_provider_rationale_invalid")
            refs = item.get("evidence_refs")
            if (
                not isinstance(refs, list)
                or not refs
                or len(refs) != len(set(refs))
                or not set(refs).issubset(allowed_evidence)
            ):
                errors.append("organization_evolution_provider_evidence_invalid")
            if authority_keys.intersection(item):
                errors.append("organization_evolution_provider_authority_forbidden")
        refs = payload.get("evidence_refs")
        if not isinstance(refs, list) or not refs or not set(refs).issubset(allowed_evidence):
            errors.append("organization_evolution_provider_global_evidence_invalid")
        uncertainty = payload.get("uncertainty")
        if (
            not isinstance(uncertainty, (int, float))
            or isinstance(uncertainty, bool)
            or not 0.0 <= float(uncertainty) <= 1.0
        ):
            errors.append("organization_evolution_provider_uncertainty_invalid")
        if not isinstance(payload.get("global_rationale"), str) or not payload["global_rationale"].strip():
            errors.append("organization_evolution_provider_global_rationale_invalid")
        return list(dict.fromkeys(errors))

    @staticmethod
    def provider_schema() -> dict[str, Any]:
        return {
            "type": "object",
            "required": ["proposals", "global_rationale", "uncertainty", "evidence_refs"],
            "properties": {
                "proposals": {"type": "array", "items": {"type": "object"}},
                "global_rationale": {"type": "string"},
                "uncertainty": {"type": "number"},
                "evidence_refs": {"type": "array", "items": {"type": "string"}},
            },
        }
