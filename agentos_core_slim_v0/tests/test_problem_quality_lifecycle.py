import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    CascadingInvalidationGraph,
    CreditLedger,
    ProblemQualityEvalHarness,
    ProblemQualityObservation,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    SOURCE_GROUP,
    SOURCE_HUMAN_BASELINE,
    SOURCE_MEMBER,
)
from agentos_runtime import (
    DeliberationSeed,
    FeedbackCreditSubject,
    ProblemQualityLifecycleRuntime,
    ProblemTrialPlan,
)


EVIDENCE = "evidence://project-source"
TRIAL_EVIDENCE = "evidence://independent-trial"
SCOPE = "project://fixture"


def make_seed() -> DeliberationSeed:
    return DeliberationSeed.create(
        seed_id="seed-problem-quality",
        source_problem_id="group-problem",
        objective="Why did every negative control fail to falsify the primary result?",
        research_object="negative_control_failure",
        project_scope=SCOPE,
        evidence_refs=(EVIDENCE,),
        rival_explanations=("threshold artifact", "scope-local effect"),
        operationalization="Re-run all controls against frozen thresholds.",
        falsifier="At least one independent control falsifies the result.",
        required_harnesses=("independent_experiment_harness",),
        unresolved_conflicts=("Threshold calibration remains disputed.",),
        expected_cbit_gain=0.78,
        agenda_selection_receipt_ref="problem-selection://receipt",
    )


def quality_payload(task, score: float = 0.8) -> dict:
    return {
        "candidate_id": task.inputs["candidate_id"],
        "scope": SCOPE,
        "evidence_grounding": score,
        "premise_soundness": score,
        "novelty": score,
        "falsifiability": score,
        "discriminatory_power": score,
        "harness_feasibility": score,
        "expected_cbit_gain": score,
        "normalized_cost": 0.25,
        "negative_transfer_risk": 0.15,
        "assessment_rationale": "The evidence supports a bounded and falsifiable comparison.",
        "evidence_refs": list(task.allowed_evidence),
    }


def outcome_payload(task, resolution="PARTIAL") -> dict:
    residuals = []
    if resolution == "PARTIAL":
        residuals = [
            {
                "problem_id": "RESIDUAL_threshold-calibration",
                "statement": "Which threshold calibration preserves control sensitivity?",
                "research_object": "threshold_calibration",
                "scope": SCOPE,
                "evidence_refs": [TRIAL_EVIDENCE],
                "rival_explanations": ["metric artifact"],
            }
        ]
    survived = resolution != "INVALIDATED"
    return {
        "trial_resolution": resolution,
        "observed_cbit_gain": 0.66 if survived else 0.05,
        "rival_explanations_reduced": ["scope-local effect"] if survived else [],
        "problem_survived": survived,
        "residual_problems": residuals,
        "normalized_cost": 0.3,
        "negative_transfer_signal": 0.1 if survived else 0.7,
        "independent_replication": {
            "performed": True,
            "harness_receipt_ref": task.inputs["independent_harness_receipt_ref"],
            "outcome": "replicated" if survived else "falsified",
        },
        "interpretation": "Independent evidence narrowed the rival set.",
        "evidence_refs": [TRIAL_EVIDENCE],
    }


class ScriptedLifecycleProvider:
    def __init__(
        self,
        *,
        quality_scores=None,
        outcome_resolution="PARTIAL",
        quality_override=None,
        outcome_override=None,
    ):
        self.profile = ProviderCapabilityProfile(
            provider_id="quality-provider",
            model_id="quality-model",
            task_kinds=("problem_quality_assessment", "problem_trial_outcome_interpretation"),
            max_timeout_seconds=120,
        )
        self.quality_scores = list(quality_scores or [0.85, 0.7, 0.65])
        self.outcome_resolution = outcome_resolution
        self.quality_override = quality_override
        self.outcome_override = outcome_override
        self.tasks = []

    def invoke(self, task):
        self.tasks.append(task)
        if task.task_kind == "problem_quality_assessment":
            payload = quality_payload(task, self.quality_scores.pop(0))
            if self.quality_override:
                payload.update(self.quality_override)
        else:
            payload = outcome_payload(task, self.outcome_resolution)
            if self.outcome_override:
                payload.update(self.outcome_override)
        return {
            "result": payload,
            "usage": {"total_tokens": 100},
            "provenance_refs": task.allowed_evidence,
        }


