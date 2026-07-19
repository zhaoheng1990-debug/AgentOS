import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor
from agentos_runtime import (
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveDeliberationSession,
    standard_role_contract,
)


ROLES = (
    "HYPOTHESIS_GENERATOR",
    "ADVERSARIAL_REVIEWER",
    "REPLICATOR",
    "SYNTHESIZER",
)


def agent(role: str, index: int) -> CognitiveAgent:
    agent_id = role.lower().replace("_", "-")
    descriptor = AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=("semantic_judgment", "source_read"),
        runner_id=f"runner-{index}",
        harness_id=f"harness-{index}",
        provider_id=f"provider-{index}",
        context_isolation_key=f"context-{index}",
        allowed_evidence_scopes=("project://fixture",),
    )
    return CognitiveAgent(
        descriptor,
        standard_role_contract(role),
        model_id=f"model-{index}",
        private_memory_namespace=f"memory-{index}",
        harness_capabilities=("source_read", f"role_action_{index}"),
        credit_subject_id=f"credit-{index}",
    )


def role_payload(role: str, evidence_ref: str = "evidence://source") -> dict:
    if role == "HYPOTHESIS_GENERATOR":
        return {
            "hypotheses": ["claim-a"],
            "assumptions": ["assumption-a"],
            "rival_explanations": ["rival-a"],
            "falsifiable_predictions": ["prediction-a"],
            "evidence_refs": [evidence_ref],
            "confidence": 0.7,
        }
    if role == "ADVERSARIAL_REVIEWER":
        return {
            "objections": ["objection-a"],
            "strongest_falsifier": "evidence://source",
            "rival_set_coverage": 0.8,
            "evidence_refs": [evidence_ref],
            "recommended_epistemic_state": "PENDING",
            "confidence": 0.8,
        }
    if role == "REPLICATOR":
        return {
            "replication_outcome": "INCONCLUSIVE",
            "gate_results": {"G1": False},
            "deviations": ["insufficient power"],
            "evidence_refs": [evidence_ref],
            "confidence": 0.75,
        }
    return {
        "converged_claims": [],
        "unresolved_conflicts": ["claim-a remains unresolved"],
        "minority_positions": ["rival-a"],
        "evidence_refs": [evidence_ref],
        "uncertainties": ["replication inconclusive"],
    }


class ScriptedAgentAdapter:
    def __init__(self, cognitive_agent: CognitiveAgent, payloads: list[dict] | None = None):
        self.adapter_id = f"adapter-{cognitive_agent.agent_id}"
        self.agent = cognitive_agent
        self.payloads = list(payloads or [role_payload(cognitive_agent.role)])
        self.contexts = []
        self.workspaces = []

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        assert cognitive_agent.agent_id == self.agent.agent_id
        self.contexts.append(context_view)
        self.workspaces.append(private_workspace)
        payload = self.payloads.pop(0)
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.agent.descriptor.provider_id,
            model_id=self.agent.model_id,
            invocation_receipt_ref=f"provider-receipt://{work_order.work_order_id}",
        )


def session(tmp_path, *, adapters=None, cognitive_agents=None):
    cognitive_agents = cognitive_agents or tuple(agent(role, index) for index, role in enumerate(ROLES, start=1))
    adapters = adapters or {
        item.agent_id: ScriptedAgentAdapter(item)
        for item in cognitive_agents
    }
    return CognitiveDeliberationSession(
        session_id="session-fixture",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        agents=cognitive_agents,
        adapters=adapters,
        workspace_root=tmp_path / "private-workspaces",
        kernel_authorization_ref="kernel-authorization://fixture",
    ), adapters


