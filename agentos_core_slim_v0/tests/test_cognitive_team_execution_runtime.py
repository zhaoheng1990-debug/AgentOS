import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    ARM_BEST_MEMBER,
    ARM_DYNAMIC_TEAM,
    ARM_FIXED_TEAM,
    AgentDescriptor,
    AgentRegistry,
    AgentRoleRequirement,
    CreditLedger,
    FrozenFindingTrialHarness,
    OrganizationLearningEvaluator,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    TrialFindingCatalogEntry,
    TrialFindingTruth,
)
from agentos_runtime import (
    AgentAdapterResult,
    CognitiveAgent,
    CognitiveCoordinationRuntime,
    CognitiveExecutionTrialSpec,
    CognitiveTeamExecutionRuntime,
    CognitiveTeamFormationRuntime,
    CognitiveOrganizationAblationRuntime,
    DeliberationSeed,
    OrganizationExperimentPlan,
    organization_records_from_ablation_smoke_result,
    standard_role_contract,
)


SCOPE = "project://execution-fixture"
EVIDENCE = ("evidence://execution-a", "evidence://execution-b")
ROLES = (
    ("HYPOTHESIS_GENERATOR", "generate"),
    ("ADVERSARIAL_REVIEWER", "challenge"),
    ("REPLICATOR", "replicate"),
    ("SYNTHESIZER", "synthesize"),
)
CATALOG = (
    TrialFindingCatalogEntry("F1", "The narrow local finding survived the frozen check."),
    TrialFindingCatalogEntry("F2", "The broad causal promotion is supported."),
    TrialFindingCatalogEntry("F3", "The alternate mechanism is still unresolved."),
)
TRUTHS = (
    TrialFindingTruth("F1", "SUPPORTED"),
    TrialFindingTruth("F2", "REJECTED"),
    TrialFindingTruth("F3", "UNRESOLVED"),
)


class ScriptedProvider:
    def __init__(self, provider_id, model_id, task_kinds, result_factory):
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=tuple(task_kinds),
            max_timeout_seconds=120,
        )
        self.result_factory = result_factory
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        return {
            "result": self.result_factory(task),
            "usage": {"total_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


class ScriptedAgentAdapter:
    def __init__(self, descriptor):
        self.adapter_id = f"adapter-{descriptor.agent_id}"
        self.descriptor = descriptor
        self.contexts = []
        self.work_orders = []

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        assert cognitive_agent.agent_id == self.descriptor.agent_id
        self.contexts.append(context_view)
        self.work_orders.append(work_order)
        payload = role_payload(cognitive_agent.role)
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.descriptor.provider_id,
            model_id=self.descriptor.model_id,
            invocation_receipt_ref=f"provider-receipt://{work_order.work_order_id}",
        )


class ScriptedCoordinatorAdapter:
    def __init__(self, coordinator, payloads):
        self.adapter_id = f"adapter-{coordinator.agent_id}"
        self.coordinator = coordinator
        self.payloads = list(payloads)

    def invoke(self, cognitive_agent, work_order, context_view, private_workspace):
        payload = self.payloads.pop(0)
        return AgentAdapterResult(
            status="COMPLETED",
            provider_support_receipt=payload,
            provider_id=self.coordinator.descriptor.provider_id,
            model_id=self.coordinator.model_id,
            invocation_receipt_ref=f"provider-receipt://{work_order.work_order_id}",
        )


def descriptor(agent_id, role, capability, provider_id, model_id="model-v1"):
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=(capability, "source_read"),
        runner_id=f"runner-{agent_id}",
        harness_id="execution-harness",
        provider_id=provider_id,
        model_id=model_id,
        context_isolation_key=f"context-{agent_id}",
        allowed_evidence_scopes=(SCOPE,),
    )


def make_registry():
    registry = AgentRegistry()
    registry.register(descriptor("framer-a", "PROBLEM_FRAMER", "frame", "baseline-a"))
    registry.register(descriptor("framer-b", "PROBLEM_FRAMER", "frame", "baseline-b"))
    for index, (role, capability) in enumerate(ROLES):
        registry.register(descriptor(f"fixed-{index}", role, capability, "provider-fixed"))
        registry.register(
            descriptor(
                f"dynamic-{index}",
                role,
                capability,
                "provider-dynamic-a" if index % 2 == 0 else "provider-dynamic-b",
            )
        )
    return registry