def observation(observation_id: str, source_kind: str, score: float) -> ProblemQualityObservation:
    return ProblemQualityObservation(
        observation_id=observation_id,
        candidate_id=f"candidate-{observation_id}",
        source_kind=source_kind,
        source_subject_id=f"subject-{observation_id}",
        problem_statement=f"Question {observation_id}?",
        scope=SCOPE,
        evidence_refs=(EVIDENCE,),
        provider_id="provider",
        model_id="model",
        provider_support_receipt_ref=f"provider://{observation_id}",
        evidence_grounding=score,
        premise_soundness=score,
        novelty=score,
        falsifiability=score,
        discriminatory_power=score,
        harness_feasibility=score,
        expected_cbit_gain=score,
        normalized_cost=0.2,
        negative_transfer_risk=0.1,
        assessment_rationale="bounded assessment",
    )


def make_runtime(tmp_path, provider=None):
    provider = provider or ScriptedLifecycleProvider()
    runtime = ProblemQualityLifecycleRuntime(
        lifecycle_id="problem-quality-fixture",
        seed=make_seed(),
        provider_router=ProviderTaskRouter([provider]),
        workspace_root=tmp_path / "quality-public",
        admitted_evidence_refs=(EVIDENCE, TRIAL_EVIDENCE),
    )
    return runtime, provider


def assess_baselines(runtime):
    runtime.assess_problem(
        candidate_id="group-problem",
        source_kind=SOURCE_GROUP,
        source_subject_id="group-runtime",
        problem_statement=make_seed().objective,
        evidence_refs=(EVIDENCE,),
    )
    runtime.assess_problem(
        candidate_id="member-problem",
        source_kind=SOURCE_MEMBER,
        source_subject_id="member-agent",
        problem_statement="Could a threshold artifact explain the result?",
        evidence_refs=(EVIDENCE,),
    )
    runtime.assess_problem(
        candidate_id="human-problem",
        source_kind=SOURCE_HUMAN_BASELINE,
        source_subject_id="human-baseline",
        problem_statement="Which control should be rerun first?",
        evidence_refs=(EVIDENCE,),
    )


def make_plan():
    return ProblemTrialPlan.create(
        trial_id="trial-problem-quality",
        problem_id="group-problem",
        required_harnesses=("independent_experiment_harness",),
        measurable_outcomes=("observed_cbit_gain", "rival_reduction"),
        stop_conditions=("frozen_gate_reached",),
        budget={"max_runs": 3},
        rollback_ref="rollback://problem-quality",
    )


def harness_summary(observed_cbit=0.66):
    return {
        "frozen_gate_passed": True,
        "observed_cbit_measurement": {
            "value": observed_cbit,
            "measurement_method": "fixture_frozen_cbit_measurement",
            "components": {"fixture_signal": observed_cbit},
        },
    }


def activate(runtime):
    assess_baselines(runtime)
    runtime.freeze_prospective_evaluation()
    runtime.approve_for_trial(
        trial_plan=make_plan(),
        kernel_authorization_ref="kernel://agenda-review-approved",
    )
    runtime.activate_trial(
        kernel_execution_authorization_ref="kernel://trial-execution-approved",
        harness_execution_receipts={
            "independent_experiment_harness": "harness://independent-run",
        },
    )


def test_problem_quality_harness_requires_group_member_and_human_baselines():
    harness = ProblemQualityEvalHarness()
    with pytest.raises(ValueError, match="human_problem_baseline_required"):
        harness.evaluate(
            "evaluation",
            (
                observation("group", SOURCE_GROUP, 0.8),
                observation("member", SOURCE_MEMBER, 0.7),
            ),
        )


@pytest.mark.parametrize(
    ("group_score", "member_score", "human_score", "member_verdict", "human_verdict"),
    (
        (0.85, 0.65, 0.70, "OUTPERFORMS", "OUTPERFORMS"),
        (0.70, 0.69, 0.70, "AT_PARITY", "AT_PARITY"),
        (0.60, 0.80, 0.70, "UNDERPERFORMS", "UNDERPERFORMS"),
    ),
)
def test_problem_quality_harness_distinguishes_all_baseline_verdicts(
    group_score,
    member_score,
    human_score,
    member_verdict,
    human_verdict,
):
    evaluation = ProblemQualityEvalHarness().evaluate(
        "evaluation",
        (
            observation("group", SOURCE_GROUP, group_score),
            observation("member", SOURCE_MEMBER, member_score),
            observation("human", SOURCE_HUMAN_BASELINE, human_score),
        ),
    )
    assert evaluation.verdict_vs_best_member == member_verdict
    assert evaluation.verdict_vs_human_baseline == human_verdict
    assert evaluation.frozen is True
    assert evaluation.execution_authorized is False


