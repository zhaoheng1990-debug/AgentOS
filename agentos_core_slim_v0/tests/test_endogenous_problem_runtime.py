import json
import sys
from dataclasses import replace
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgentDescriptor, ProviderCapabilityProfile, ProviderTaskRouter
from agentos_runtime import (
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveDeliberationSession,
    EndogenousProblemRuntime,
    ProviderCognitiveAgentAdapter,
    standard_role_contract,
)


PROBLEM_ROLES = (
    "PROBLEM_FRAMER",
    "PROBLEM_CRITIC",
    "RESEARCHABILITY_ASSESSOR",
    "AGENDA_SYNTHESIZER",
)


def make_agent(role: str, index: int) -> CognitiveAgent:
    slug = role.lower().replace("_", "-")
    descriptor = AgentDescriptor(
        agent_id=slug,
        role=role,
        capabilities=("semantic_judgment", "source_read"),
        runner_id=f"problem-runner-{index}",
        harness_id=f"problem-harness-{index}",
        provider_id=f"problem-provider-{index}",
        context_isolation_key=f"problem-context-{index}",
        allowed_evidence_scopes=("project://fixture",),
    )
    return CognitiveAgent(
        descriptor,
        standard_role_contract(role),
        model_id=f"problem-model-{index}",
        private_memory_namespace=f"problem-memory-{index}",
        harness_capabilities=("source_read", "formal_receipt_write"),
        credit_subject_id=f"problem-credit-{index}",
    )


def framer_payload() -> dict:
    return {
        "problem_candidates": [
            {
                "problem_id": "problem-negative-control-mechanism",
                "question": "Which mechanism explains the failed negative-control family?",
                "research_object": "negative_control_failure",
                "scope": "project://fixture",
                "triggering_anomaly": "Local comparison survives while the family gate fails.",
                "rival_explanations": ["metric artifact", "scope-local effect"],
                "falsifier": "Independent family-level revalidation finds no failure.",
                "evidence_refs": ["evidence://source"],
                "expected_cbit_gain": 0.8,
                "urgency": 0.7,
                "novelty": 0.6,
            },
            {
                "problem_id": "problem-local-rule-transfer",
                "question": "Under which scopes do the local rules transfer to held-out conditions?",
                "research_object": "local_rule_transfer",
                "scope": "project://fixture",
                "triggering_anomaly": "Two local rules survive without global retention support.",
                "rival_explanations": ["overfitting", "bounded transfer"],
                "falsifier": "No preregistered held-out scope preserves either rule.",
                "evidence_refs": ["evidence://source"],
                "expected_cbit_gain": 0.7,
                "urgency": 0.5,
                "novelty": 0.8,
            },
        ],
        "generation_rationale": "Residual contradictions define two distinct research objects.",
        "coverage_notes": ["mechanism", "transfer boundary"],
        "evidence_refs": ["evidence://source"],
    }


def critic_payload() -> dict:
    return {
        "candidate_reviews": [
            {
                "problem_id": "problem-negative-control-mechanism",
                "premise_risk": 0.2,
                "redundancy_risk": 0.1,
                "negative_transfer_risk": 0.1,
                "challenge": "Separate mechanism failure from threshold choice.",
                "evidence_refs": ["evidence://source"],
            },
            {
                "problem_id": "problem-local-rule-transfer",
                "premise_risk": 0.3,
                "redundancy_risk": 0.2,
                "negative_transfer_risk": 0.2,
                "challenge": "Do not presuppose transfer exists.",
                "evidence_refs": ["evidence://source"],
            },
        ],
        "surviving_problem_ids": [
            "problem-negative-control-mechanism",
            "problem-local-rule-transfer",
        ],
        "minority_objections": ["The anomaly may be a frozen-threshold artifact."],
        "evidence_refs": ["evidence://source"],
    }