def test_four_roles_execute_with_information_barriers_and_kernel_owned_candidate_state(tmp_path):
    deliberation, adapters = session(tmp_path)

    result = deliberation.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert result.candidate_state == "PENDING_EPISTEMIC_REVIEW"
    assert [message.message_type for message in result.messages] == [
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
        "BOUNDED_SYNTHESIS",
    ]
    assert adapters["hypothesis-generator"].contexts[0].input_messages == ()
    assert [item.message_type for item in adapters["adversarial-reviewer"].contexts[0].input_messages] == [
        "HYPOTHESIS_PROPOSAL"
    ]
    assert [item.message_type for item in adapters["replicator"].contexts[0].input_messages] == [
        "HYPOTHESIS_PROPOSAL"
    ]
    assert [item.message_type for item in adapters["synthesizer"].contexts[0].input_messages] == [
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
    ]
    assert all(len(adapter.workspaces) == 1 for adapter in adapters.values())
    assert len({adapter.workspaces[0].namespace for adapter in adapters.values()}) == 4
    assert all(receipt.status == "COMPLETED" for receipt in result.execution_receipts)
    replay = deliberation.verify_replay()
    assert replay["valid"] is True
    assert replay["event_count"] == 5
    assert deliberation.public_store_path.joinpath("snapshot.json").is_file()
    assert deliberation.public_store_path.joinpath("events.jsonl").is_file()


def test_kernel_authorized_reviewer_ablation_runs_remaining_roles_only(tmp_path):
    cognitive_agents = tuple(
        agent(role, index)
        for index, role in enumerate(ROLES, start=1)
        if role != "ADVERSARIAL_REVIEWER"
    )
    adapters = {item.agent_id: ScriptedAgentAdapter(item) for item in cognitive_agents}
    deliberation = CognitiveDeliberationSession(
        session_id="reviewer-ablation",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        agents=cognitive_agents,
        adapters=adapters,
        workspace_root=tmp_path / "reviewer-ablation",
        kernel_authorization_ref="kernel-authorization://fixture",
        authorized_omitted_roles=("ADVERSARIAL_REVIEWER",),
        ablation_authorization_ref="kernel://organization-ablation/no-reviewer",
    )

    result = deliberation.run_to_candidate()

    assert [message.message_type for message in result.messages] == [
        "HYPOTHESIS_PROPOSAL",
        "REPLICATION_REPORT",
        "BOUNDED_SYNTHESIS",
    ]
    assert [item.message_type for item in adapters["synthesizer"].contexts[0].input_messages] == [
        "HYPOTHESIS_PROPOSAL",
        "REPLICATION_REPORT",
    ]
    assert result.stage == "CANDIDATE"
    assert deliberation.verify_replay()["valid"]


def test_role_omission_requires_explicit_kernel_ablation_authorization(tmp_path):
    cognitive_agents = tuple(
        agent(role, index)
        for index, role in enumerate(ROLES, start=1)
        if role != "REPLICATOR"
    )

    with pytest.raises(ValueError, match="deliberation_role_omission_not_authorized"):
        CognitiveDeliberationSession(
            session_id="unauthorized-ablation",
            objective="Determine the narrowest source-supported claim.",
            project_scope="project://fixture",
            frozen_gate_refs=("gate://fixture",),
            evidence_refs=("evidence://source",),
            agents=cognitive_agents,
            adapters={item.agent_id: ScriptedAgentAdapter(item) for item in cognitive_agents},
            workspace_root=tmp_path / "unauthorized",
            kernel_authorization_ref="kernel-authorization://fixture",
            authorized_omitted_roles=("REPLICATOR",),
        )


def test_shared_private_memory_namespace_cannot_form_cognitive_organization(tmp_path):
    cognitive_agents = list(agent(role, index) for index, role in enumerate(ROLES, start=1))
    cognitive_agents[1] = CognitiveAgent(
        cognitive_agents[1].descriptor,
        cognitive_agents[1].contract,
        model_id=cognitive_agents[1].model_id,
        private_memory_namespace=cognitive_agents[0].private_memory_namespace,
        harness_capabilities=cognitive_agents[1].harness_capabilities,
        credit_subject_id=cognitive_agents[1].credit_subject_id,
    )

    with pytest.raises(ValueError, match="cognitive_team_private_memory_not_isolated"):
        session(tmp_path, cognitive_agents=tuple(cognitive_agents))