def seed():
    return DeliberationSeed.create(
        seed_id="execution-seed",
        source_problem_id="execution-problem",
        objective="Determine which frozen findings are supported, rejected, or unresolved.",
        research_object="bounded_finding_classification",
        project_scope=SCOPE,
        evidence_refs=EVIDENCE,
        rival_explanations=("broad causal promotion", "scope-local effect"),
        operationalization="Classify every finding under the frozen source protocol.",
        falsifier="The held-out Harness contradicts the classification.",
        required_harnesses=("frozen-finding-harness",),
        unresolved_conflicts=("F3 remains open.",),
        expected_cbit_gain=0.8,
        agenda_selection_receipt_ref="agenda://execution",
    )


def baseline_result(question):
    def result(task):
        return {
            "problem_id": f"problem-{task.inputs['blind_member_id']}",
            "question": question,
            "research_object": "bounded_finding_classification",
            "scope": SCOPE,
            "triggering_anomaly": "The broad claim exceeds the frozen local evidence.",
            "rival_explanations": ["broad causal promotion", "scope-local effect"],
            "falsifier": "The held-out Harness contradicts the classification.",
            "required_harnesses": ["frozen-finding-harness"],
            "expected_cbit_gain": 0.7,
            "evidence_refs": list(EVIDENCE),
        }

    return result


def formation_proposal(task):
    return {
        "selected_agent_ids": [f"dynamic-{index}" for index in range(4)],
        "role_coverage": {role: f"dynamic-{index}" for index, (role, _) in enumerate(ROLES)},
        "formation_rationale": "Choose a role-complete, context-isolated, two-provider team.",
        "expected_cbit_gain": 0.8,
        "independence_risks": ["Two provider families are reused."],
        "negative_transfer_risks": ["Historical performance is only advisory."],
        "evidence_refs": list(EVIDENCE),
    }


def semantic_assessment(task):
    mechanical = task.inputs["harness_owned_metrics"]
    return {
        "blind_arm_id": task.inputs["blind_arm_id"],
        "quality_score": mechanical["observed_cbit_gain"],
        **mechanical,
        "evidence_refs": list(EVIDENCE),
    }


def candidate(state="correct"):
    if state == "correct":
        groups = (["F1"], ["F2"], ["F3"])
    elif state == "partial":
        groups = (["F1", "F3"], ["F2"], [])
    else:
        groups = (["F1", "F2", "F3"], [], [])
    return {
        "answer": f"Bounded candidate output: {state}.",
        "supported_finding_ids": groups[0],
        "rejected_finding_ids": groups[1],
        "unresolved_finding_ids": groups[2],
        "rival_explanations": ["The alternate mechanism remains possible."],
        "falsifier": "A held-out intervention reverses F1.",
        "evidence_refs": list(EVIDENCE),
        "uncertainties": ["Cross-scope transfer is unknown."],
    }


def role_payload(role):
    if role == "HYPOTHESIS_GENERATOR":
        return {
            "hypotheses": ["F1 is local; F2 may be overbroad."],
            "assumptions": ["Frozen source hashes are valid."],
            "rival_explanations": ["F3 remains open."],
            "falsifiable_predictions": ["The Harness rejects F2."],
            "evidence_refs": list(EVIDENCE),
            "confidence": 0.7,
        }
    if role == "ADVERSARIAL_REVIEWER":
        return {
            "objections": ["F2 exceeds the evidence."],
            "strongest_falsifier": "The held-out Harness rejects F2.",
            "rival_set_coverage": 0.8,
            "evidence_refs": list(EVIDENCE),
            "recommended_epistemic_state": "PENDING",
            "confidence": 0.8,
        }
    if role == "REPLICATOR":
        return {
            "replication_outcome": "INCONCLUSIVE",
            "gate_results": {"F1": True, "F2": False},
            "deviations": ["F3 lacks a discriminating intervention."],
            "evidence_refs": list(EVIDENCE),
            "confidence": 0.75,
        }
    return {
        "converged_claims": ["F1 survives locally."],
        "unresolved_conflicts": ["F3 remains unresolved."],
        "minority_positions": ["F2 might hold under another scope."],
        "evidence_refs": list(EVIDENCE),
        "uncertainties": ["No cross-scope promotion."],
    }