def test_provider_quality_assessment_is_blinded_and_frozen(tmp_path):
    runtime, provider = make_runtime(tmp_path)
    assess_baselines(runtime)
    evaluation = runtime.freeze_prospective_evaluation()
    assert evaluation.group_observation_id == "observation-problem-quality-fixture-1"
    assert all("source_kind" not in task.inputs for task in provider.tasks)
    assert all("source_subject_id" not in task.inputs for task in provider.tasks)
    assert all(task.inputs["candidate_id"].startswith("blind-") for task in provider.tasks)
    assert len({tuple(sorted(task.inputs)) for task in provider.tasks}) == 1
    with pytest.raises(RuntimeError, match="assessment_window_closed"):
        runtime.assess_problem(
            candidate_id="late",
            source_kind=SOURCE_MEMBER,
            source_subject_id="late-member",
            problem_statement="Late question?",
            evidence_refs=(EVIDENCE,),
        )


def test_invalid_provider_metric_is_blocked_without_observation(tmp_path):
    runtime, _ = make_runtime(
        tmp_path,
        ScriptedLifecycleProvider(quality_override={"premise_soundness": float("nan")}),
    )
    with pytest.raises(ValueError, match="problem_quality_metric_invalid:premise_soundness"):
        runtime.assess_problem(
            candidate_id="group-problem",
            source_kind=SOURCE_GROUP,
            source_subject_id="group-runtime",
            problem_statement=make_seed().objective,
            evidence_refs=(EVIDENCE,),
        )
    assert runtime.snapshot().observations == ()
    assert runtime.snapshot().state == "PENDING_AGENDA_REVIEW"