def test_missing_provider_output_blocks_and_retry_preserves_failed_receipt(tmp_path):
    cognitive_agents = tuple(agent(role, index) for index, role in enumerate(ROLES, start=1))
    generator = cognitive_agents[0]
    invalid = role_payload(generator.role)
    invalid.pop("confidence")
    adapters = {item.agent_id: ScriptedAgentAdapter(item) for item in cognitive_agents}
    adapters[generator.agent_id] = ScriptedAgentAdapter(generator, [invalid, role_payload(generator.role)])
    deliberation, _ = session(tmp_path, adapters=adapters, cognitive_agents=cognitive_agents)

    blocked = deliberation.execute_current()

    assert blocked.stage == "BLOCKED"
    assert blocked.messages == ()
    assert blocked.execution_receipts[-1].status == "BLOCKED"
    assert "confidence" in blocked.execution_receipts[-1].errors[0]

    retried = deliberation.retry_blocked()

    assert retried.stage == "REVIEW"
    assert len(retried.messages) == 1
    assert [item.status for item in retried.execution_receipts] == ["BLOCKED", "COMPLETED"]


def test_unapproved_evidence_and_agent_owned_final_state_are_blocked(tmp_path):
    cognitive_agents = tuple(agent(role, index) for index, role in enumerate(ROLES, start=1))
    generator = cognitive_agents[0]
    outside = role_payload(generator.role, evidence_ref="evidence://outside-scope")
    adapters = {item.agent_id: ScriptedAgentAdapter(item) for item in cognitive_agents}
    adapters[generator.agent_id] = ScriptedAgentAdapter(generator, [outside])
    deliberation, _ = session(tmp_path, adapters=adapters, cognitive_agents=cognitive_agents)

    blocked = deliberation.execute_current()

    assert blocked.stage == "BLOCKED"
    assert "provider_evidence_ref_not_admitted" in blocked.execution_receipts[-1].errors

    clean_deliberation, clean_adapters = session(tmp_path / "authority")
    clean_deliberation.execute_current()
    clean_deliberation.execute_current()
    clean_deliberation.execute_current()
    synth_payload = role_payload("SYNTHESIZER")
    synth_payload["final_candidate_state"] = "ACCEPTED"
    clean_adapters["synthesizer"].payloads = [synth_payload]

    authority_block = clean_deliberation.execute_current()

    assert authority_block.stage == "BLOCKED"
    assert "agent_final_state_authority_forbidden" in authority_block.execution_receipts[-1].errors


def test_public_deliberation_replay_detects_event_tampering(tmp_path):
    deliberation, _adapters = session(tmp_path)
    deliberation.execute_current()
    events_path = deliberation.public_store_path / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[1]["payload"]["next_stage"] = "CANDIDATE"
    events_path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")

    verification = deliberation.verify_replay()

    assert verification["valid"] is False
    assert "event_hash_mismatch:1" in verification["failures"]


def test_kernel_authorized_synthesizer_omission_forms_candidate_without_synthesis(tmp_path):
    cognitive_agents = tuple(
        agent(role, index)
        for index, role in enumerate(ROLES, start=1)
        if role != "SYNTHESIZER"
    )
    adapters = {item.agent_id: ScriptedAgentAdapter(item) for item in cognitive_agents}
    deliberation = CognitiveDeliberationSession(
        session_id="session-no-synthesizer",
        objective="Measure the contribution of bounded synthesis.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        agents=cognitive_agents,
        adapters=adapters,
        workspace_root=tmp_path / "private-workspaces",
        kernel_authorization_ref="kernel://organization-ablation/no-synthesizer",
        authorized_omitted_roles=("SYNTHESIZER",),
        ablation_authorization_ref="kernel://organization-ablation/no-synthesizer",
    )

    result = deliberation.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert result.candidate_state == "PENDING_EPISTEMIC_REVIEW"
    assert [message.message_type for message in result.messages] == [
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
    ]
    assert result.authorized_omitted_roles == ("SYNTHESIZER",)
    assert deliberation.verify_replay()["valid"] is True