def make_formation_runtime(tmp_path, registry=None, budget=None):
    registry = registry or make_registry()
    baseline_a = ScriptedProvider(
        "baseline-a", "model-v1", ("independent_problem_baseline_generation",), baseline_result("Question A?")
    )
    baseline_b = ScriptedProvider(
        "baseline-b", "model-v1", ("independent_problem_baseline_generation",), baseline_result("Question B?")
    )
    formation = ScriptedProvider(
        "formation-provider", "formation-model", ("cognitive_team_formation_proposal",), formation_proposal
    )
    assessor = ScriptedProvider(
        "assessment-provider", "assessment-model", ("team_trial_semantic_assessment",), semantic_assessment
    )
    runtime = CognitiveTeamFormationRuntime(
        runtime_id="execution-formation",
        seed=seed(),
        registry=registry,
        baseline_agent_ids=("framer-a", "framer-b"),
        baseline_routers={
            "framer-a": ProviderTaskRouter([baseline_a]),
            "framer-b": ProviderTaskRouter([baseline_b]),
        },
        formation_router=ProviderTaskRouter([formation]),
        trial_assessment_router=ProviderTaskRouter([assessor]),
        required_roles=tuple(AgentRoleRequirement(role, (capability,)) for role, capability in ROLES),
        fixed_team_id="fixed-team",
        fixed_team_agent_ids=tuple(f"fixed-{index}" for index in range(4)),
        workspace_root=tmp_path / "formation",
        evidence_payload={"public_source": "frozen fixture"},
        admitted_evidence_refs=EVIDENCE,
        minimum_provider_diversity=2,
    )
    runtime.generate_independent_baselines()
    runtime.propose_team(team_id="dynamic-team")
    decision = runtime.authorize_team(
        kernel_authorization_ref="kernel://formation",
        budget=budget or {"max_provider_calls_per_arm": 12, "max_retries_per_stage": 0},
    )
    return runtime, decision, assessor


def make_trial_spec(decision):
    return CognitiveExecutionTrialSpec(
        trial_id="execution-trial",
        objective=seed().objective,
        project_scope=SCOPE,
        evidence_refs=EVIDENCE,
        evidence_payload={
            "public_source": "frozen fixture",
            "finding_catalog": [item.as_dict() for item in CATALOG],
        },
        finding_catalog=CATALOG,
        frozen_gate_refs=("gate://execution",),
        stop_conditions=("all findings classified", "provider budget exhausted"),
        budget=decision.budget,
        kernel_authorization_ref="kernel://execution-trial",
    )


def make_execution_runtime(tmp_path, *, formation=None, registry=None, budget=None, coordinator_factory=None):
    registry = registry or make_registry()
    formation, decision, assessor = (
        make_formation_runtime(tmp_path, registry, budget) if formation is None else formation
    )
    team_adapters = {
        agent_id: ScriptedAgentAdapter(registry.get(agent_id))
        for agent_id in (
            *(f"fixed-{index}" for index in range(4)),
            *(f"dynamic-{index}" for index in range(4)),
        )
    }
    solo_provider = ScriptedProvider(
        "baseline-a", "model-v1", ("solo_cognitive_trial",), lambda task: candidate("partial")
    )
    normalizers = {}
    for agent_id, state in (("fixed-3", "wrong"), ("dynamic-3", "correct")):
        descriptor_item = registry.get(agent_id)
        provider = ScriptedProvider(
            descriptor_item.provider_id,
            descriptor_item.model_id,
            ("team_trial_output_normalization",),
            lambda task, state=state: candidate(state),
        )
        normalizers[agent_id] = ProviderTaskRouter([provider])
    runtime = CognitiveTeamExecutionRuntime(
        execution_id="execution-runtime",
        formation_runtime=formation,
        registry=registry,
        trial_spec=make_trial_spec(decision),
        team_adapters=team_adapters,
        solo_routers={"framer-a": ProviderTaskRouter([solo_provider])},
        normalization_routers=normalizers,
        trial_harness=FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS),
        workspace_root=tmp_path / "execution",
        coordination_runtime_factory=coordinator_factory,
    )
    return runtime, team_adapters, solo_provider, normalizers, assessor


def coordination_payload(action, target):
    return {
        "route_action": action,
        "target_role": target,
        "rationale": "Use the same bounded coordination protocol in each team arm.",
        "unresolved_questions": ["Which findings survive?"],
        "evidence_gaps": [],
        "conflict_message_refs": [],
        "evidence_refs": list(EVIDENCE),
        "expected_cbit_gain": 0.4,
        "stop_condition": "Stop after bounded synthesis.",
    }


def coordinator_factory(arm, workspace_root):
    descriptor_item = AgentDescriptor(
        agent_id=f"coordinator-{arm.lower()}",
        role="COORDINATOR",
        capabilities=("route_proposal", "formal_receipt_read"),
        runner_id="coordinator-runner",
        harness_id="coordinator-harness",
        provider_id="coordinator-provider",
        model_id="coordinator-model",
        context_isolation_key=f"coordinator-context-{arm.lower()}",
        allowed_evidence_scopes=(SCOPE,),
    )
    agent = CognitiveAgent(
        descriptor_item,
        standard_role_contract("COORDINATOR"),
        model_id="coordinator-model",
        private_memory_namespace=f"coordinator-memory-{arm.lower()}",
        harness_capabilities=("formal_receipt_read", "route_proposal"),
        credit_subject_id=f"credit-coordinator-{arm.lower()}",
    )
    payloads = [
        coordination_payload("RUN_ROLE", "HYPOTHESIS_GENERATOR"),
        coordination_payload("RUN_ROLE", "ADVERSARIAL_REVIEWER"),
        coordination_payload("RUN_ROLE", "REPLICATOR"),
        coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER"),
        coordination_payload("FINALIZE_CANDIDATE", "NONE"),
    ]
    return CognitiveCoordinationRuntime(
        coordinator=agent,
        adapter=ScriptedCoordinatorAdapter(agent, payloads),
        workspace_root=workspace_root,
        max_cycles=5,
        max_role_executions_per_role=1,
    )


