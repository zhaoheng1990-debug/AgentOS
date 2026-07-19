import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor
from agentos_runtime import (
    CognitiveAgent,
    CognitiveMessage,
    PrivateAgentWorkspace,
    standard_role_contract,
)


def descriptor(agent_id: str, role: str, context: str) -> AgentDescriptor:
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=("semantic_judgment",),
        runner_id="codex",
        harness_id=f"harness-{agent_id}",
        provider_id="provider-a",
        context_isolation_key=context,
        allowed_evidence_scopes=("project://fixture",),
    )


def test_standard_roles_have_distinct_epistemic_contracts_without_final_state_authority():
    roles = (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "SYNTHESIZER",
    )
    contracts = [standard_role_contract(role) for role in roles]

    assert len({item.contract_id for item in contracts}) == 4
    assert len({item.provider_operation_id for item in contracts}) == 4
    assert len({item.output_message_type for item in contracts}) == 4
    assert all(item.provider_required for item in contracts)
    assert all(item.final_state_authority is False for item in contracts)
    assert standard_role_contract("REPLICATOR").allowed_input_message_types == ("HYPOTHESIS_PROPOSAL",)
    assert standard_role_contract("SYNTHESIZER").allowed_input_message_types == (
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
    )
    coordinator = standard_role_contract("COORDINATOR")
    assert coordinator.provider_operation_id == "cognitive_deliberation_coordination"
    assert coordinator.output_message_type == "COORDINATION_PROPOSAL"
    assert coordinator.final_state_authority is False


def test_problem_definition_roles_have_independent_provider_operations_and_information_barriers():
    roles = (
        "PROBLEM_FRAMER",
        "PROBLEM_CRITIC",
        "RESEARCHABILITY_ASSESSOR",
        "AGENDA_SYNTHESIZER",
    )
    contracts = [standard_role_contract(role) for role in roles]

    assert len({contract.provider_operation_id for contract in contracts}) == 4
    assert len({contract.output_message_type for contract in contracts}) == 4
    assert contracts[0].allowed_input_message_types == ()
    assert contracts[1].allowed_input_message_types == ("PROBLEM_CANDIDATE_SET",)
    assert contracts[2].allowed_input_message_types == ("PROBLEM_CANDIDATE_SET",)
    assert contracts[3].allowed_input_message_types == (
        "PROBLEM_CANDIDATE_SET",
        "PROBLEM_CRITIQUE",
        "RESEARCHABILITY_REPORT",
    )
    assert all(contract.final_state_authority is False for contract in contracts)


def test_cognitive_agent_binds_role_provider_model_memory_and_harness_capabilities():
    contract = standard_role_contract("HYPOTHESIS_GENERATOR")
    agent = CognitiveAgent(
        descriptor("generator", "HYPOTHESIS_GENERATOR", "ctx-generator"),
        contract,
        model_id="model-a",
        private_memory_namespace="memory-generator",
        harness_capabilities=("source_read", "hypothesis_write"),
        credit_subject_id="credit-generator",
    )

    assert agent.role == "HYPOTHESIS_GENERATOR"
    assert agent.provider_binding == "provider-a/model-a"
    assert agent.private_memory_namespace == "memory-generator"
    assert agent.contract.final_state_authority is False

    with pytest.raises(ValueError, match="agent_role_contract_mismatch"):
        CognitiveAgent(
            descriptor("wrong", "ADVERSARIAL_REVIEWER", "ctx-wrong"),
            contract,
            model_id="model-a",
            private_memory_namespace="memory-wrong",
            harness_capabilities=("source_read",),
            credit_subject_id="credit-wrong",
        )


def test_private_workspace_is_owner_scoped_and_hash_chained(tmp_path):
    workspace = PrivateAgentWorkspace(tmp_path, "generator", "memory-generator")

    first = workspace.append("generator", "WORK_ORDER_RECEIVED", {"work_order_id": "wo-1"})
    second = workspace.append("generator", "PRIVATE_NOTE", {"note": "unpublished rival"})

    assert first["previous_event_hash"] == ""
    assert second["previous_event_hash"] == first["event_hash"]
    assert len(workspace.history("generator")) == 2
    with pytest.raises(PermissionError, match="private_workspace_owner_mismatch"):
        workspace.history("reviewer")


def test_formal_message_rejects_private_reasoning_export():
    with pytest.raises(ValueError, match="private_reasoning_export_forbidden"):
        CognitiveMessage.create(
            message_id="message-1",
            session_id="session-1",
            sender_agent_id="generator",
            sender_role="HYPOTHESIS_GENERATOR",
            message_type="HYPOTHESIS_PROPOSAL",
            payload={
                "hypotheses": ["candidate"],
                "chain_of_thought": "private internal reasoning",
            },
            evidence_refs=("evidence://source",),
        )


def test_formal_message_hash_commits_to_public_payload_and_evidence():
    message = CognitiveMessage.create(
        message_id="message-1",
        session_id="session-1",
        sender_agent_id="generator",
        sender_role="HYPOTHESIS_GENERATOR",
        message_type="HYPOTHESIS_PROPOSAL",
        payload={"hypotheses": ["candidate"], "rival_explanations": ["rival"]},
        evidence_refs=("evidence://source",),
    )

    assert len(message.message_hash) == 64
    assert message.as_dict()["payload"]["hypotheses"] == ["candidate"]
    assert "private_memory" not in message.as_dict()