def assessor_payload() -> dict:
    return {
        "assessments": [
            {
                "problem_id": "problem-negative-control-mechanism",
                "operationalization": "Re-run each negative-control member against frozen thresholds.",
                "falsifiability": 0.9,
                "tractability": 0.8,
                "normalized_cost": 0.3,
                "required_harnesses": ["independent_experiment_harness"],
                "evidence_refs": ["evidence://source"],
            },
            {
                "problem_id": "problem-local-rule-transfer",
                "operationalization": "Pre-register held-out scopes and test both local rules.",
                "falsifiability": 0.8,
                "tractability": 0.6,
                "normalized_cost": 0.5,
                "required_harnesses": ["heldout_evaluation_harness"],
                "evidence_refs": ["evidence://source"],
            },
        ],
        "researchable_problem_ids": [
            "problem-negative-control-mechanism",
            "problem-local-rule-transfer",
        ],
        "missing_capabilities": [],
        "evidence_refs": ["evidence://source"],
    }


def synthesizer_payload(selected="problem-negative-control-mechanism") -> dict:
    rejected = [
        problem_id
        for problem_id in (
            "problem-negative-control-mechanism",
            "problem-local-rule-transfer",
        )
        if problem_id != selected
    ]
    return {
        "decision": "SELECT",
        "selected_problem_id": selected,
        "selection_rationale": "It most directly resolves the contradiction with high falsifiability.",
        "rejected_problem_ids": rejected,
        "unresolved_conflicts": ["Threshold artifact remains a rival."],
        "evidence_refs": ["evidence://source"],
        "expected_cbit_gain": 0.8,
        "stop_condition": "Stop if family-level revalidation removes the anomaly.",
    }


def role_payload(role: str) -> dict:
    return {
        "PROBLEM_FRAMER": framer_payload,
        "PROBLEM_CRITIC": critic_payload,
        "RESEARCHABILITY_ASSESSOR": assessor_payload,
        "AGENDA_SYNTHESIZER": synthesizer_payload,
    }[role]()


class ScriptedProblemAdapter:
    def __init__(self, agent: CognitiveAgent, payloads=None):
        self.adapter_id = f"problem-adapter-{agent.agent_id}"
        self.agent = agent
        self.payloads = list(payloads or [role_payload(agent.role)])
        self.contexts = []
        self.workspaces = []

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        assert cognitive_agent.agent_id == self.agent.agent_id
        self.contexts.append(context_view)
        self.workspaces.append(private_workspace)
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
    def __init__(self, agent: CognitiveAgent, payload: dict):
        self.profile = ProviderCapabilityProfile(
            provider_id=agent.descriptor.provider_id,
            model_id=agent.model_id,
            task_kinds=(agent.contract.provider_operation_id,),
            max_timeout_seconds=120,
        )
        self.payload = payload
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.payload,
            "usage": {"total_tokens": 100},
            "provenance_refs": task.allowed_evidence,
        }


