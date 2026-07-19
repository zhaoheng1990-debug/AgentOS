import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor, ProviderCapabilityProfile, ProviderTaskRouter
from agentos_runtime import (
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveDeliberationSession,
    CognitiveMessage,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)


ROLE_ORDER = (
    "HYPOTHESIS_GENERATOR",
    "ADVERSARIAL_REVIEWER",
    "REPLICATOR",
    "SYNTHESIZER",
)


def make_agent(role: str, index: int) -> CognitiveAgent:
    slug = role.lower().replace("_", "-")
    descriptor = AgentDescriptor(
        agent_id=slug,
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
        harness_capabilities=("source_read", "formal_receipt_write"),
        credit_subject_id=f"credit-{index}",
    )


def role_payload(role: str) -> dict:
    if role == "HYPOTHESIS_GENERATOR":
        return {
            "hypotheses": ["claim-a"],
            "assumptions": ["assumption-a"],
            "rival_explanations": ["rival-a"],
            "falsifiable_predictions": ["prediction-a"],
            "evidence_refs": ["evidence://source"],
            "confidence": 0.7,
        }
    if role == "ADVERSARIAL_REVIEWER":
        return {
            "objections": ["objection-a"],
            "strongest_falsifier": "evidence://source",
            "rival_set_coverage": 0.8,
            "evidence_refs": ["evidence://source"],
            "recommended_epistemic_state": "PENDING",
            "confidence": 0.8,
        }
    if role == "REPLICATOR":
        return {
            "replication_outcome": "INCONCLUSIVE",
            "gate_results": {"G1": False},
            "deviations": ["insufficient power"],
            "evidence_refs": ["evidence://source"],
            "confidence": 0.75,
        }
    return {
        "converged_claims": [],
        "unresolved_conflicts": ["claim-a remains unresolved"],
        "minority_positions": ["rival-a"],
        "evidence_refs": ["evidence://source"],
        "uncertainties": ["replication inconclusive"],
    }


def coordination_payload(action: str, target_role: str, **overrides) -> dict:
    payload = {
        "route_action": action,
        "target_role": target_role,
        "rationale": "Choose the next bounded action from public receipts.",
        "unresolved_questions": ["Does the claim survive independent checks?"],
        "evidence_gaps": [],
        "conflict_message_refs": [],
        "evidence_refs": ["evidence://source"],
        "expected_cbit_gain": 0.4,
        "stop_condition": "Stop after bounded synthesis is formally available.",
    }
    payload.update(overrides)
    return payload


class ScriptedAdapter:
    def __init__(self, cognitive_agent: CognitiveAgent, payloads: list[dict]):
        self.adapter_id = f"adapter-{cognitive_agent.agent_id}"
        self.agent = cognitive_agent
        self.payloads = list(payloads)
        self.contexts = []
        self.work_orders = []

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        assert cognitive_agent.agent_id == self.agent.agent_id
        self.contexts.append(context_view)
        self.work_orders.append(work_order)
        if cognitive_agent.role == "COORDINATOR":
            private_workspace.append(
                cognitive_agent.agent_id,
                "PRIVATE_COORDINATOR_NOTE",
                {"private_note_text": "must not enter the public context"},
            )
            assert "must not enter the public context" not in str(context_view.as_dict())
        payload = self.payloads.pop(0)
        if isinstance(payload, AgentAdapterResult):
            return payload
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.agent.descriptor.provider_id,
            model_id=self.agent.model_id,
            invocation_receipt_ref=f"provider-receipt://{work_order.work_order_id}",
        )


class CapturingProviderAdapter:
    def __init__(self, cognitive_agent: CognitiveAgent, payload: dict):
        self.profile = ProviderCapabilityProfile(
            provider_id=cognitive_agent.descriptor.provider_id,
            model_id=cognitive_agent.model_id,
            task_kinds=(cognitive_agent.contract.provider_operation_id,),
            max_timeout_seconds=120,
        )
        self.payload = payload
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.payload,
            "usage": {"total_tokens": 50},
            "provenance_refs": task.allowed_evidence,
        }


def make_runtime(
    tmp_path,
    payloads,
    *,
    max_cycles=8,
    max_role_executions_per_role=2,
    authorized_omitted_roles=(),
):
    coordinator = make_agent("COORDINATOR", 5)
    adapter = ScriptedAdapter(coordinator, payloads)
    runtime = CognitiveCoordinationRuntime(
        coordinator=coordinator,
        adapter=adapter,
        workspace_root=tmp_path / "coordinator-private",
        max_cycles=max_cycles,
        max_role_executions_per_role=max_role_executions_per_role,
        authorized_omitted_roles=authorized_omitted_roles,
        ablation_authorization_ref=(
            "kernel://organization-ablation/coordinator"
            if authorized_omitted_roles
            else ""
        ),
    )
    return runtime, adapter


