"""Adapters that bind independent cognitive agents to ProviderTaskRouter."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_roles import CognitiveAgent, PrivateAgentWorkspace
from .deliberation import (
    AgentAdapterResult,
    CognitiveContextView,
    CognitiveWorkOrder,
)


PROVIDER_COGNITIVE_AGENT_ADAPTER_VERSION = "provider_cognitive_agent_adapter_v0_1"


class ProviderCognitiveAgentAdapter:
    """Translate one formal role work order into a bounded provider task."""

    def __init__(
        self,
        adapter_id: str,
        router: ProviderTaskRouter,
        *,
        timeout_seconds: int = 120,
    ) -> None:
        if not adapter_id:
            raise ValueError("cognitive_agent_adapter_id_required")
        self.adapter_id = adapter_id
        self.router = router
        self.timeout_seconds = timeout_seconds

    def invoke(
        self,
        cognitive_agent: CognitiveAgent,
        work_order: CognitiveWorkOrder,
        context_view: CognitiveContextView,
        private_workspace: PrivateAgentWorkspace,
    ) -> AgentAdapterResult:
        if work_order.agent_id != cognitive_agent.agent_id or context_view.role != cognitive_agent.role:
            raise ValueError("cognitive_agent_work_order_binding_mismatch")
        task = ProviderCognitiveTask(
            task_id=work_order.work_order_id,
            task_kind=cognitive_agent.contract.provider_operation_id,
            objective=work_order.objective,
            inputs={
                "context": context_view.as_dict(),
                "formal_work_order": work_order.as_dict(),
            },
            allowed_evidence=list(work_order.allowed_evidence_refs),
            expected_schema=work_order.output_schema,
            timeout_seconds=self.timeout_seconds,
            freshness_requirement="session_frozen_gate_and_evidence_coordinate",
            failure_semantics="block_role_stage_without_local_semantic_substitution",
        )
        envelope = self.router.route(task)
        envelope_payload = envelope.as_dict()
        invocation_receipt = envelope_payload["invocation_receipt"]
        invocation_ref = f"provider-invocation://{invocation_receipt['receipt_hash']}"
        private_workspace.append(
            cognitive_agent.agent_id,
            "PROVIDER_INVOCATION_RECORDED",
            {
                "task_id": task.task_id,
                "task_contract_hash": task.contract_hash(),
                "invocation_receipt_ref": invocation_ref,
                "status": envelope.status,
            },
        )
        selected_provider = envelope.invocation_receipt.provider_id
        selected_model = envelope.invocation_receipt.model_id
        binding_matches = (
            selected_provider == cognitive_agent.descriptor.provider_id
            and selected_model == cognitive_agent.model_id
        )
        if envelope.semantic_result_present and not binding_matches:
            return AgentAdapterResult(
                status="BINDING_MISMATCH",
                provider_support_receipt=envelope.normalized_result,
                provider_id=selected_provider,
                model_id=selected_model,
                invocation_receipt_ref=invocation_ref,
                validation_errors=("agent_provider_binding_mismatch",),
                provider_envelope=envelope_payload,
            )
        return AgentAdapterResult(
            status=envelope.status,
            provider_support_receipt=envelope.normalized_result,
            provider_id=selected_provider,
            model_id=selected_model,
            invocation_receipt_ref=invocation_ref,
            validation_errors=envelope.validation_errors,
            provider_envelope=envelope_payload,
        )
