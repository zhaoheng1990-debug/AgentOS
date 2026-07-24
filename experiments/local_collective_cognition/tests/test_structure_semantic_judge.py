from pathlib import Path
import json
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_elicitor_fresh_holdout import CASES  # noqa: E402
from local_collective_cognition.structure_semantic_judge_blinding import (  # noqa: E402
    build_blind_surface, validate_blind_surface,
)
from local_collective_cognition.structure_semantic_judge_consensus import (  # noqa: E402
    build_semantic_report, validate_semantic_report,
)
from local_collective_cognition.structure_semantic_judge_artifact import validate_semantic_artifact  # noqa: E402
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_CRITERIA, JUDGE_TASK_KIND, validate_semantic_judgment,
)
from local_collective_cognition.structure_semantic_judge_runtime import StructureSemanticJudgeRuntime  # noqa: E402
from local_collective_cognition.structure_semantic_judge_recovery import merge_recovered_judge_run  # noqa: E402


def _source_artifact():
    runs = []
    for model_index, model_id in enumerate(("small-a", "small-b", "strong")):
        trials = []
        for case_index, case in enumerate(CASES):
            outcome = {
                "outcome_hash": hash_payload([model_id, case.item_id]),
                "quality_score": 0.4 + model_index * 0.2,
                "provider_status": "COMPLETED",
            }
            packet = None if model_id == "small-b" and case_index == 0 else {
                "item_id": case.item_id,
                "contrastive_packet": f"RIVAL_A: object {model_index} A | RIVAL_B: object {model_index} B | CONTRAST: unit | QUESTION: Which unit?",
            }
            trials.append({"item_id": case.item_id, "packet": packet, "outcome": outcome})
        runs.append({"model_id": model_id, "trials": trials})
    return {"artifact_hash": "a" * 64, "model_runs": runs}


def _runtime_surface():
    surface = {
        "blinding_version": "fixture", "source_artifact_hash": "a" * 64,
        "batches": [{
            "batch_id": "batch-1", "public_prompt": "A request has two plausible units.",
            "public_candidates": [
                {"blind_candidate_id": "blind-a", "contrastive_packet": "packet a"},
                {"blind_candidate_id": "blind-b", "contrastive_packet": "packet b"},
                {"blind_candidate_id": "blind-s", "contrastive_packet": "packet s"},
            ],
        }],
        "bindings": {
            "blind-a": {"model_id": "small-a", "item_id": "x", "outcome_hash": "1", "mechanical_quality_score": 0.4, "provider_status": "COMPLETED", "packet_hash": "a"},
            "blind-b": {"model_id": "small-b", "item_id": "x", "outcome_hash": "2", "mechanical_quality_score": 0.5, "provider_status": "COMPLETED", "packet_hash": "b"},
            "blind-s": {"model_id": "strong", "item_id": "x", "outcome_hash": "3", "mechanical_quality_score": 0.6, "provider_status": "COMPLETED", "packet_hash": "c"},
        },
        "excluded_trials": [],
    }
    commitment = dict(surface)
    surface["surface_hash"] = hash_payload(commitment)
    runtime = StructureSemanticJudgeRuntime.__new__(StructureSemanticJudgeRuntime)
    runtime.fresh_artifact = {"artifact_hash": "a" * 64}
    runtime.surface = surface
    runtime.evidence_refs = ("artifact://" + "a" * 64,)
    return runtime


class FixtureJudge:
    def __init__(self, provider_id, model_id, state="PRESENT"):
        self.state = state
        self.seen_inputs = []
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id, model_id=model_id,
            task_kinds=(JUDGE_TASK_KIND,), max_timeout_seconds=120,
        )

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        assessments = [{
            "blind_candidate_id": item["blind_candidate_id"],
            "criteria": {criterion: self.state for criterion in JUDGE_CRITERIA},
            "confidence": 0.8, "audit_note": "fixture audit", "fatal_issue": "",
        } for item in task.inputs["blind_candidates"]]
        return {
            "result": {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
                       "assessments": assessments, "evidence_refs": list(task.allowed_evidence)},
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "provenance_refs": list(task.allowed_evidence),
        }


class FailOnceJudge(FixtureJudge):
    def __init__(self):
        super().__init__("provider-flaky", "judge-flaky")
        self.failed = False

    def invoke(self, task):
        if not self.failed:
            self.failed = True
            raise ValueError("fixture_transport_failure")
        return super().invoke(task)


def _fresh_report_surface():
    return {"artifact_hash": "a" * 64, "report": {
        "report_hash": "b" * 64, "selected_small_model_id": "small-a",
        "comparator_small_model_id": "small-b", "strong_model_id": "strong",
        "profiles": [
            {"model_id": "small-a", "mean_quality_score": 0.4},
            {"model_id": "small-b", "mean_quality_score": 0.5},
            {"model_id": "strong", "mean_quality_score": 0.6},
        ],
    }}


def test_blind_surface_is_deterministic_and_omits_source_identity():
    surface = build_blind_surface(_source_artifact())
    validate_blind_surface(surface)
    assert surface == build_blind_surface(_source_artifact())
    public = json.dumps(surface["batches"], sort_keys=True)
    assert all(model_id not in public for model_id in ("small-a", "small-b", "strong"))
    assert len(surface["bindings"]) == 11
    assert surface["excluded_trials"][0]["reason"] == "SOURCE_PACKET_UNAVAILABLE"


