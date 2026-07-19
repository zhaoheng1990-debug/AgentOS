import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    AgentDescriptor,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
)
from agentos_runtime import (
    CognitiveAgent,
    CognitiveContextView,
    CognitiveMessage,
    CognitiveWorkOrder,
    PrivateAgentWorkspace,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)


class CapturingProviderAdapter:
    def __init__(self, provider_id, model_id, task_kind, result):
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=(task_kind,),
            max_timeout_seconds=120,
        )
        self.result = result
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.result,
            "usage": {"total_tokens": 100},
            "provenance_refs": task.allowed_evidence,
        }


def generator_agent(provider_id="provider-a", model_id="model-a"):
    descriptor = AgentDescriptor(
        "generator",
        "HYPOTHESIS_GENERATOR",
        ("semantic_judgment", "source_read"),
        "codex",
        "harness-a",
        provider_id,
        "context-generator",
        ("project://fixture",),
    )
    return CognitiveAgent(
        descriptor,
        standard_role_contract("HYPOTHESIS_GENERATOR"),
        model_id,
        "memory-generator",
        ("source_read", "hypothesis_write"),
        "credit-generator",
    )


def generator_payload():
    return {
        "hypotheses": ["claim-a"],
        "assumptions": ["assumption-a"],
        "rival_explanations": ["rival-a"],
        "falsifiable_predictions": ["prediction-a"],
        "evidence_refs": ["evidence://source"],
        "confidence": 0.7,
    }


def work_order(agent):
    return CognitiveWorkOrder(
        work_order_id="work-order-1",
        session_id="session-1",
        agent_id=agent.agent_id,
        role=agent.role,
        stage="GENERATION",
        objective=agent.contract.purpose,
        role_contract_id=agent.contract.contract_id,
        input_message_refs=(),
        allowed_evidence_refs=("evidence://source", "gate://fixture"),
        output_schema=agent.contract.expected_schema(),
        kernel_authorization_ref="kernel://authorization",
    )


def context(agent, workspace):
    return CognitiveContextView(
        session_id="session-1",
        objective="Find the narrowest claim.",
        project_scope="project://fixture",
        role=agent.role,
        context_isolation_key=agent.descriptor.context_isolation_key,
        private_workspace_descriptor=workspace.public_descriptor(),
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        evidence_payload={"frozen_summary": "public evidence only"},
        input_messages=(),
        excluded_message_refs=(),
    )


def test_provider_adapter_exposes_formal_context_but_not_private_workspace_history(tmp_path):
    agent = generator_agent()
    workspace = PrivateAgentWorkspace(tmp_path, agent.agent_id, agent.private_memory_namespace)
    workspace.append(agent.agent_id, "PRIVATE_NOTE", {"note": "do not expose this"})
    provider = CapturingProviderAdapter(
        "provider-a",
        "model-a",
        agent.contract.provider_operation_id,
        generator_payload(),
    )
    adapter = ProviderCognitiveAgentAdapter("runtime-provider-a", ProviderTaskRouter([provider]))

    result = adapter.invoke(agent, work_order(agent), context(agent, workspace), workspace)

    assert result.status == "COMPLETED"
    assert result.provider_support_receipt == generator_payload()
    assert result.provider_id == "provider-a"
    assert result.model_id == "model-a"
    assert result.provider_envelope["invocation_receipt"]["receipt_hash"]
    sent_inputs = provider.tasks[0].inputs
    assert sent_inputs["context"]["private_workspace_descriptor"]["namespace"] == "memory-generator"
    assert "do not expose this" not in str(sent_inputs)
    assert [item["event_type"] for item in workspace.history(agent.agent_id)] == [
        "PRIVATE_NOTE",
        "PROVIDER_INVOCATION_RECORDED",
    ]


def test_provider_adapter_blocks_fallback_that_changes_agent_provider_identity(tmp_path):
    agent = generator_agent(provider_id="provider-a", model_id="model-a")
    workspace = PrivateAgentWorkspace(tmp_path, agent.agent_id, agent.private_memory_namespace)
    fallback = CapturingProviderAdapter(
        "provider-b",
        "model-b",
        agent.contract.provider_operation_id,
        generator_payload(),
    )
    adapter = ProviderCognitiveAgentAdapter("runtime-fallback", ProviderTaskRouter([fallback]))

    result = adapter.invoke(agent, work_order(agent), context(agent, workspace), workspace)

    assert result.status == "BINDING_MISMATCH"
    assert result.provider_id == "provider-b"
    assert result.model_id == "model-b"
    assert result.validation_errors == ("agent_provider_binding_mismatch",)


def test_context_view_contains_only_formal_messages(tmp_path):
    agent = generator_agent()
    workspace = PrivateAgentWorkspace(tmp_path, agent.agent_id, agent.private_memory_namespace)
    formal = CognitiveMessage.create(
        message_id="message-1",
        session_id="session-1",
        sender_agent_id="other-agent",
        sender_role="ADVERSARIAL_REVIEWER",
        message_type="ADVERSARIAL_REVIEW",
        payload={"objections": ["formal objection"]},
        evidence_refs=("evidence://source",),
    )
    view = CognitiveContextView(
        session_id="session-1",
        objective="Find the narrowest claim.",
        project_scope="project://fixture",
        role=agent.role,
        context_isolation_key=agent.descriptor.context_isolation_key,
        private_workspace_descriptor=workspace.public_descriptor(),
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        evidence_payload={"frozen_summary": "public evidence only"},
        input_messages=(formal,),
        excluded_message_refs=(),
    )

    serialized = view.as_dict()

    assert serialized["input_messages"][0]["payload"] == {"objections": ["formal objection"]}
    assert "events.jsonl" not in str(serialized)