def test_candidate_cannot_self_promote_to_trial(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    assess_baselines(runtime)
    runtime.freeze_prospective_evaluation()
    with pytest.raises(ValueError, match="kernel_authorization_required"):
        runtime.approve_for_trial(trial_plan=make_plan(), kernel_authorization_ref="")
    assert runtime.snapshot().state == "PENDING_AGENDA_REVIEW"


def test_failed_quality_gate_can_be_kernel_rejected_and_fed_back(tmp_path):
    runtime, _ = make_runtime(
        tmp_path,
        ScriptedLifecycleProvider(quality_override={"negative_transfer_risk": 0.9}),
    )
    assess_baselines(runtime)
    evaluation = runtime.freeze_prospective_evaluation()
    assert evaluation.group_trial_gate_passed is False
    rejection = runtime.reject_for_trial(
        reason="quality gate and admitted evidence reject the trial",
        kernel_adjudication_ref="kernel://quality-rejected",
        evidence_refs=(EVIDENCE, TRIAL_EVIDENCE),
    )
    assert rejection.execution_authorized is False
    assert runtime.snapshot().state == "INVALIDATED"

    class AgendaSink:
        def record_agenda_feedback(self, feedback):
            assert feedback.problem_resolution == "INVALIDATED"
            return ()

    ledger = CreditLedger()
    graph = CascadingInvalidationGraph()
    feedback = runtime.apply_feedback(
        agenda_feedback_sink=AgendaSink(),
        credit_ledger=ledger,
        invalidation_graph=graph,
        credit_subjects=(FeedbackCreditSubject("group-framer", "agent"),),
    )
    assert feedback.trial_id == "NO_TRIAL_QUALITY_REJECTION"
    assert feedback.invalidation_receipt is not None
    assert graph.is_reuse_blocked("problem://group-problem") is True
    assert ledger.profile("group-framer").trust_score == 0.0


def test_trial_activation_requires_authorized_independent_harness_receipt(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    assess_baselines(runtime)
    runtime.freeze_prospective_evaluation()
    runtime.approve_for_trial(
        trial_plan=make_plan(),
        kernel_authorization_ref="kernel://approved",
    )
    with pytest.raises(ValueError, match="required_harness_receipt_missing"):
        runtime.activate_trial(
            kernel_execution_authorization_ref="kernel://execute",
            harness_execution_receipts={},
        )
    assert runtime.snapshot().state == "APPROVED_FOR_TRIAL"


def test_partial_trial_records_outcome_and_feedback(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    activate(runtime)
    outcome = runtime.record_outcome(
        trial_evidence_refs=(TRIAL_EVIDENCE,),
        harness_result_summary=harness_summary(),
        independent_harness_receipt_ref="harness://independent-run",
    )
    assert runtime.snapshot().state == "PARTIAL"
    assert outcome.candidate_only is True
    assert outcome.publication_authorized is False
    assert outcome.residual_problems[0].problem_id == "RESIDUAL_threshold-calibration"

    class AgendaSink:
        def __init__(self):
            self.feedback = None

        def record_agenda_feedback(self, feedback):
            self.feedback = feedback
            return tuple(item.problem_id for item in feedback.residual_problems)

    sink = AgendaSink()
    ledger = CreditLedger()
    graph = CascadingInvalidationGraph()
    feedback = runtime.apply_feedback(
        agenda_feedback_sink=sink,
        credit_ledger=ledger,
        invalidation_graph=graph,
        credit_subjects=(FeedbackCreditSubject("group-framer", "agent"),),
    )
    assert sink.feedback.problem_resolution == "PARTIAL"
    assert feedback.residual_problem_ids == ("RESIDUAL_threshold-calibration",)
    assert ledger.profile("group-framer").event_count == 1
    assert feedback.route_selection_authority is False
    assert runtime.verify_replay()["valid"] is True


def test_invalidated_trial_penalizes_credit_and_blocks_problem_reuse(tmp_path):
    runtime, _ = make_runtime(
        tmp_path,
        ScriptedLifecycleProvider(outcome_resolution="INVALIDATED"),
    )
    activate(runtime)
    runtime.record_outcome(
        trial_evidence_refs=(TRIAL_EVIDENCE,),
        harness_result_summary=harness_summary(0.05),
        independent_harness_receipt_ref="harness://independent-run",
    )

    class AgendaSink:
        def record_agenda_feedback(self, feedback):
            assert feedback.problem_resolution == "INVALIDATED"
            return ()

    ledger = CreditLedger()
    graph = CascadingInvalidationGraph()
    feedback = runtime.apply_feedback(
        agenda_feedback_sink=AgendaSink(),
        credit_ledger=ledger,
        invalidation_graph=graph,
        credit_subjects=(FeedbackCreditSubject("quality-provider", "provider"),),
    )
    assert ledger.profile("quality-provider").trust_score == 0.0
    assert graph.is_reuse_blocked("problem://group-problem") is True
    assert feedback.invalidation_receipt["root_node_id"] == "problem://group-problem"


def test_outcome_rejects_unapproved_replication_receipt(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    activate(runtime)
    with pytest.raises(ValueError, match="replication_receipt_not_authorized"):
        runtime.record_outcome(
            trial_evidence_refs=(TRIAL_EVIDENCE,),
            harness_result_summary=harness_summary(),
            independent_harness_receipt_ref="harness://different-run",
        )
    assert runtime.snapshot().state == "ACTIVE"


def test_outcome_rejects_rival_claimed_reduced_but_retained_in_residual(tmp_path):
    runtime, _ = make_runtime(
        tmp_path,
        ScriptedLifecycleProvider(
            outcome_override={"rival_explanations_reduced": ["metric artifact"]},
        ),
    )
    activate(runtime)
    with pytest.raises(ValueError, match="reduced_rival_reappears"):
        runtime.record_outcome(
            trial_evidence_refs=(TRIAL_EVIDENCE,),
            harness_result_summary=harness_summary(),
            independent_harness_receipt_ref="harness://independent-run",
        )
    assert runtime.snapshot().state == "ACTIVE"


def test_outcome_rejects_provider_cbit_that_differs_from_harness_measurement(tmp_path):
    runtime, _ = make_runtime(
        tmp_path,
        ScriptedLifecycleProvider(outcome_override={"observed_cbit_gain": 0.9}),
    )
    activate(runtime)
    with pytest.raises(ValueError, match="observed_cbit_mismatch_harness_measurement"):
        runtime.record_outcome(
            trial_evidence_refs=(TRIAL_EVIDENCE,),
            harness_result_summary=harness_summary(),
            independent_harness_receipt_ref="harness://independent-run",
        )
    assert runtime.snapshot().state == "ACTIVE"


def test_problem_quality_replay_detects_tamper(tmp_path):
    runtime, _ = make_runtime(tmp_path)
    assess_baselines(runtime)
    runtime.freeze_prospective_evaluation()
    assert runtime.verify_replay()["valid"] is True
    events_path = runtime.public_store_path / "events.jsonl"
    events = events_path.read_text(encoding="utf-8").splitlines()
    record = json.loads(events[0])
    record["payload"]["problem_id"] = "tampered"
    events[0] = json.dumps(record, sort_keys=True)
    events_path.write_text("\n".join(events) + "\n", encoding="utf-8")
    assert runtime.verify_replay()["valid"] is False


def test_live_smoke_fixture_rebinds_seed_to_current_project_source():
    from examples.problem_quality_lifecycle_project_source_smoke import (
        DEFAULT_PROBLEM_SNAPSHOT,
        _reconstruct_agenda,
        _seed_from_snapshot,
    )
    from examples.project_source_group_cognition_smoke import default_paths, load_source_dossier

    source_pack, gate_file = default_paths()
    dossier, _ = load_source_dossier(source_pack, gate_file)
    snapshot = json.loads(DEFAULT_PROBLEM_SNAPSHOT.read_text(encoding="utf-8"))
    seed = _seed_from_snapshot(snapshot, tuple(dossier["source_refs"]))
    agenda = _reconstruct_agenda(snapshot, seed)

    assert DEFAULT_PROBLEM_SNAPSHOT.is_file()
    assert all(ref in dossier["source_refs"] for ref in seed.evidence_refs)
    assert agenda.problem(seed.source_problem_id).status == "ACTIVE"