def ablation_coordinator_factory(protocol_id, workspace_root, omitted_roles, authorization_ref):
    descriptor_item = AgentDescriptor(
        agent_id=f"coordinator-{protocol_id.lower()}",
        role="COORDINATOR",
        capabilities=("route_proposal", "formal_receipt_read"),
        runner_id="coordinator-runner",
        harness_id="coordinator-harness",
        provider_id="coordinator-provider",
        model_id="coordinator-model",
        context_isolation_key=f"coordinator-context-{protocol_id.lower()}",
        allowed_evidence_scopes=(SCOPE,),
    )
    agent = CognitiveAgent(
        descriptor_item,
        standard_role_contract("COORDINATOR"),
        model_id="coordinator-model",
        private_memory_namespace=f"coordinator-memory-{protocol_id.lower()}",
        harness_capabilities=("formal_receipt_read", "route_proposal"),
        credit_subject_id=f"credit-coordinator-{protocol_id.lower()}",
    )
    role_sequence = ["HYPOTHESIS_GENERATOR"]
    if "ADVERSARIAL_REVIEWER" not in omitted_roles:
        role_sequence.append("ADVERSARIAL_REVIEWER")
    if "REPLICATOR" not in omitted_roles:
        role_sequence.append("REPLICATOR")
    payloads = [coordination_payload("RUN_ROLE", role) for role in role_sequence]
    if "SYNTHESIZER" not in omitted_roles:
        payloads.append(coordination_payload("PROCEED_TO_SYNTHESIS", "SYNTHESIZER"))
    payloads.append(coordination_payload("FINALIZE_CANDIDATE", "NONE"))
    return CognitiveCoordinationRuntime(
        coordinator=agent,
        adapter=ScriptedCoordinatorAdapter(agent, payloads),
        workspace_root=workspace_root,
        max_cycles=len(payloads),
        max_role_executions_per_role=1,
        authorized_omitted_roles=omitted_roles,
        ablation_authorization_ref=(authorization_ref if omitted_roles else ""),
    )


def authorized_ablation_plan(*, max_trial_runs=4):
    return OrganizationExperimentPlan(
        plan_id="experiment-ablation",
        context_key="context://execution-fixture/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
        selected_variants=(
            "DYNAMIC_NO_COORDINATOR",
            "DYNAMIC_NO_REVIEWER",
            "DYNAMIC_NO_REPLICATOR",
        ),
        rationale_refs=("organization-policy://fixture", "organization-diagnosis://fixture"),
        policy_ref="organization-policy://fixture",
        budget={"max_trial_runs": max_trial_runs, "max_provider_calls_per_run": 20},
        budget_hash="a" * 64,
        kernel_authorization_ref="kernel://organization-ablation/fixture",
        created_at="2026-07-19T00:00:00+00:00",
        plan_hash="b" * 64,
        candidate_state="AUTHORIZED_FOR_EXPERIMENT",
        execution_authorized=True,
    )


def make_ablation_runtime(tmp_path):
    base, adapters, _solo, normalizers, assessor = make_execution_runtime(tmp_path / "base")
    runtime = CognitiveOrganizationAblationRuntime(
        runtime_id="organization-ablation",
        experiment_plan=authorized_ablation_plan(),
        formation_runtime=base.formation_runtime,
        registry=base.registry,
        trial_spec=base.trial_spec,
        team_adapters=adapters,
        normalization_router=normalizers["dynamic-3"],
        semantic_assessment_router=ProviderTaskRouter([assessor]),
        trial_harness=base.trial_harness,
        workspace_root=tmp_path / "ablation",
        coordination_runtime_factory=ablation_coordinator_factory,
    )
    return runtime, adapters, assessor