def coordinate(runtime, *, current_stage="INTAKE", messages=(), counts=None):
    return runtime.coordinate(
        session_id="session-fixture",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        evidence_payload={"public_summary": "public evidence only"},
        messages=messages,
        role_execution_counts=counts or {role: 0 for role in ROLE_ORDER},
        current_stage=current_stage,
        kernel_authorization_ref="kernel-authorization://fixture",
    )


def test_coordinator_proposes_but_kernel_applies_route_and_keeps_private_memory_isolated(tmp_path):
    runtime, adapter = make_runtime(
        tmp_path,
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
    )

    decision = coordinate(runtime)

    assert decision.status == "APPLIED"
    assert decision.next_stage == "GENERATION"
    assert decision.proposal.route_action == "RUN_ROLE"
    assert decision.receipt.status == "COMPLETED"
    assert decision.receipt.provider_audit["status"].startswith("PASS_PROVIDER_SUPPORT")
    assert adapter.contexts[0].coordination_state["current_stage"] == "INTAKE"
    assert adapter.contexts[0].input_messages == ()
    assert adapter.work_orders[0].stage == "COORDINATION"
    assert decision.proposal.as_dict().get("final_candidate_state") is None


def test_coordinator_uses_existing_provider_router_with_fixed_identity(tmp_path):
    coordinator = make_agent("COORDINATOR", 5)
    provider = CapturingProviderAdapter(
        coordinator,
        coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR"),
    )
    adapter = ProviderCognitiveAgentAdapter(
        "coordinator-provider-adapter",
        ProviderTaskRouter([provider]),
    )
    runtime = CognitiveCoordinationRuntime(
        coordinator=coordinator,
        adapter=adapter,
        workspace_root=tmp_path / "coordinator-private",
    )

    decision = coordinate(runtime)

    assert decision.status == "APPLIED"
    assert provider.tasks[0].task_kind == "cognitive_deliberation_coordination"
    assert provider.tasks[0].inputs["context"]["coordination_state"]["current_stage"] == "INTAKE"
    assert provider.tasks[0].expected_schema["properties"]["stop_condition"]["minLength"] == 1
    assert provider.tasks[0].expected_schema["properties"]["evidence_refs"]["minItems"] == 1
    assert "events.jsonl" not in str(provider.tasks[0].inputs)
    assert decision.receipt.provider_id == coordinator.descriptor.provider_id
    assert decision.receipt.model_id == coordinator.model_id


def test_coordinator_cannot_claim_final_state_or_use_unadmitted_evidence(tmp_path):
    authority = coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR", accepted=True)
    runtime, _adapter = make_runtime(tmp_path / "authority", [authority])

    blocked = coordinate(runtime)

    assert blocked.status == "BLOCKED"
    assert "coordinator_final_state_authority_forbidden" in blocked.errors
    assert blocked.next_stage == ""

    outside = coordination_payload(
        "RUN_ROLE",
        "HYPOTHESIS_GENERATOR",
        evidence_refs=["evidence://outside"],
    )
    runtime, _adapter = make_runtime(tmp_path / "outside", [outside])

    blocked = coordinate(runtime)

    assert blocked.status == "BLOCKED"
    assert "coordinator_evidence_ref_not_admitted" in blocked.errors


def test_coordinator_rejects_nonfinite_cbit_and_empty_semantic_fields(tmp_path):
    invalid = coordination_payload(
        "RUN_ROLE",
        "HYPOTHESIS_GENERATOR",
        expected_cbit_gain=float("nan"),
        rationale="",
        stop_condition="",
        evidence_refs=[],
    )
    runtime, _adapter = make_runtime(tmp_path, [invalid])

    blocked = coordinate(runtime)

    assert blocked.status == "BLOCKED"
    assert "coordinator_expected_cbit_must_be_finite" in blocked.errors
    assert "coordinator_rationale_required" in blocked.errors
    assert "coordinator_stop_condition_required" in blocked.errors
    assert "coordinator_evidence_refs_required" in blocked.errors