def test_candidate_source_self_identification_is_blocked_before_judging():
    artifact = _source_artifact()
    artifact["model_runs"][0]["trials"][0]["packet"]["contrastive_packet"] += " small-a"
    surface = build_blind_surface(artifact)
    assert any(item["reason"] == "SOURCE_IDENTITY_LEAK" for item in surface["excluded_trials"])
    assert len(surface["bindings"]) == 10


def test_runtime_sends_blind_inputs_and_builds_hash_bound_receipts():
    runtime = _runtime_surface()
    judge = FixtureJudge("provider-a", "judge-a")
    run = runtime.evaluate_judge(experiment_id="judge-fixture", adapter=judge)
    assert run["successful_batches"] == 1 and run["total_provider_calls"] == 1
    rendered = json.dumps(judge.seen_inputs, sort_keys=True)
    assert all(model_id not in rendered for model_id in ("small-a", "small-b", "strong"))
    validate_semantic_judgment(
        run["judgments"][0]["payload"], batch_id="batch-1",
        candidate_ids=("blind-a", "blind-b", "blind-s"),
        evidence_refs=runtime.evidence_refs,
    )


def test_two_independent_judges_form_candidate_without_authority():
    runtime = _runtime_surface()
    runs = tuple(runtime.evaluate_judge(
        experiment_id="judge-fixture", adapter=FixtureJudge(f"provider-{i}", f"judge-{i}"),
    ) for i in (1, 2))
    report = build_semantic_report(
        experiment_id="judge-fixture", fresh_artifact=_fresh_report_surface(),
        surface=runtime.surface, judge_runs=runs,
    )
    validate_semantic_report(
        report, fresh_artifact=_fresh_report_surface(), surface=runtime.surface, judge_runs=runs,
    )
    assert report["exact_criterion_agreement"] == 1.0
    assert report["candidate_state"] == "SEMANTIC_SCALE_CALIBRATION_CANDIDATE"
    assert report["selection_authority"] is False and report["retention_authority"] is False


def test_one_failed_batch_can_recover_once_without_erasing_work():
    runtime = _runtime_surface()
    judge = FailOnceJudge()
    primary = runtime.evaluate_judge(experiment_id="judge-fixture", adapter=judge)
    assert primary["failed_batches"] == 1 and primary["total_provider_calls"] == 1
    recovery = runtime.evaluate_judge(
        experiment_id="judge-fixture", adapter=judge, batch_ids=("batch-1",),
    )
    merged = merge_recovered_judge_run(primary, recovery, surface=runtime.surface)
    assert merged["successful_batches"] == 1 and merged["failed_batches"] == 0
    assert merged["total_provider_calls"] == 2
    assert merged["recovered_failures"][0]["batch_id"] == "batch-1"


def test_direct_provider_conflict_requires_audit_and_cannot_be_rehashed_away():
    runtime = _runtime_surface()
    runs = (
        runtime.evaluate_judge(experiment_id="judge-fixture", adapter=FixtureJudge("p1", "j1", "PRESENT")),
        runtime.evaluate_judge(experiment_id="judge-fixture", adapter=FixtureJudge("p2", "j2", "ABSENT")),
    )
    fresh = _fresh_report_surface()
    report = build_semantic_report(
        experiment_id="judge-fixture", fresh_artifact=fresh, surface=runtime.surface, judge_runs=runs,
    )
    assert report["direct_conflict_rate"] == 1.0
    assert report["candidate_state"] == "SEMANTIC_JUDGE_DISAGREEMENT_REQUIRES_AUDIT"
    report["candidate_state"] = "SEMANTIC_SCALE_CALIBRATION_CANDIDATE"
    committed = {key: value for key, value in report.items() if key != "report_hash"}
    report["report_hash"] = hash_payload(committed)
    with pytest.raises(ValueError, match="report_invalid"):
        validate_semantic_report(report, fresh_artifact=fresh, surface=runtime.surface, judge_runs=runs)


def test_semantic_artifact_binds_both_sources_and_inner_report():
    runtime = _runtime_surface()
    runs = tuple(runtime.evaluate_judge(
        experiment_id="judge-fixture", adapter=FixtureJudge(f"p{i}", f"j{i}"),
    ) for i in (1, 2))
    fresh = _fresh_report_surface()
    report = build_semantic_report(
        experiment_id="judge-fixture", fresh_artifact=fresh, surface=runtime.surface, judge_runs=runs,
    )
    commitment = {
        "experiment_id": "judge-fixture", "calibration_source_hash": "c" * 64,
        "fresh_source_hash": fresh["artifact_hash"], "blind_surface": runtime.surface,
        "judge_runs": list(runs), "report": report, "claim_boundary": "candidate-only",
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_semantic_artifact(
        artifact, calibration_artifact={"artifact_hash": "c" * 64}, fresh_artifact=fresh,
    )
    artifact["fresh_source_hash"] = "d" * 64
    artifact["artifact_hash"] = hash_payload({
        key: value for key, value in artifact.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="source_binding_invalid"):
        validate_semantic_artifact(
            artifact, calibration_artifact={"artifact_hash": "c" * 64}, fresh_artifact=fresh,
        )