def test_authorized_matched_ablation_executes_one_component_omission_per_protocol(tmp_path):
    runtime, adapters, _assessor = make_ablation_runtime(tmp_path)

    snapshot = runtime.execute_protocols()

    by_protocol = {item.protocol_id: item for item in snapshot.protocol_results}
    assert set(by_protocol) == {
        "DYNAMIC_TEAM",
        "DYNAMIC_NO_COORDINATOR",
        "DYNAMIC_NO_REVIEWER",
        "DYNAMIC_NO_REPLICATOR",
    }
    assert len(by_protocol["DYNAMIC_TEAM"].formal_messages) == 4
    assert len(by_protocol["DYNAMIC_NO_COORDINATOR"].formal_messages) == 4
    assert len(by_protocol["DYNAMIC_NO_REVIEWER"].formal_messages) == 3
    assert len(by_protocol["DYNAMIC_NO_REPLICATOR"].formal_messages) == 3
    assert by_protocol["DYNAMIC_NO_COORDINATOR"].coordination_receipt_count == 0
    assert by_protocol["DYNAMIC_NO_REVIEWER"].omitted_components == ("ADVERSARIAL_REVIEWER",)
    assert by_protocol["DYNAMIC_NO_REPLICATOR"].omitted_components == ("REPLICATOR",)
    assert len(adapters["dynamic-1"].contexts) == 3
    assert len(adapters["dynamic-2"].contexts) == 3
    assert all(item["valid"] for item in runtime.verify_protocol_replays().values())


def test_authorized_no_synthesizer_uses_generator_projection_without_hidden_synthesis(tmp_path):
    base, adapters, _solo, normalizers, assessor = make_execution_runtime(tmp_path / "base")
    generator = base.registry.get("dynamic-0")
    projector = ScriptedProvider(
        generator.provider_id,
        generator.model_id,
        ("team_trial_output_normalization",),
        lambda task: candidate("partial"),
    )
    plan = OrganizationExperimentPlan(
        plan_id="experiment-no-synth",
        context_key="context://execution-fixture/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
        selected_variants=("DYNAMIC_NO_SYNTHESIZER",),
        rationale_refs=("organization-policy://fixture", "organization-diagnosis://fixture"),
        policy_ref="organization-policy://fixture",
        budget={"max_trial_runs": 2, "max_provider_calls_per_run": 20},
        budget_hash="c" * 64,
        kernel_authorization_ref="kernel://organization-ablation/no-synth",
        created_at="2026-07-19T00:00:00+00:00",
        plan_hash="d" * 64,
        candidate_state="AUTHORIZED_FOR_EXPERIMENT",
        execution_authorized=True,
    )
    runtime = CognitiveOrganizationAblationRuntime(
        runtime_id="organization-ablation-no-synth",
        experiment_plan=plan,
        formation_runtime=base.formation_runtime,
        registry=base.registry,
        trial_spec=base.trial_spec,
        team_adapters=adapters,
        normalization_router=normalizers["dynamic-3"],
        unsynthesized_normalization_router=ProviderTaskRouter([projector]),
        semantic_assessment_router=ProviderTaskRouter([assessor]),
        trial_harness=base.trial_harness,
        workspace_root=tmp_path / "ablation",
        coordination_runtime_factory=ablation_coordinator_factory,
    )

    snapshot = runtime.execute_protocols()
    no_synth = {item.protocol_id: item for item in snapshot.protocol_results}[
        "DYNAMIC_NO_SYNTHESIZER"
    ]

    assert no_synth.omitted_components == ("SYNTHESIZER",)
    assert "dynamic-3" not in no_synth.agent_ids
    assert [item["message_type"] for item in no_synth.formal_messages] == [
        "HYPOTHESIS_PROPOSAL",
        "ADVERSARIAL_REVIEW",
        "REPLICATION_REPORT",
    ]
    assert len(projector.tasks) == 1
    assert [item["message_type"] for item in projector.tasks[0].inputs["formal_messages"]] == [
        "HYPOTHESIS_PROPOSAL"
    ]
    assert projector.tasks[0].inputs["projection_mode"] == "UNSYNTHESIZED_GENERATOR_PROPOSAL"
    assert projector.tasks[0].expected_schema["properties"]["falsifier"]["minLength"] == 1


def test_ablation_assessment_is_blind_and_harness_owned(tmp_path):
    runtime, _adapters, assessor = make_ablation_runtime(tmp_path)
    runtime.execute_protocols()

    snapshot = runtime.evaluate_protocols()

    assert len(snapshot.observations) == 4
    assert all(item.harness_receipt.harness_owned for item in snapshot.observations)
    serialized = json.dumps([task.inputs for task in assessor.tasks], sort_keys=True)
    assert "DYNAMIC_NO_" not in serialized
    assert '"protocol_id"' not in serialized
    assert '"agent_ids"' not in serialized
    assert "expected_state" not in serialized
    quality_contract = assessor.tasks[0].expected_schema["properties"]["quality_score"]
    assert quality_contract == {"type": "number", "minimum": 0.0, "maximum": 1.0}
    assert "never use a 0-100 scale" in assessor.tasks[0].objective
    assert runtime.verify_replay()["valid"]


