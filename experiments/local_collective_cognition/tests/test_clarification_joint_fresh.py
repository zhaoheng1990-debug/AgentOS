from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_joint_fresh_contracts import FRESH_COORDINATOR_TASK_KIND, assess_fresh_decision  # noqa: E402
from local_collective_cognition.clarification_joint_fresh_eval import build_joint_fresh_analysis, build_joint_fresh_report, validate_joint_fresh_report  # noqa: E402
from local_collective_cognition.clarification_joint_fresh_runtime import ClarificationJointFreshRuntime, validate_joint_fresh_run  # noqa: E402
from local_collective_cognition.clarification_joint_holdout import build_joint_holdout_artifact, validate_joint_holdout_artifact  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, oracle):
        self.oracle = oracle
        self.profile = ProviderCapabilityProfile(provider_id="fixture-joint-fresh", model_id="fixture", task_kinds=(FRESH_COORDINATOR_TASK_KIND,), max_timeout_seconds=180)

    def invoke(self, task):
        decisions = []
        for conflict in task.inputs["batch"]["conflicts"]:
            truth = self.oracle[conflict["conflict_id"]]["construction_truth"]
            actions = {axis: "REOPEN" if truth[axis] != conflict["locked_consensus_axes"][axis] else "PRESERVE" for axis in ("SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")}
            decisions.append({
                "conflict_id": conflict["conflict_id"], "consensus_axis_actions": actions,
                "local_basis_action": "REVISE" if truth["SELECTION_BASIS"] != conflict["local_basis_outcome"]["selection_basis"] else "PRESERVE",
                "final_selected_object": truth["SELECTED_OBJECT"], "final_selection_basis": truth["SELECTION_BASIS"],
                "final_pragmatic_preference": truth["PRAGMATIC_PREFERENCE"], "final_assessment_completeness": truth["AXIS_ASSESSMENT_COMPLETE"],
                "evidence_quote": "NONE", "decision_basis": "Fixture joint semantic decision.", "confidence": 0.9,
            })
        batch = task.inputs["batch"]
        return {"result": {"batch_id": batch["batch_id"], "decisions": decisions, "evidence_refs": list(task.allowed_evidence)}, "usage": {"input_tokens": 220, "output_tokens": 180}, "provenance_refs": list(task.allowed_evidence)}


def _fixture():
    corpus = build_joint_holdout_artifact(); oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationJointFreshRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-v013", adapter=FixtureAdapter(oracle))
    return corpus, run


def test_fresh_joint_holdout_balances_preserve_and_reopen_without_exposing_menu():
    corpus = build_joint_holdout_artifact(); validate_joint_holdout_artifact(corpus)
    oracle = corpus["private_oracle"]["bindings"]
    assert len(oracle) == 24
    for axis in ("SELECTION_BASIS", "SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"):
        group = [item for item in oracle.values() if item["target_axis"] == axis]
        assert len(group) == 6 and sum(item["target_action"] == "PRESERVE" for item in group) == 3
    public = json.dumps(corpus["public_surface"], sort_keys=True)
    assert "target_axis" not in public and "target_action" not in public and "construction_truth" not in public


def test_fresh_joint_fixture_closes_tuple_and_action_diagnostics_without_authority():
    corpus, run = _fixture(); validate_joint_fresh_run(run, corpus_artifact=corpus)
    report = build_joint_fresh_report(corpus_artifact=corpus, run=run); validate_joint_fresh_report(report, corpus_artifact=corpus, run=run)
    assert report["preserve_all_baseline"]["tuple_accuracy"] == 0.5
    assert report["candidate_metrics"]["tuple_accuracy"] == 1.0
    assert report["candidate_metrics"]["target_action_accuracy"] == 1.0
    assert report["construction_diagnostic_all_passed"] is True
    assert report["candidate_state"] == "AWAITING_JOINT_COORDINATOR_MODEL_PANEL"
    assert report["selection_authority"] is False
    assert build_joint_fresh_analysis(report)["candidate_state"] == "PRE_PANEL_DIAGNOSTIC_ONLY"


def test_fresh_joint_runtime_derives_governance_without_overall_disposition():
    corpus = build_joint_holdout_artifact(); conflict = corpus["public_surface"]["batches"][0]["conflicts"][0]
    locked = conflict["locked_consensus_axes"]
    decision = {"consensus_axis_actions": {axis: "PRESERVE" for axis in locked}, "local_basis_action": "PRESERVE", "final_selected_object": locked["SELECTED_OBJECT"], "final_selection_basis": conflict["local_basis_outcome"]["selection_basis"], "final_pragmatic_preference": locked["PRAGMATIC_PREFERENCE"], "final_assessment_completeness": locked["AXIS_ASSESSMENT_COMPLETE"]}
    assessment = assess_fresh_decision(decision, conflict=conflict)
    assert assessment["mechanical_state"] in ("COHERENT_PRESERVATION_CANDIDATE", "INCOHERENT_TUPLE")
    bad = deepcopy(decision); bad["consensus_axis_actions"]["SELECTED_OBJECT"] = "REOPEN"
    assert assess_fresh_decision(bad, conflict=conflict)["mechanical_state"] == "INVALID_ACTION_DECLARATION"


def test_fresh_joint_run_rejects_assessment_tamper():
    corpus, run = _fixture(); tampered = deepcopy(run)
    tampered["judgments"][0]["decisions"][0]["runtime_assessment"]["governance_valid"] = False
    judgment = tampered["judgments"][0]
    judgment["judgment_hash"] = hash_payload({key: value for key, value in judgment.items() if key != "judgment_hash"})
    tampered["run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "run_hash"})
    with pytest.raises(ValueError, match="runtime_assessment_invalid"):
        validate_joint_fresh_run(tampered, corpus_artifact=corpus)