def test_kernel_blocks_premature_synthesis_and_role_budget_overrun(tmp_path):
    runtime, _adapter = make_runtime(
        tmp_path / "premature",
        [coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER")],
    )

    premature = coordinate(runtime)

    assert premature.status == "BLOCKED"
    assert premature.errors == (
        "field_enum_mismatch:route_action",
        "field_enum_mismatch:target_role",
    )

    runtime, _adapter = make_runtime(
        tmp_path / "budget",
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
        max_role_executions_per_role=1,
    )
    exhausted = coordinate(
        runtime,
        current_stage="GENERATION",
        counts={**{role: 0 for role in ROLE_ORDER}, "HYPOTHESIS_GENERATOR": 1},
    )

    assert exhausted.status == "BLOCKED"
    assert "coordination_role_execution_budget_exhausted:HYPOTHESIS_GENERATOR" in exhausted.errors


def test_coordinator_schema_exposes_only_kernel_reachable_intake_actions(tmp_path):
    runtime, adapter = make_runtime(
        tmp_path,
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
    )

    decision = coordinate(runtime)

    assert decision.status == "APPLIED"
    schema = adapter.work_orders[0].output_schema["properties"]
    assert schema["route_action"]["enum"] == [
        "RUN_ROLE",
        "REQUEST_EVIDENCE",
        "STOP_BLOCKED",
    ]
    assert schema["target_role"]["enum"] == ["HYPOTHESIS_GENERATOR", "NONE"]


def test_kernel_mandatory_progression_allows_zero_local_gain_but_discretionary_rerun_does_not(tmp_path):
    runtime, _adapter = make_runtime(
        tmp_path / "mandatory",
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR", expected_cbit_gain=0.0)],
    )

    mandatory = coordinate(runtime)

    assert mandatory.status == "APPLIED"
    proposal = CognitiveMessage.create(
        message_id="proposal-zero-rerun",
        session_id="session-fixture",
        sender_agent_id="hypothesis-generator",
        sender_role="HYPOTHESIS_GENERATOR",
        message_type="HYPOTHESIS_PROPOSAL",
        payload={"hypotheses": ["claim-a"]},
        evidence_refs=("evidence://source",),
    )
    proposal_ref = f"message://{proposal.message_id}/{proposal.message_hash}"
    runtime, _adapter = make_runtime(
        tmp_path / "rerun",
        [
            coordination_payload(
                "RUN_ROLE",
                "HYPOTHESIS_GENERATOR",
                expected_cbit_gain=0.0,
                conflict_message_refs=[proposal_ref],
            )
        ],
    )

    rerun = coordinate(
        runtime,
        current_stage="GENERATION",
        messages=(proposal,),
        counts={**{role: 0 for role in ROLE_ORDER}, "HYPOTHESIS_GENERATOR": 1},
    )

    assert rerun.status == "BLOCKED"
    assert "coordination_positive_cbit_required_for_role_execution" in rerun.errors


def test_coordinator_replans_synthesis_prerequisites_for_authorized_reviewer_ablation(tmp_path):
    proposal = CognitiveMessage.create(
        message_id="proposal-ablation",
        session_id="session-fixture",
        sender_agent_id="hypothesis-generator",
        sender_role="HYPOTHESIS_GENERATOR",
        message_type="HYPOTHESIS_PROPOSAL",
        payload={"hypotheses": ["claim-a"]},
        evidence_refs=("evidence://source",),
    )
    replication = CognitiveMessage.create(
        message_id="replication-ablation",
        session_id="session-fixture",
        sender_agent_id="replicator",
        sender_role="REPLICATOR",
        message_type="REPLICATION_REPORT",
        payload={"replication_outcome": "INCONCLUSIVE"},
        evidence_refs=("evidence://source",),
        parent_message_refs=(f"message://{proposal.message_id}/{proposal.message_hash}",),
    )
    runtime, adapter = make_runtime(
        tmp_path,
        [coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER")],
        authorized_omitted_roles=("ADVERSARIAL_REVIEWER",),
    )

    decision = coordinate(
        runtime,
        current_stage="REPLICATION",
        messages=(proposal, replication),
        counts={
            "HYPOTHESIS_GENERATOR": 1,
            "ADVERSARIAL_REVIEWER": 0,
            "REPLICATOR": 1,
            "SYNTHESIZER": 0,
        },
    )

    assert decision.status == "APPLIED"
    assert decision.next_stage == "SYNTHESIS"
    state = adapter.contexts[0].coordination_state
    assert state["authorized_omitted_roles"] == ["ADVERSARIAL_REVIEWER"]
    assert all(
        candidate.get("target_role") != "ADVERSARIAL_REVIEWER"
        for candidate in state["admissible_progression_candidates"]
    )


def test_coordinator_finalizes_authorized_no_synthesizer_protocol_without_bounded_synthesis(tmp_path):
    role_agents = tuple(make_agent(role, index) for index, role in enumerate(ROLE_ORDER[:3], start=1))
    messages = tuple(
        CognitiveMessage.create(
            message_id=f"message-{index}",
            session_id="session-no-synth",
            sender_agent_id=item.agent_id,
            sender_role=item.role,
            message_type=item.contract.output_message_type,
            payload=role_payload(item.role),
            evidence_refs=("evidence://source",),
        )
        for index, item in enumerate(role_agents, start=1)
    )
    runtime, adapter = make_runtime(
        tmp_path,
        [coordination_payload("FINALIZE_CANDIDATE", "NONE", expected_cbit_gain=0.0)],
        authorized_omitted_roles=("SYNTHESIZER",),
    )

    decision = coordinate(
        runtime,
        current_stage="REPLICATION",
        messages=messages,
        counts={
            "HYPOTHESIS_GENERATOR": 1,
            "ADVERSARIAL_REVIEWER": 1,
            "REPLICATOR": 1,
            "SYNTHESIZER": 0,
        },
    )

    assert decision.status == "APPLIED"
    assert decision.next_stage == "CANDIDATE"
    state = adapter.contexts[0].coordination_state
    assert state["admissible_progression_candidates"] == [
        {"route_action": "FINALIZE_CANDIDATE", "target_role": "NONE"}
    ]
    assert "PROCEED_TO_SYNTHESIS" not in state["allowed_route_actions"]
    assert "asks the Kernel to form a pending candidate" in state["kernel_route_policy"]


def test_reexecuting_completed_role_requires_public_conflict_reference(tmp_path):
    proposal = CognitiveMessage.create(
        message_id="proposal-1",
        session_id="session-fixture",
        sender_agent_id="hypothesis-generator",
        sender_role="HYPOTHESIS_GENERATOR",
        message_type="HYPOTHESIS_PROPOSAL",
        payload={"hypotheses": ["claim-a"]},
        evidence_refs=("evidence://source",),
    )
    counts = {**{role: 0 for role in ROLE_ORDER}, "HYPOTHESIS_GENERATOR": 1}
    runtime, _adapter = make_runtime(
        tmp_path / "without-conflict",
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
    )

    blocked = coordinate(runtime, current_stage="GENERATION", messages=(proposal,), counts=counts)

    assert blocked.status == "BLOCKED"
    assert "coordination_reexecution_requires_public_conflict_ref" in blocked.errors

    proposal_ref = f"message://{proposal.message_id}/{proposal.message_hash}"
    runtime, _adapter = make_runtime(
        tmp_path / "with-conflict",
        [
            coordination_payload(
                "RUN_ROLE",
                "HYPOTHESIS_GENERATOR",
                conflict_message_refs=[proposal_ref],
            )
        ],
    )

    applied = coordinate(runtime, current_stage="GENERATION", messages=(proposal,), counts=counts)

    assert applied.status == "APPLIED"
    assert applied.next_stage == "GENERATION"


def test_coordination_cycle_budget_blocks_without_another_provider_call(tmp_path):
    runtime, adapter = make_runtime(
        tmp_path,
        [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
        max_cycles=1,
    )

    assert coordinate(runtime).status == "APPLIED"
    exhausted = coordinate(runtime)

    assert exhausted.status == "BLOCKED"
    assert exhausted.errors == ("coordination_cycle_budget_exhausted",)
    assert len(adapter.contexts) == 1


def test_session_rejects_coordinator_that_reuses_role_context(tmp_path):
    role_agents = tuple(make_agent(role, index) for index, role in enumerate(ROLE_ORDER, start=1))
    coordinator = make_agent("COORDINATOR", 5)
    descriptor = AgentDescriptor(
        agent_id=coordinator.agent_id,
        role=coordinator.role,
        capabilities=coordinator.descriptor.capabilities,
        runner_id=coordinator.descriptor.runner_id,
        harness_id=coordinator.descriptor.harness_id,
        provider_id=coordinator.descriptor.provider_id,
        context_isolation_key=role_agents[0].descriptor.context_isolation_key,
        allowed_evidence_scopes=coordinator.descriptor.allowed_evidence_scopes,
    )
    coordinator = CognitiveAgent(
        descriptor,
        coordinator.contract,
        coordinator.model_id,
        coordinator.private_memory_namespace,
        coordinator.harness_capabilities,
        coordinator.credit_subject_id,
    )
    runtime = CognitiveCoordinationRuntime(
        coordinator=coordinator,
        adapter=ScriptedAdapter(
            coordinator,
            [coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR")],
        ),
        workspace_root=tmp_path / "coordinator-private",
    )

    with pytest.raises(ValueError, match="coordinator_context_not_isolated"):
        CognitiveDeliberationSession(
            session_id="session-context-collision",
            objective="Determine the narrowest source-supported claim.",
            project_scope="project://fixture",
            frozen_gate_refs=("gate://fixture",),
            evidence_refs=("evidence://source",),
            agents=role_agents,
            adapters={item.agent_id: ScriptedAdapter(item, [role_payload(item.role)]) for item in role_agents},
            workspace_root=tmp_path / "role-private",
            kernel_authorization_ref="kernel-authorization://fixture",
            coordination_runtime=runtime,
        )


def test_deliberation_session_uses_coordinator_for_dynamic_role_order_and_finalization(tmp_path):
    role_agents = tuple(make_agent(role, index) for index, role in enumerate(ROLE_ORDER, start=1))
    role_adapters = {
        item.agent_id: ScriptedAdapter(item, [role_payload(item.role)])
        for item in role_agents
    }
    coordination_runtime, coordination_adapter = make_runtime(
        tmp_path,
        [
            coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR"),
            coordination_payload("RUN_ROLE", "REPLICATOR"),
            coordination_payload("RUN_ROLE", "ADVERSARIAL_REVIEWER"),
            coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER"),
            coordination_payload("FINALIZE_CANDIDATE", "NONE", expected_cbit_gain=0.0),
        ],
    )
    session = CognitiveDeliberationSession(
        session_id="session-fixture",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        evidence_payload={"public_summary": "public evidence only"},
        agents=role_agents,
        adapters=role_adapters,
        workspace_root=tmp_path / "role-private",
        kernel_authorization_ref="kernel-authorization://fixture",
        coordination_runtime=coordination_runtime,
    )

    result = session.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert result.candidate_state == "PENDING_EPISTEMIC_REVIEW"
    assert [message.message_type for message in result.messages] == [
        "HYPOTHESIS_PROPOSAL",
        "REPLICATION_REPORT",
        "ADVERSARIAL_REVIEW",
        "BOUNDED_SYNTHESIS",
    ]
    assert len(result.coordination_proposals) == 5
    assert len(result.coordination_receipts) == 5
    assert all(receipt.status == "COMPLETED" for receipt in result.coordination_receipts)
    assert [context.coordination_state["current_stage"] for context in coordination_adapter.contexts] == [
        "INTAKE",
        "GENERATION",
        "REPLICATION",
        "REVIEW",
        "SYNTHESIS",
    ]
    assert session.verify_replay()["valid"] is True


def test_distinct_coordination_checkpoints_recover_independently_and_preserve_failures(tmp_path):
    role_agents = tuple(make_agent(role, index) for index, role in enumerate(ROLE_ORDER, start=1))
    role_adapters = {
        item.agent_id: ScriptedAdapter(item, [role_payload(item.role)])
        for item in role_agents
    }
    coordinator = make_agent("COORDINATOR", 5)
    unavailable = AgentAdapterResult(
        status="PROVIDER_UNAVAILABLE",
        provider_support_receipt=None,
        provider_id=coordinator.descriptor.provider_id,
        model_id=coordinator.model_id,
        invocation_receipt_ref="provider-receipt://unavailable",
        validation_errors=("provider_unavailable",),
    )
    coordination_adapter = ScriptedAdapter(
        coordinator,
        [
            coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR"),
            unavailable,
            coordination_payload("RUN_ROLE", "REPLICATOR"),
            unavailable,
            coordination_payload("RUN_ROLE", "ADVERSARIAL_REVIEWER"),
            coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER"),
            coordination_payload("FINALIZE_CANDIDATE", "NONE", expected_cbit_gain=0.0),
        ],
    )
    coordination_runtime = CognitiveCoordinationRuntime(
        coordinator=coordinator,
        adapter=coordination_adapter,
        workspace_root=tmp_path / "coordinator-private",
        max_cycles=8,
        max_role_executions_per_role=2,
    )
    session = CognitiveDeliberationSession(
        session_id="session-recovery",
        objective="Determine the narrowest source-supported claim.",
        project_scope="project://fixture",
        frozen_gate_refs=("gate://fixture",),
        evidence_refs=("evidence://source",),
        agents=role_agents,
        adapters=role_adapters,
        workspace_root=tmp_path / "role-private",
        kernel_authorization_ref="kernel-authorization://fixture",
        coordination_runtime=coordination_runtime,
    )

    result = session.run_to_candidate(max_retries_per_stage=1)

    assert result.stage == "CANDIDATE"
    assert [receipt.status for receipt in result.coordination_receipts].count("BLOCKED") == 2
    assert [receipt.status for receipt in result.coordination_receipts].count("COMPLETED") == 5
    assert len(result.coordination_proposals) == 5
    assert session.verify_replay()["valid"] is True