def test_ablation_bridge_rejects_budget_that_omits_full_dynamic_baseline(tmp_path):
    base, adapters, _solo, normalizers, assessor = make_execution_runtime(tmp_path / "base")

    with pytest.raises(ValueError, match="ablation_budget_must_cover_baseline_and_variants"):
        CognitiveOrganizationAblationRuntime(
            runtime_id="underbudgeted-ablation",
            experiment_plan=authorized_ablation_plan(max_trial_runs=3),
            formation_runtime=base.formation_runtime,
            registry=base.registry,
            trial_spec=base.trial_spec,
            team_adapters=adapters,
            normalization_router=normalizers["dynamic-3"],
            semantic_assessment_router=ProviderTaskRouter([assessor]),
            trial_harness=base.trial_harness,
            workspace_root=tmp_path / "underbudgeted",
            coordination_runtime_factory=ablation_coordinator_factory,
        )


def test_ablation_evidence_aliases_are_mechanically_bounded(tmp_path):
    runtime, _adapters, _assessor = make_ablation_runtime(tmp_path)
    aliased = candidate("correct")
    aliased["evidence_refs"] = ["E1"]
    unknown = candidate("correct")
    unknown["evidence_refs"] = ["E999"]

    assert runtime._candidate_errors(aliased) == []
    assert "organization_ablation_candidate_evidence_invalid" in runtime._candidate_errors(unknown)
    mechanical = {
        "observed_cbit_gain": 1.0,
        "errors_exposed": 1,
        "errors_corrected": 1,
        "negative_transfer_opportunities": 2,
        "negative_transfer_intercepts": 2,
        "normalized_cost": 0.5,
        "convergence_steps": 10,
    }
    assessment = {
        "blind_arm_id": "blind-fixture",
        "quality_score": 0.8,
        **mechanical,
        "evidence_refs": ["E1"],
    }
    assert runtime._assessment_errors(assessment, "blind-fixture", mechanical) == []
    assessment["evidence_refs"] = ["E999"]
    assert "organization_ablation_assessment_evidence_mismatch" in runtime._assessment_errors(
        assessment, "blind-fixture", mechanical
    )


def test_team_execution_evidence_aliases_match_ablation_contract(tmp_path):
    runtime, _adapters, _solo, _normalizers, _assessor = make_execution_runtime(tmp_path)
    aliased = candidate("correct")
    aliased["evidence_refs"] = ["E1"]
    unknown = candidate("correct")
    unknown["evidence_refs"] = ["E999"]

    assert runtime._candidate_errors(aliased) == []
    assert "execution_candidate_unadmitted_evidence_ref" in runtime._candidate_errors(unknown)
    assert runtime._provider_trial_inputs()["evidence_aliases"][0] == {
        "alias": "E1",
        "evidence_ref": EVIDENCE[0],
    }


def ablation_smoke_payload(snapshot, bundle_id):
    return {
        "status": "PASS",
        "bundle_id": bundle_id,
        "selected_variants": [
            "DYNAMIC_NO_COORDINATOR",
            "DYNAMIC_NO_REVIEWER",
            "DYNAMIC_NO_REPLICATOR",
        ],
        "gates": {
            "authorized_protocols_completed": True,
            "all_protocol_replays_valid": True,
            "ablation_replay_valid": True,
            "evidence_surface_equal": True,
            "harness_owns_observed_cbit": True,
            "hidden_truth_absent_from_provider_inputs": True,
            "provider_budget_respected": True,
            "semantic_assessment_blinded": True,
            "one_component_omitted_per_variant": True,
        },
        "ablation_observations": [item.as_dict() for item in snapshot.observations],
    }


def test_two_independent_ablation_bundles_feed_identifiable_matched_pairs(tmp_path):
    runtime, _adapters, _assessor = make_ablation_runtime(tmp_path)
    runtime.execute_protocols()
    snapshot = runtime.evaluate_protocols()
    records = []
    for index in (1, 2):
        records.extend(
            organization_records_from_ablation_smoke_result(
                ablation_smoke_payload(snapshot, f"bundle-{index}"),
                context_key="context://execution-fixture/finding-classification",
                evidence_tier="SCRIPTED_FIXTURE",
                trial_group_id=f"trial-{index}",
            )
        )

    report = OrganizationLearningEvaluator(minimum_repeated_trials=2).attribute(
        tuple(records),
        context_key="context://execution-fixture/finding-classification",
        evidence_tier="SCRIPTED_FIXTURE",
    )
    by_component = {item.component_id: item for item in report.components}

    assert by_component["COORDINATOR"].identifiability == "IDENTIFIED_MATCHED_ABLATION"
    assert by_component["ADVERSARIAL_REVIEWER"].matched_pair_count == 2
    assert by_component["REPLICATOR"].matched_pair_count == 2
    assert by_component["SYNTHESIZER"].identifiability == "NOT_IDENTIFIABLE"