def runtime(
    tmp_path,
    *,
    adapters=None,
    agents=None,
    minimum_priority=0.2,
    evidence_refs=("evidence://source",),
    invalidated_evidence_refs=(),
):
    agents = agents or tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    adapters = adapters or {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    return EndogenousProblemRuntime(
        session_id="problem-session-fixture",
        discovery_objective="Discover the next high-value research question from unresolved project evidence.",
        project_scope="project://fixture",
        evidence_refs=evidence_refs,
        evidence_payload={
            "observed_results": ["local rules survive"],
            "unresolved_conflicts": ["negative-control family fails"],
        },
        agents=agents,
        adapters=adapters,
        workspace_root=tmp_path / "problem-private",
        kernel_authorization_ref="kernel-authorization://problem-fixture",
        minimum_priority=minimum_priority,
        invalidated_evidence_refs=invalidated_evidence_refs,
    ), adapters


def test_group_problem_definition_emerges_candidate_and_deliberation_seed(tmp_path):
    problem_runtime, adapters = runtime(tmp_path)

    result = problem_runtime.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert result.candidate_state == "PENDING_AGENDA_REVIEW"
    assert [message.message_type for message in result.messages] == [
        "PROBLEM_CANDIDATE_SET",
        "PROBLEM_CRITIQUE",
        "RESEARCHABILITY_REPORT",
        "AGENDA_SELECTION_PROPOSAL",
    ]
    assert adapters["problem-framer"].contexts[0].input_messages == ()
    assert adapters["problem-framer"].contexts[0].runtime_state["seeded_problem_questions"] == []
    assert (
        adapters["problem-framer"].contexts[0].runtime_state["nested_output_contract"]
        ["problem_candidates"]["minimum_items"]
        == 2
    )
    assert [message.message_type for message in adapters["problem-critic"].contexts[0].input_messages] == [
        "PROBLEM_CANDIDATE_SET"
    ]
    assert [message.message_type for message in adapters["researchability-assessor"].contexts[0].input_messages] == [
        "PROBLEM_CANDIDATE_SET"
    ]
    assert [message.message_type for message in adapters["agenda-synthesizer"].contexts[0].input_messages] == [
        "PROBLEM_CANDIDATE_SET",
        "PROBLEM_CRITIQUE",
        "RESEARCHABILITY_REPORT",
    ]
    assert result.agenda_selection.decision == "SELECT"
    assert result.agenda_selection.execution_authorized is False
    assert result.deliberation_seed.source_problem_id == "problem-negative-control-mechanism"
    assert result.deliberation_seed.objective == "Which mechanism explains the failed negative-control family?"
    assert result.deliberation_seed.candidate_state == "PENDING_AGENDA_REVIEW"
    assert result.deliberation_seed.execution_authorized is False
    assert result.deliberation_seed.expected_cbit_gain == 0.8
    intake = result.deliberation_seed.as_coordination_intake()
    assert intake["objective"] == result.deliberation_seed.objective
    assert intake["project_scope"] == "project://fixture"
    assert intake["evidence_payload"]["source_problem_id"] == result.deliberation_seed.source_problem_id
    assert problem_runtime.verify_replay()["valid"] is True


def test_problem_roles_use_existing_provider_router_and_registered_operations(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    providers = {
        agent.agent_id: CapturingProviderAdapter(agent, role_payload(agent.role))
        for agent in agents
    }
    adapters = {
        agent.agent_id: ProviderCognitiveAgentAdapter(
            f"provider-adapter-{agent.agent_id}",
            ProviderTaskRouter([providers[agent.agent_id]]),
        )
        for agent in agents
    }
    problem_runtime, _ = runtime(tmp_path, agents=agents, adapters=adapters)

    result = problem_runtime.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert {provider.tasks[0].task_kind for provider in providers.values()} == {
        "endogenous_problem_framing",
        "problem_candidate_adversarial_review",
        "problem_researchability_assessment",
        "group_agenda_synthesis_and_selection",
    }
    framer_task = providers["problem-framer"].tasks[0]
    assert (
        framer_task.expected_schema["properties"]["problem_candidates"]["items"]
        ["properties"]["scope"]["enum"]
        == ["project://fixture"]
    )
    assert all(
        receipt.provider_audit["status"].startswith("PASS_PROVIDER")
        for receipt in result.execution_receipts
    )
    assert all("events.jsonl" not in str(provider.tasks[0].inputs) for provider in providers.values())


def test_pending_problem_seed_enters_kernel_authorized_coordinated_deliberation(tmp_path):
    problem_runtime, _ = runtime(tmp_path / "problem")
    problem_result = problem_runtime.run_to_candidate()
    seed = problem_result.deliberation_seed
    core_roles = (
        "HYPOTHESIS_GENERATOR",
        "ADVERSARIAL_REVIEWER",
        "REPLICATOR",
        "SYNTHESIZER",
    )
    core_agents = tuple(make_agent(role, index + 10) for index, role in enumerate(core_roles, start=1))
    role_payloads = {
        "HYPOTHESIS_GENERATOR": {
            "hypotheses": ["mechanism-a"],
            "assumptions": ["thresholds remain frozen"],
            "rival_explanations": ["threshold artifact"],
            "falsifiable_predictions": ["family revalidation separates the rivals"],
            "evidence_refs": ["evidence://source"],
            "confidence": 0.7,
        },
        "ADVERSARIAL_REVIEWER": {
            "objections": ["mechanism may be a threshold artifact"],
            "strongest_falsifier": "family-level revalidation",
            "rival_set_coverage": 0.8,
            "evidence_refs": ["evidence://source"],
            "recommended_epistemic_state": "PENDING",
            "confidence": 0.8,
        },
        "REPLICATOR": {
            "replication_outcome": "INCONCLUSIVE",
            "gate_results": {"family_revalidation": False},
            "deviations": ["independent experiment not yet executed"],
            "evidence_refs": ["evidence://source"],
            "confidence": 0.7,
        },
        "SYNTHESIZER": {
            "converged_claims": [],
            "unresolved_conflicts": ["mechanism versus threshold artifact"],
            "minority_positions": ["scope-local effect"],
            "evidence_refs": ["evidence://source"],
            "uncertainties": ["independent family revalidation pending"],
        },
    }
    role_adapters = {
        agent.agent_id: ScriptedProblemAdapter(agent, [role_payloads[agent.role]])
        for agent in core_agents
    }
    coordinator = make_agent("COORDINATOR", 20)
    coordination_payloads = [
        {
            "route_action": "RUN_ROLE",
            "target_role": "HYPOTHESIS_GENERATOR",
            "rationale": "Begin the selected problem.",
            "unresolved_questions": [seed.objective],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": ["evidence://source"],
            "expected_cbit_gain": 0.6,
            "stop_condition": "Stop after bounded synthesis.",
        },
        {
            "route_action": "RUN_ROLE",
            "target_role": "ADVERSARIAL_REVIEWER",
            "rationale": "Challenge the generated mechanism.",
            "unresolved_questions": [seed.objective],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": ["evidence://source"],
            "expected_cbit_gain": 0.5,
            "stop_condition": "Stop after bounded synthesis.",
        },
        {
            "route_action": "RUN_ROLE",
            "target_role": "REPLICATOR",
            "rationale": "Independently assess the evidence.",
            "unresolved_questions": [seed.objective],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": ["evidence://source"],
            "expected_cbit_gain": 0.5,
            "stop_condition": "Stop after bounded synthesis.",
        },
        {
            "route_action": "PROCEED_TO_SYNTHESIS",
            "target_role": "SYNTHESIZER",
            "rationale": "All independent formal roles are present.",
            "unresolved_questions": [seed.objective],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": ["evidence://source"],
            "expected_cbit_gain": 0.4,
            "stop_condition": "Stop after bounded synthesis.",
        },
        {
            "route_action": "FINALIZE_CANDIDATE",
            "target_role": "NONE",
            "rationale": "A bounded synthesis is available.",
            "unresolved_questions": [seed.objective],
            "evidence_gaps": [],
            "conflict_message_refs": [],
            "evidence_refs": ["evidence://source"],
            "expected_cbit_gain": 0.0,
            "stop_condition": "Bounded synthesis is available.",
        },
    ]
    coordinator_adapter = ScriptedProblemAdapter(coordinator, coordination_payloads)
    coordination_runtime = CognitiveCoordinationRuntime(
        coordinator=coordinator,
        adapter=coordinator_adapter,
        workspace_root=tmp_path / "coordinator-private",
    )

    deliberation = CognitiveDeliberationSession.from_deliberation_seed(
        seed=seed,
        session_id="seeded-deliberation",
        frozen_gate_refs=("gate://generated-problem",),
        agents=core_agents,
        adapters=role_adapters,
        workspace_root=tmp_path / "role-private",
        kernel_authorization_ref="kernel-authorization://seeded-deliberation",
        coordination_runtime=coordination_runtime,
    )
    result = deliberation.run_to_candidate()

    assert result.stage == "CANDIDATE"
    assert deliberation.objective == seed.objective
    assert coordinator_adapter.contexts[0].objective == seed.objective
    assert coordinator_adapter.contexts[0].evidence_payload["source_problem_id"] == seed.source_problem_id
    assert result.candidate_state == "PENDING_EPISTEMIC_REVIEW"

    with pytest.raises(ValueError, match="deliberation_seed_state_must_be_pending_agenda_review"):
        replace(seed, candidate_state="ACCEPTED")


def test_problem_framer_must_emit_plural_evidence_bounded_candidates(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    invalid = framer_payload()
    invalid["problem_candidates"] = invalid["problem_candidates"][:1]
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-framer"] = ScriptedProblemAdapter(agents[0], [invalid])
    problem_runtime, _ = runtime(tmp_path, agents=agents, adapters=adapters)

    result = problem_runtime.execute_current()

    assert result.stage == "BLOCKED"
    assert "problem_candidate_plurality_required" in result.execution_receipts[-1].errors
    assert (
        adapters["problem-framer"].workspaces[0]
        .history("problem-framer")[-1]["payload"]["quarantined_provider_support_receipt"]
        ["problem_candidates"][0]["problem_id"]
        == "problem-negative-control-mechanism"
    )


def test_group_can_stop_without_forming_seed_and_low_priority_selection_is_blocked(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    stop = synthesizer_payload()
    stop.update(
        {
            "decision": "STOP",
            "selected_problem_id": "NONE",
            "selection_rationale": "No candidate should be activated under the current evidence budget.",
            "rejected_problem_ids": [
                "problem-negative-control-mechanism",
                "problem-local-rule-transfer",
            ],
            "expected_cbit_gain": 0.0,
        }
    )
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["agenda-synthesizer"] = ScriptedProblemAdapter(agents[3], [stop])
    problem_runtime, _ = runtime(tmp_path / "stop", agents=agents, adapters=adapters)

    stopped = problem_runtime.run_to_candidate()

    assert stopped.stage == "CANDIDATE"
    assert stopped.candidate_state == "NO_AGENDA_CANDIDATE"
    assert stopped.agenda_selection.decision == "STOP"
    assert stopped.deliberation_seed is None

    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    problem_runtime, _ = runtime(
        tmp_path / "priority",
        agents=agents,
        adapters=adapters,
        minimum_priority=0.95,
    )
    problem_runtime.execute_current()
    problem_runtime.execute_current()
    problem_runtime.execute_current()

    blocked = problem_runtime.execute_current()

    assert blocked.stage == "BLOCKED"
    assert "agenda_selected_candidate_below_runtime_priority_gate" in blocked.execution_receipts[-1].errors


def test_invalidated_evidence_is_removed_from_admission_boundary(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    payload = framer_payload()
    payload["problem_candidates"][0]["evidence_refs"] = ["evidence://invalidated"]
    payload["evidence_refs"] = ["evidence://valid"]
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-framer"] = ScriptedProblemAdapter(agents[0], [payload])
    problem_runtime, _ = runtime(
        tmp_path,
        agents=agents,
        adapters=adapters,
        evidence_refs=("evidence://valid", "evidence://invalidated"),
        invalidated_evidence_refs=("evidence://invalidated",),
    )

    blocked = problem_runtime.execute_current()

    assert blocked.stage == "BLOCKED"
    assert "problem_candidate_evidence_ref_not_admitted:evidence://invalidated" in blocked.execution_receipts[-1].errors

    with pytest.raises(ValueError, match="problem_runtime_no_valid_evidence_after_invalidation"):
        runtime(
            tmp_path / "all-invalid",
            evidence_refs=("evidence://invalidated",),
            invalidated_evidence_refs=("evidence://invalidated",),
        )


def test_unknown_review_id_and_unresearchable_selection_block_closed(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    bad_review = critic_payload()
    bad_review["surviving_problem_ids"] = ["problem-not-generated"]
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-critic"] = ScriptedProblemAdapter(agents[1], [bad_review])
    problem_runtime, _ = runtime(tmp_path / "review", agents=agents, adapters=adapters)
    problem_runtime.execute_current()

    blocked = problem_runtime.execute_current()

    assert blocked.stage == "BLOCKED"
    assert "problem_review_unknown_candidate_id:problem-not-generated" in blocked.execution_receipts[-1].errors

    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    bad_assessment = assessor_payload()
    bad_assessment["researchable_problem_ids"] = ["problem-local-rule-transfer"]
    adapters["researchability-assessor"] = ScriptedProblemAdapter(agents[2], [bad_assessment])
    adapters["agenda-synthesizer"] = ScriptedProblemAdapter(
        agents[3],
        [synthesizer_payload("problem-negative-control-mechanism")],
    )
    problem_runtime, _ = runtime(tmp_path / "selection", agents=agents, adapters=adapters)
    problem_runtime.execute_current()
    problem_runtime.execute_current()
    problem_runtime.execute_current()

    blocked = problem_runtime.execute_current()

    assert blocked.stage == "BLOCKED"
    assert "agenda_selection_not_researchable" in blocked.execution_receipts[-1].errors


def test_duplicate_review_and_harnessless_researchable_candidate_are_blocked(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    duplicate_review = critic_payload()
    duplicate_review["candidate_reviews"].append(dict(duplicate_review["candidate_reviews"][0]))
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-critic"] = ScriptedProblemAdapter(agents[1], [duplicate_review])
    problem_runtime, _ = runtime(tmp_path / "duplicate", agents=agents, adapters=adapters)
    problem_runtime.execute_current()

    blocked = problem_runtime.execute_current()

    assert "problem_review_candidate_ids_not_unique" in blocked.execution_receipts[-1].errors

    harnessless = assessor_payload()
    harnessless["assessments"][0]["required_harnesses"] = []
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["researchability-assessor"] = ScriptedProblemAdapter(agents[2], [harnessless])
    problem_runtime, _ = runtime(tmp_path / "harnessless", agents=agents, adapters=adapters)
    problem_runtime.execute_current()
    problem_runtime.execute_current()

    blocked = problem_runtime.execute_current()

    assert (
        "researchable_candidate_harness_required:problem-negative-control-mechanism"
        in blocked.execution_receipts[-1].errors
    )


def test_problem_runtime_blocks_authority_claim_and_unadmitted_nested_evidence(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    authority = framer_payload()
    authority["execution_authorized"] = True
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-framer"] = ScriptedProblemAdapter(agents[0], [authority])
    problem_runtime, _ = runtime(tmp_path / "authority", agents=agents, adapters=adapters)

    blocked = problem_runtime.execute_current()

    assert "problem_agent_final_state_authority_forbidden" in blocked.execution_receipts[-1].errors

    outside = framer_payload()
    outside["problem_candidates"][0]["evidence_refs"] = ["evidence://outside"]
    adapters["problem-framer"] = ScriptedProblemAdapter(agents[0], [outside])
    problem_runtime, _ = runtime(tmp_path / "evidence", agents=agents, adapters=adapters)

    blocked = problem_runtime.execute_current()

    assert "problem_candidate_evidence_ref_not_admitted:evidence://outside" in blocked.execution_receipts[-1].errors


def test_problem_runtime_retry_preserves_provider_failure_and_public_replay_detects_tampering(tmp_path):
    agents = tuple(make_agent(role, index) for index, role in enumerate(PROBLEM_ROLES, start=1))
    unavailable = AgentAdapterResult(
        status="PROVIDER_UNAVAILABLE",
        provider_support_receipt=None,
        provider_id=agents[0].descriptor.provider_id,
        model_id=agents[0].model_id,
        invocation_receipt_ref="provider-receipt://unavailable",
        validation_errors=("provider_unavailable",),
    )
    adapters = {agent.agent_id: ScriptedProblemAdapter(agent) for agent in agents}
    adapters["problem-framer"] = ScriptedProblemAdapter(agents[0], [unavailable, framer_payload()])
    problem_runtime, _ = runtime(tmp_path, agents=agents, adapters=adapters)

    blocked = problem_runtime.execute_current()
    recovered = problem_runtime.retry_blocked()

    assert blocked.stage == "BLOCKED"
    assert recovered.stage == "PROBLEM_REVIEW"
    assert [receipt.status for receipt in recovered.execution_receipts] == ["BLOCKED", "COMPLETED"]

    events_path = problem_runtime.public_store_path / "events.jsonl"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    events[1]["payload"]["next_stage"] = "CANDIDATE"
    events_path.write_text("\n".join(json.dumps(event, sort_keys=True) for event in events) + "\n", encoding="utf-8")

    verification = problem_runtime.verify_replay()

    assert verification["valid"] is False
    assert "event_hash_mismatch:1" in verification["failures"]
