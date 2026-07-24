from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_protocol import ActionCost, build_action_receipt  # noqa: E402
from local_collective_cognition.cognitive_action_selective_holdout import build_selective_holdout, validate_selective_holdout  # noqa: E402
from local_collective_cognition.cognitive_action_selective_runtime import (  # noqa: E402
    ADMISSION_CAP,
    SELECTIVE_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_selective_run,
    build_admission_plan,
    build_selective_preregistration,
    run_local_preference_roles,
    run_selective_adjudication,
    run_selective_baseline,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    }


class FixtureAdapter:
    def __init__(self, *, fail_preferences=False):
        self.fail_preferences = fail_preferences
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-selective",
            model_id="fixture-model",
            task_kinds=(SELECTIVE_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        conflict_id = task.inputs["public_object"]["conflict_id"]
        evidence = list(task.allowed_evidence)
        if "frozen_selected_object" in task.inputs:
            if self.fail_preferences:
                raise ValueError("fixture_preference_failure")
            result = {
                "conflict_id": conflict_id,
                "pragmatic_preference": "CANDIDATE_B",
                "rationale": "The narrower operational reading is the more useful default.",
                "confidence": 0.8,
                "evidence_refs": evidence,
            }
        else:
            result = {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "selection_basis": "NO_PREFERENCE",
                "pragmatic_preference": "NONE",
                "evidence_state": "SOFT_AMBIGUITY",
                "assessment_process_state": "COMPLETE",
                "action": "CLARIFY",
                "rationale": "Neither candidate is entailed by the displayed request.",
                "confidence": 0.7,
                "evidence_refs": evidence,
            }
        return {
            "result": result,
            "usage": {"provider_calls": 1, "input_tokens": 100, "output_tokens": 20, "latency_ms": 5},
            "provenance_refs": evidence,
        }


class FixtureLocalRole:
    model_id = "fixture-local"

    def invoke(self, *, role_id, item, evidence_refs):
        receipt = build_action_receipt(
            action_id="local-" + item["conflict_id"],
            action_type="COMPARE",
            object_ref="object://" + item["conflict_id"],
            actor_role="PRAGMATIC_DEFAULT",
            actor_instance=self.model_id,
            method="fixture",
            result_state="CANDIDATE",
            result={"pragmatic_preference": "CANDIDATE_A"},
            evidence_refs=evidence_refs,
            support=("Fixture preference.",),
            cost=ActionCost(provider_calls=1, input_tokens=40, output_tokens=4, latency_ms=1),
        )
        commitment = {
            "adapter_version": "staged_semantic_scoring_adapter_v0_16",
            "model_id": self.model_id,
            "role_id": role_id,
            "object_ref": "object://" + item["conflict_id"],
            "registry_hash": hash_payload(["fixture", role_id]),
            "selected_call": "STAGED_SCORE",
            "action_receipt": receipt,
            "score_receipt": {"score_hash": "fixture"},
            "wall_latency_ms": 1,
            "reference_available": False,
        }
        return {**commitment, "output_hash": hash_payload(commitment)}


def build_fixture_runs(*, fail_preferences=False):
    corpus = build_selective_holdout()
    prereg = build_selective_preregistration(source_evaluation=source_evaluation())
    baseline = run_selective_baseline(corpus=corpus, preregistration=prereg, adapter=FixtureAdapter())
    admission = build_admission_plan(corpus=corpus, preregistration=prereg, baseline_run=baseline)
    local = run_local_preference_roles(corpus=corpus, admission_plan=admission, adapter=FixtureLocalRole())
    run = run_selective_adjudication(
        corpus=corpus,
        preregistration=prereg,
        baseline_run=baseline,
        admission_plan=admission,
        local_role_run=local,
        adapter=FixtureAdapter(fail_preferences=fail_preferences),
    )
    return corpus, prereg, baseline, admission, local, run


def test_selective_holdout_is_cross_balanced_and_unlabeled():
    corpus = build_selective_holdout()
    validate_selective_holdout(corpus)
    assert corpus["case_count"] == 24
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {6}
    assert "design_stratum" not in str(corpus["public_surface"])


def test_selective_admission_is_capped_and_preserves_selected_object():
    corpus, _, baseline, admission, local, run = build_fixture_runs()
    assert len(admission["eligible_conflict_ids"]) == 24
    assert len(admission["admitted_conflict_ids"]) == ADMISSION_CAP
    assert admission["cap_applied"] is True
    baseline_by_id = {item["conflict_id"]: item["payload"] for item in baseline["outputs"]}
    assert len(run["routed_outputs"]) == 24
    assert all(
        output["payload"]["selected_object"] == baseline_by_id[output["conflict_id"]]["selected_object"]
        for output in run["routed_outputs"]
    )
    analysis = analyze_selective_run(
        corpus=corpus,
        baseline_run=baseline,
        admission_plan=admission,
        local_role_run=local,
        run=run,
    )
    assert analysis["successful_adjudication_count"] == ADMISSION_CAP
    assert analysis["selected_object_preservation_count"] == 24
    assert analysis["routed_coverage"] == 1.0


def test_failed_adjudication_falls_back_to_exact_baseline():
    _, _, baseline, admission, _, run = build_fixture_runs(fail_preferences=True)
    baseline_by_id = {item["conflict_id"]: item["payload"] for item in baseline["outputs"]}
    admitted = set(admission["admitted_conflict_ids"])
    assert len(run["failures"]) == len(admitted)
    for output in run["routed_outputs"]:
        if output["conflict_id"] in admitted:
            assert output["route_state"] == "BASELINE_PRESERVED"
            assert output["payload"] == baseline_by_id[output["conflict_id"]]