def test_tampered_ablation_protocol_blocks_harness_evaluation(tmp_path):
    runtime, _adapters, _assessor = make_ablation_runtime(tmp_path)
    runtime.execute_protocols()
    protocol_path = next(iter(runtime._protocol_stores.values())).events_path
    events = protocol_path.read_text(encoding="utf-8").splitlines()
    event = json.loads(events[0])
    event["payload"]["kernel_authorization_ref"] = "tampered"
    events[0] = json.dumps(event)
    protocol_path.write_text("\n".join(events) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="organization_ablation_protocol_replay_invalid"):
        runtime.evaluate_protocols()


def test_authorized_bridge_executes_solo_fixed_and_dynamic_arms_with_real_role_sessions(tmp_path):
    runtime, adapters, _, _, _ = make_execution_runtime(tmp_path)

    snapshot = runtime.execute_arms(best_member_agent_id="framer-a")

    assert snapshot.state == "ARMS_EXECUTED"
    assert {item.arm for item in snapshot.arm_results} == {
        ARM_BEST_MEMBER,
        ARM_FIXED_TEAM,
        ARM_DYNAMIC_TEAM,
    }
    by_arm = {item.arm: item for item in snapshot.arm_results}
    assert by_arm[ARM_BEST_MEMBER].provider_call_count == 1
    assert by_arm[ARM_BEST_MEMBER].replay_verification["valid"]
    assert by_arm[ARM_FIXED_TEAM].provider_call_count == 5
    assert by_arm[ARM_DYNAMIC_TEAM].provider_call_count == 5
    assert len(by_arm[ARM_FIXED_TEAM].formal_messages) == 4
    assert len(by_arm[ARM_DYNAMIC_TEAM].formal_messages) == 4
    assert by_arm[ARM_FIXED_TEAM].replay_verification["valid"]
    assert by_arm[ARM_DYNAMIC_TEAM].replay_verification["valid"]
    assert by_arm[ARM_DYNAMIC_TEAM].context_isolated
    assert all(len(adapter.contexts) == 1 for adapter in adapters.values())
    assert adapters["dynamic-2"].contexts[0].input_messages[0].message_type == "HYPOTHESIS_PROPOSAL"
    assert all(item["valid"] for item in runtime.verify_arm_replays().values())


def test_harness_evaluation_fails_closed_when_an_arm_replay_is_tampered(tmp_path):
    runtime, _, _, _, _ = make_execution_runtime(tmp_path)
    runtime.execute_arms(best_member_agent_id="framer-a")
    events_path = (
        tmp_path
        / "execution"
        / ARM_BEST_MEMBER.lower()
        / "public"
        / "execution-runtime-solo"
        / "events.jsonl"
    )
    event = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    event["payload"]["candidate_output"]["answer"] = "tampered"
    events_path.write_text(json.dumps(event) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="execution_arm_replay_invalid"):
        runtime.evaluate_arms()


def test_provider_may_cite_an_admitted_subset_but_not_an_out_of_scope_source(tmp_path):
    runtime, _, _, _, _ = make_execution_runtime(tmp_path)
    admitted_subset = candidate("correct")
    admitted_subset["evidence_refs"] = [EVIDENCE[0]]
    outsider = candidate("correct")
    outsider["evidence_refs"] = ["evidence://outside"]

    assert runtime._candidate_errors(admitted_subset) == []
    assert "execution_candidate_unadmitted_evidence_ref" in runtime._candidate_errors(outsider)


def test_hidden_truth_never_enters_provider_tasks_and_harness_measures_real_cbit(tmp_path):
    runtime, _, solo, normalizers, assessor = make_execution_runtime(tmp_path)
    runtime.execute_arms(best_member_agent_id="framer-a")

    evaluation = runtime.evaluate_arms()

    snapshot = runtime.snapshot()
    receipts = {item.arm: item for item in snapshot.harness_receipts}
    assert receipts[ARM_DYNAMIC_TEAM].observed_cbit_gain == 1.0
    assert receipts[ARM_FIXED_TEAM].observed_cbit_gain < 0.5
    assert evaluation.verdict_vs_best_member == "OUTPERFORMS"
    assert evaluation.verdict_vs_fixed_team == "OUTPERFORMS"
    provider_tasks = [*solo.tasks, *assessor.tasks]
    for router in normalizers.values():
        provider_tasks.extend(router.adapters[0].tasks)
    serialized = json.dumps([task.inputs for task in provider_tasks], sort_keys=True)
    assert "expected_state" not in serialized
    assert "trial_truth" not in serialized
    assert '"arm"' not in json.dumps([task.inputs for task in assessor.tasks], sort_keys=True)


