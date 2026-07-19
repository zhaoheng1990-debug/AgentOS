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
    CreditEvent,
    CreditLedger,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    TeamCounterfactualEvalHarness,
    TeamTrialObservation,
)
from agentos_runtime import CognitiveTeamFormationRuntime, DeliberationSeed


SCOPE = "project://team-fixture"
EVIDENCE = "evidence://team-source"
ROLES = (
    ("HYPOTHESIS_GENERATOR", "generate"),
    ("ADVERSARIAL_REVIEWER", "challenge"),
    ("REPLICATOR", "replicate"),
    ("SYNTHESIZER", "synthesize"),
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
        result = self.result_factory(task)
        return {
            "result": result,
            "usage": {"total_tokens": 25},
            "provenance_refs": list(task.allowed_evidence),
        }


def make_seed():
    return DeliberationSeed.create(
        seed_id="team-seed",
        source_problem_id="problem-team",
        objective="Which mechanism explains the unresolved project anomaly?",
        research_object="project_anomaly",
        project_scope=SCOPE,
        evidence_refs=(EVIDENCE,),
        rival_explanations=("measurement artifact", "real scope effect"),
        operationalization="Compare rival predictions under one frozen protocol.",
        falsifier="Neither rival predicts the held-out observation.",
        required_harnesses=("counterfactual_team_harness",),
        unresolved_conflicts=("The causal direction remains unresolved.",),
        expected_cbit_gain=0.8,
        agenda_selection_receipt_ref="agenda://team-seed",
    )


def descriptor(agent_id, role, capability, provider_id, model_id="model-v1"):
    return AgentDescriptor(
        agent_id=agent_id,
        role=role,
        capabilities=(capability,),
        runner_id=f"runner-{agent_id}",
        harness_id=f"harness-{role.lower()}",
        provider_id=provider_id,
        model_id=model_id,
        context_isolation_key=f"context-{agent_id}",
        allowed_evidence_scopes=(SCOPE,),
    )


def make_registry():
    registry = AgentRegistry()
    registry.register(descriptor("framer-a", "PROBLEM_FRAMER", "frame", "baseline-provider-a"))
    registry.register(descriptor("framer-b", "PROBLEM_FRAMER", "frame", "baseline-provider-b"))
    for index, (role, capability) in enumerate(ROLES):
        registry.register(descriptor(f"fixed-{index}", role, capability, "fixed-provider"))
        registry.register(
            descriptor(
                f"dynamic-{index}",
                role,
                capability,
                "dynamic-provider-a" if index % 2 == 0 else "dynamic-provider-b",
            )
        )
    return registry


def baseline_payload(question):
    def result(task):
        return {
            "problem_id": f"problem-{task.inputs['blind_member_id']}",
            "question": question,
            "research_object": "project_anomaly",
            "scope": SCOPE,
            "triggering_anomaly": "The held-out observation distinguishes no current explanation.",
            "rival_explanations": ["measurement artifact", "real scope effect"],
            "falsifier": "The proposed discriminator fails on held-out evidence.",
            "required_harnesses": ["counterfactual_team_harness"],
            "expected_cbit_gain": 0.72,
            "evidence_refs": [EVIDENCE],
        }

    return result


def proposal_payload(override=None):
    payload = {
        "selected_agent_ids": ["dynamic-3", "dynamic-1", "dynamic-0", "dynamic-2"],
        "role_coverage": {role: f"dynamic-{index}" for index, (role, _) in enumerate(ROLES)},
        "formation_rationale": "The selected contexts cover generation, challenge, replication, and synthesis.",
        "expected_cbit_gain": 0.78,
        "independence_risks": ["Two members share each provider family."],
        "negative_transfer_risks": ["Historical credit may not transfer to this scope."],
        "evidence_refs": [EVIDENCE],
    }
    payload.update(override or {})
    return payload


def trial_assessment_payload(task):
    score = task.inputs["semantic_artifact"]["semantic_quality"]
    mechanical = task.inputs["harness_owned_metrics"]
    return {
        "blind_arm_id": task.inputs["blind_arm_id"],
        "quality_score": score,
        "observed_cbit_gain": mechanical["observed_cbit_gain"],
        "errors_exposed": mechanical["errors_exposed"],
        "errors_corrected": mechanical["errors_corrected"],
        "negative_transfer_opportunities": mechanical["negative_transfer_opportunities"],
        "negative_transfer_intercepts": mechanical["negative_transfer_intercepts"],
        "normalized_cost": mechanical["normalized_cost"],
        "convergence_steps": mechanical["convergence_steps"],
        "evidence_refs": list(task.allowed_evidence),
    }


def make_runtime(tmp_path, *, registry=None, baseline_results=None, proposal_override=None):
    registry = registry or make_registry()
    baseline_results = baseline_results or (
        baseline_payload("Which intervention distinguishes artifact from scope effect?"),
        baseline_payload("What held-out perturbation reverses the observed anomaly?"),
    )
    providers = (
        ScriptedProvider(
            "baseline-provider-a",
            "model-v1",
            ("independent_problem_baseline_generation",),
            baseline_results[0],
        ),
        ScriptedProvider(
            "baseline-provider-b",
            "model-v1",
            ("independent_problem_baseline_generation",),
            baseline_results[1],
        ),
    )
    formation = ScriptedProvider(
        "formation-provider",
        "formation-model",
        ("cognitive_team_formation_proposal",),
        lambda task: proposal_payload(proposal_override),
    )
    trial_assessor = ScriptedProvider(
        "trial-assessment-provider",
        "trial-assessment-model",
        ("team_trial_semantic_assessment",),
        trial_assessment_payload,
    )
    runtime = CognitiveTeamFormationRuntime(
        runtime_id="team-runtime-fixture",
        seed=make_seed(),
        registry=registry,
        baseline_agent_ids=("framer-a", "framer-b"),
        baseline_routers={
            "framer-a": ProviderTaskRouter([providers[0]]),
            "framer-b": ProviderTaskRouter([providers[1]]),
        },
        formation_router=ProviderTaskRouter([formation]),
        trial_assessment_router=ProviderTaskRouter([trial_assessor]),
        required_roles=tuple(AgentRoleRequirement(role, (capability,)) for role, capability in ROLES),
        fixed_team_id="fixed-team",
        fixed_team_agent_ids=tuple(f"fixed-{index}" for index in range(4)),
        workspace_root=tmp_path,
        evidence_payload={"source": "frozen project evidence", "unresolved": True},
        admitted_evidence_refs=(EVIDENCE,),
        advisory_credit_profiles={"dynamic-0": {"trust_score": 0.7, "advisory_only": True}},
        minimum_provider_diversity=2,
    )
    return runtime, providers, formation


def authorize(runtime):
    runtime.generate_independent_baselines()
    runtime.propose_team(team_id="dynamic-team")
    return runtime.authorize_team(
        kernel_authorization_ref="kernel://team-decision",
        budget={"max_provider_calls": 12, "max_iterations": 3},
    )


def observation(arm, subject_id, agent_ids, score, budget_hash, *, protocol="team-protocol-v1"):
    return TeamTrialObservation(
        observation_id=f"observation-{arm.lower()}",
        trial_id="team-trial-1",
        arm=arm,
        subject_id=subject_id,
        agent_ids=tuple(agent_ids),
        quality_score=score,
        observed_cbit_gain=score,
        errors_exposed=2,
        errors_corrected=2 if score >= 0.7 else 1,
        negative_transfer_opportunities=2,
        negative_transfer_intercepts=2 if score >= 0.7 else 1,
        normalized_cost=0.2,
        convergence_steps=2,
        evidence_refs=(EVIDENCE,),
        harness_protocol_id=protocol,
        budget_hash=budget_hash,
        harness_receipt_ref=f"harness://{arm.lower()}",
        semantic_assessment_receipt_ref=f"provider://{arm.lower()}",
    )


def valid_observations(
    runtime,
    budget_hash,
    dynamic_score=0.9,
    dynamic_protocol="team-protocol-v1",
    best_member_score=0.6,
    fixed_team_score=0.7,
):
    arms = (
        (ARM_BEST_MEMBER, "framer-a", ("framer-a",), best_member_score),
        (ARM_FIXED_TEAM, "fixed-team", tuple(f"fixed-{index}" for index in range(4)), fixed_team_score),
        (ARM_DYNAMIC_TEAM, "dynamic-team", runtime.snapshot().proposal.selected_agent_ids, dynamic_score),
    )
    return tuple(
        runtime.assess_trial_arm(
            trial_id="team-trial-1",
            arm=arm,
            subject_id=subject_id,
            agent_ids=agent_ids,
            harness_protocol_id=(dynamic_protocol if arm == ARM_DYNAMIC_TEAM else "team-protocol-v1"),
            budget_hash=budget_hash,
            harness_receipt_ref=f"harness://{arm.lower()}",
            harness_summary={
                "observed_cbit_gain": score,
                "errors_exposed": 2,
                "errors_corrected": 2 if score >= 0.7 else 1,
                "negative_transfer_opportunities": 2,
                "negative_transfer_intercepts": 2 if score >= 0.7 else 1,
                "normalized_cost": 0.2,
                "convergence_steps": 2,
            },
            semantic_artifact={"semantic_quality": score, "candidate": "bounded trial output"},
        )
        for arm, subject_id, agent_ids, score in arms
    )


def test_independent_baselines_are_context_isolated_and_receive_no_candidate_question(tmp_path):
    runtime, providers, _ = make_runtime(tmp_path)

    receipts = runtime.generate_independent_baselines()

    assert len({item.context_isolation_key for item in receipts}) == 2
    assert len({item.provider_id for item in receipts}) == 2
    assert len({item.question for item in receipts}) == 2
    assert all(not item.execution_authorized for item in receipts)
    task_inputs = [provider.tasks[0].inputs for provider in providers]
    assert [set(item) for item in task_inputs] == [set(task_inputs[0]), set(task_inputs[0])]
    assert all(item["seeded_problem_questions"] == [] for item in task_inputs)
    assert all("peer" not in json.dumps(item).lower() for item in task_inputs)


def test_independent_baseline_provider_binding_uses_invocation_receipt(tmp_path):
    registry = make_registry()
    registry.replace(descriptor("framer-a", "PROBLEM_FRAMER", "frame", "wrong-provider"))
    runtime, _, _ = make_runtime(tmp_path, registry=registry)

    with pytest.raises(ValueError, match="independent_baseline_agent_provider_binding_mismatch"):
        runtime.generate_independent_baselines()


def test_duplicate_independent_problem_is_blocked(tmp_path):
    duplicate = "Which one intervention distinguishes the two rivals?"
    runtime, _, _ = make_runtime(
        tmp_path,
        baseline_results=(baseline_payload(duplicate), baseline_payload(duplicate)),
    )

    with pytest.raises(ValueError, match="independent_baseline_question_not_unique"):
        runtime.generate_independent_baselines()


def test_nested_non_string_baseline_evidence_is_typed_failure(tmp_path):
    valid = baseline_payload("Which intervention distinguishes artifact from scope effect?")

    def malformed(task):
        return {**valid(task), "evidence_refs": [{"ref": EVIDENCE}]}

    runtime, _, _ = make_runtime(
        tmp_path,
        baseline_results=(
            malformed,
            baseline_payload("What held-out perturbation reverses the observed anomaly?"),
        ),
    )

    with pytest.raises(ValueError, match="independent_baseline_evidence_not_admitted"):
        runtime.generate_independent_baselines()


@pytest.mark.parametrize(
    "override,error",
    [
        (
            {
                "selected_agent_ids": ["missing-agent", "dynamic-1", "dynamic-2", "dynamic-3"],
                "role_coverage": {
                    "HYPOTHESIS_GENERATOR": "missing-agent",
                    "ADVERSARIAL_REVIEWER": "dynamic-1",
                    "REPLICATOR": "dynamic-2",
                    "SYNTHESIZER": "dynamic-3",
                },
            },
            "team_proposal_unknown_or_ineligible_agent",
        ),
        (
            {
                "selected_agent_ids": ["fixed-0", "fixed-1", "fixed-2", "fixed-3"],
                "role_coverage": {role: f"fixed-{index}" for index, (role, _) in enumerate(ROLES)},
            },
            "team_proposal_provider_diversity_below_floor",
        ),
        ({"execution_authorized": True}, "team_proposal_authority_claim_forbidden"),
        (
            {
                "role_coverage": {
                    role: {"agent_id": f"dynamic-{index}"}
                    for index, (role, _) in enumerate(ROLES)
                }
            },
            "team_proposal_role_coverage_incomplete",
        ),
    ],
)
def test_provider_team_proposal_cannot_bypass_registry_or_kernel(tmp_path, override, error):
    runtime, _, _ = make_runtime(tmp_path, proposal_override=override)
    runtime.generate_independent_baselines()

    with pytest.raises(ValueError, match=error):
        runtime.propose_team(team_id="dynamic-team")


def test_kernel_authorizes_canonical_role_order_with_explicit_budget(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    runtime.generate_independent_baselines()
    proposal = runtime.propose_team(team_id="dynamic-team")

    assert proposal.selected_agent_ids == tuple(f"dynamic-{index}" for index in range(4))
    assert not proposal.execution_authorized
    with pytest.raises(ValueError, match="kernel_ref_and_budget_required"):
        runtime.authorize_team(kernel_authorization_ref="", budget={})
    decision = runtime.authorize_team(
        kernel_authorization_ref="kernel://team-decision",
        budget={"max_provider_calls": 12},
    )
    assert decision.execution_authorized
    assert decision.assignment.execution_authorized


def test_runtime_rejects_counterfactual_assignment_and_protocol_drift(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    observations = list(valid_observations(runtime, decision.budget_hash))
    observations[2] = observation(
        ARM_DYNAMIC_TEAM,
        "dynamic-team",
        ("dynamic-0", "dynamic-1", "dynamic-2", "fixed-3"),
        0.9,
        decision.budget_hash,
    )
    with pytest.raises(ValueError, match="dynamic_team_observation_assignment_mismatch"):
        runtime.evaluate_counterfactual(tuple(observations))

    runtime, _, _ = make_runtime(tmp_path / "protocol")
    decision = authorize(runtime)
    observations = valid_observations(
        runtime,
        decision.budget_hash,
        dynamic_protocol="drifted-protocol",
    )
    with pytest.raises(ValueError, match="team_counterfactual_harness_protocol_mismatch"):
        runtime.evaluate_counterfactual(observations)


def test_trial_assessment_freezes_harness_metrics_and_rejects_fabricated_receipt(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    drifted = ScriptedProvider(
        "trial-assessment-provider",
        "trial-assessment-model",
        ("team_trial_semantic_assessment",),
        lambda task: {**trial_assessment_payload(task), "observed_cbit_gain": 0.99},
    )
    runtime.trial_assessment_router = ProviderTaskRouter([drifted])
    with pytest.raises(ValueError, match="team_trial_assessment_harness_metric_mismatch:observed_cbit_gain"):
        runtime.assess_trial_arm(
            trial_id="team-trial-1",
            arm=ARM_BEST_MEMBER,
            subject_id="framer-a",
            agent_ids=("framer-a",),
            harness_protocol_id="team-protocol-v1",
            budget_hash=decision.budget_hash,
            harness_receipt_ref="harness://best-member",
            harness_summary={
                "observed_cbit_gain": 0.6,
                "errors_exposed": 2,
                "errors_corrected": 1,
                "negative_transfer_opportunities": 2,
                "negative_transfer_intercepts": 1,
                "normalized_cost": 0.2,
                "convergence_steps": 2,
            },
            semantic_artifact={"semantic_quality": 0.6, "candidate": "bounded trial output"},
        )

    runtime, _, _ = make_runtime(tmp_path / "fabricated")
    decision = authorize(runtime)
    fabricated = (
        observation(ARM_BEST_MEMBER, "framer-a", ("framer-a",), 0.6, decision.budget_hash),
        observation(
            ARM_FIXED_TEAM,
            "fixed-team",
            tuple(f"fixed-{index}" for index in range(4)),
            0.7,
            decision.budget_hash,
        ),
        observation(
            ARM_DYNAMIC_TEAM,
            "dynamic-team",
            runtime.snapshot().proposal.selected_agent_ids,
            0.9,
            decision.budget_hash,
        ),
    )
    with pytest.raises(ValueError, match="team_counterfactual_observation_not_provider_backed"):
        runtime.evaluate_counterfactual(fabricated)


def test_trial_subject_identity_is_locked_before_provider_invocation(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    provider = runtime.trial_assessment_router.adapters[0]

    with pytest.raises(ValueError, match="dynamic_team_observation_subject_mismatch"):
        runtime.assess_trial_arm(
            trial_id="team-trial-1",
            arm=ARM_DYNAMIC_TEAM,
            subject_id="forged-team-subject",
            agent_ids=runtime.snapshot().proposal.selected_agent_ids,
            harness_protocol_id="team-protocol-v1",
            budget_hash=decision.budget_hash,
            harness_receipt_ref="harness://dynamic-team",
            harness_summary={
                "observed_cbit_gain": 0.9,
                "errors_exposed": 2,
                "errors_corrected": 2,
                "negative_transfer_opportunities": 2,
                "negative_transfer_intercepts": 2,
                "normalized_cost": 0.2,
                "convergence_steps": 2,
            },
            semantic_artifact={"semantic_quality": 0.9, "candidate": "bounded trial output"},
        )
    assert provider.tasks == []


def test_trial_semantic_provider_receives_blind_arm_without_member_identity(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    valid_observations(runtime, decision.budget_hash)
    provider = runtime.trial_assessment_router.adapters[0]

    assert len(provider.tasks) == 3
    assert len({task.inputs["blind_arm_id"] for task in provider.tasks}) == 3
    for task in provider.tasks:
        serialized = json.dumps(task.inputs, sort_keys=True)
        assert '"arm"' not in serialized
        assert "subject_id" not in serialized
        assert "agent_ids" not in serialized
        assert "dynamic-team" not in serialized


@pytest.mark.parametrize(
    "dynamic_score,expected",
    [(0.9, "OUTPERFORMS"), (0.7, "AT_PARITY"), (0.4, "UNDERPERFORMS")],
)
def test_three_arm_harness_classifies_dynamic_team_against_fixed_team(dynamic_score, expected):
    harness = TeamCounterfactualEvalHarness()
    budget_hash = "budget-hash"
    observations = (
        observation(ARM_BEST_MEMBER, "member", ("member",), 0.6, budget_hash),
        observation(ARM_FIXED_TEAM, "fixed", ("fixed-a", "fixed-b"), 0.7, budget_hash),
        observation(ARM_DYNAMIC_TEAM, "dynamic", ("dynamic-a", "dynamic-b"), dynamic_score, budget_hash),
    )

    result = harness.evaluate("evaluation", observations)

    assert result.verdict_vs_fixed_team == expected
    assert result.frozen
    assert not result.route_selection_authority


def test_evaluation_feedback_keeps_individual_and_team_credit_separate(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    evaluation = runtime.evaluate_counterfactual(valid_observations(runtime, decision.budget_hash))
    ledger = CreditLedger()

    feedback = runtime.apply_credit_feedback(ledger)

    assert evaluation.verdict_vs_best_member == "OUTPERFORMS"
    assert evaluation.verdict_vs_fixed_team == "OUTPERFORMS"
    assert ledger.profile("framer-a").subject_kind == "agent"
    assert ledger.profile("dynamic-team").subject_kind == "team"
    assert not ledger.profile("dynamic-team").selection_authority
    assert not feedback.route_selection_authority
    assert runtime.snapshot().state == "FEEDBACK_APPLIED"
    assert runtime.verify_replay()["valid"]


def test_pure_team_parity_records_inconclusive_not_positive_credit(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    observations = valid_observations(
        runtime,
        decision.budget_hash,
        dynamic_score=0.7,
        best_member_score=0.7,
        fixed_team_score=0.7,
    )
    runtime.evaluate_counterfactual(observations)
    ledger = CreditLedger()

    feedback = runtime.apply_credit_feedback(ledger)

    profile = ledger.profile("dynamic-team")
    assert feedback.team_outcome == "TEAM_COMPOSITION_INCONCLUSIVE"
    assert profile.positive_weight == 0.0
    assert profile.negative_weight == 0.0
    assert profile.trust_score == 0.5


def test_credit_preflight_prevents_partial_write_on_subject_kind_conflict(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    decision = authorize(runtime)
    runtime.evaluate_counterfactual(valid_observations(runtime, decision.budget_hash))
    ledger = CreditLedger()
    ledger.append(
        CreditEvent(
            event_id="prior-agent-event",
            subject_id="dynamic-team",
            subject_kind="agent",
            outcome="RECEIPT_VALIDATED",
            adjudication_ref="review://prior",
            evidence_refs=(EVIDENCE,),
        )
    )

    with pytest.raises(ValueError, match="team_credit_feedback_subject_kind_conflict:dynamic-team"):
        runtime.apply_credit_feedback(ledger)
    assert ledger.events_for("framer-a") == ()


def test_public_replay_detects_event_tampering(tmp_path):
    runtime, _, _ = make_runtime(tmp_path)
    runtime.generate_independent_baselines()
    events_path = runtime.public_store_path / "events.jsonl"
    lines = events_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["event_type"] = "TAMPERED"
    lines[0] = json.dumps(record, sort_keys=True)
    events_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    verification = runtime.verify_replay()
    assert not verification["valid"]
    assert "event_hash_mismatch:0" in verification["failures"]