def test_execution_runtime_requires_exact_authorized_budget_and_complete_adapters(tmp_path):
    registry = make_registry()
    formation, decision, _ = make_formation_runtime(tmp_path, registry)
    spec = make_trial_spec(decision)
    wrong_spec = CognitiveExecutionTrialSpec(
        trial_id=spec.trial_id,
        objective=spec.objective,
        project_scope=spec.project_scope,
        evidence_refs=spec.evidence_refs,
        evidence_payload=spec.evidence_payload,
        finding_catalog=spec.finding_catalog,
        frozen_gate_refs=spec.frozen_gate_refs,
        stop_conditions=spec.stop_conditions,
        budget={"max_provider_calls_per_arm": 99},
        kernel_authorization_ref=spec.kernel_authorization_ref,
    )

    with pytest.raises(ValueError, match="execution_trial_budget_not_kernel_authorized"):
        CognitiveTeamExecutionRuntime(
            execution_id="wrong-budget",
            formation_runtime=formation,
            registry=registry,
            trial_spec=wrong_spec,
            team_adapters={},
            solo_routers={},
            normalization_routers={},
            trial_harness=FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS),
            workspace_root=tmp_path / "wrong",
        )

    runtime, adapters, solo, normalizers, _ = make_execution_runtime(tmp_path / "missing")
    adapters.pop("dynamic-2")
    with pytest.raises(ValueError, match="execution_team_adapter_binding_incomplete"):
        CognitiveTeamExecutionRuntime(
            execution_id="missing-adapter",
            formation_runtime=runtime.formation_runtime,
            registry=runtime.registry,
            trial_spec=runtime.trial_spec,
            team_adapters=adapters,
            solo_routers={"framer-a": ProviderTaskRouter([solo])},
            normalization_routers=normalizers,
            trial_harness=FrozenFindingTrialHarness("frozen-finding-harness", TRUTHS),
            workspace_root=tmp_path / "missing-adapter",
        )


def test_trial_feedback_separates_member_fixed_dynamic_and_formation_provider_credit(tmp_path):
    runtime, _, _, _, _ = make_execution_runtime(tmp_path)
    runtime.execute_arms(best_member_agent_id="framer-a")
    runtime.evaluate_arms()
    ledger = CreditLedger()

    feedback = runtime.apply_credit_feedback(ledger)

    assert feedback.route_selection_authority is False
    assert ledger.profile("framer-a").subject_kind == "agent"
    assert ledger.profile("fixed-team").subject_kind == "team"
    assert ledger.profile("dynamic-team").subject_kind == "team"
    assert ledger.profile("formation-provider").subject_kind == "provider"
    assert feedback.formation_provider_outcome == "TEAM_FORMATION_FORECAST_CALIBRATED"
    assert all(not ledger.profile(subject).selection_authority for subject in (
        "framer-a", "fixed-team", "dynamic-team", "formation-provider"
    ))
    assert runtime.verify_replay()["valid"]


def test_same_provider_backed_coordinator_protocol_runs_in_both_team_arms(tmp_path):
    runtime, _, _, _, _ = make_execution_runtime(
        tmp_path,
        coordinator_factory=coordinator_factory,
    )

    snapshot = runtime.execute_arms(best_member_agent_id="framer-a")

    by_arm = {item.arm: item for item in snapshot.arm_results}
    assert by_arm[ARM_FIXED_TEAM].coordination_receipt_count == 5
    assert by_arm[ARM_DYNAMIC_TEAM].coordination_receipt_count == 5
    assert by_arm[ARM_FIXED_TEAM].provider_call_count == 10
    assert by_arm[ARM_DYNAMIC_TEAM].provider_call_count == 10
    assert by_arm[ARM_FIXED_TEAM].coordinator_protocol_hash == by_arm[ARM_DYNAMIC_TEAM].coordinator_protocol_hash
    assert by_arm[ARM_FIXED_TEAM].coordinator_agent_id not in by_arm[ARM_FIXED_TEAM].agent_ids
    assert by_arm[ARM_DYNAMIC_TEAM].coordinator_agent_id not in by_arm[ARM_DYNAMIC_TEAM].agent_ids
