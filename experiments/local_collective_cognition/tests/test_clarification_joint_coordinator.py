from copy import deepcopy
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_joint_coordinator_contracts import JOINT_COORDINATOR_TASK_KIND, assess_joint_decision  # noqa: E402
from local_collective_cognition.clarification_joint_coordinator_eval import build_joint_coordinator_analysis, build_joint_coordinator_report, validate_joint_coordinator_report  # noqa: E402
from local_collective_cognition.clarification_joint_coordinator_runtime import ClarificationJointCoordinatorRuntime, validate_joint_coordinator_run  # noqa: E402
from local_collective_cognition.clarification_joint_coordinator_surface import build_joint_coordinator_surface, validate_joint_coordinator_surface  # noqa: E402


OUTPUT = ROOT / "outputs" / "clarification_semantic_basis_v0_11"


def _read(name):
    return json.loads((OUTPUT / name).read_text(encoding="utf-8"))


def _surface():
    inputs = {
        "corpus_artifact": _read("private_semantic_basis_corpus.json"),
        "panel_reference": _read("semantic_basis_model_panel_reference_candidate.json"),
        "adjudication_pack": _read("kimi_k3_semantic_basis_adjudication_pack.json"),
        "adjudication_response": _read("kimi_k3_semantic_basis_response.json"),
    }
    return build_joint_coordinator_surface(**inputs), inputs


class FixtureCoordinatorAdapter:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(provider_id="fixture-joint-coordinator", model_id="fixture", task_kinds=(JOINT_COORDINATOR_TASK_KIND,), max_timeout_seconds=180)
        self.seen_inputs = []

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        decisions = []
        for conflict in task.inputs["batch"]["conflicts"]:
            locked = conflict["locked_consensus_axes"]
            decisions.append({
                "conflict_id": conflict["conflict_id"], "disposition": "PRESERVE_CONSENSUS_REPAIR",
                "final_selected_object": locked["SELECTED_OBJECT"], "final_selection_basis": "PRAGMATIC_DEFAULT",
                "final_pragmatic_preference": locked["PRAGMATIC_PREFERENCE"],
                "final_assessment_completeness": locked["AXIS_ASSESSMENT_COMPLETE"],
                "preserved_consensus_axes": ["SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"],
                "reopened_consensus_axes": [], "evidence_quote": "NONE",
                "decision_basis": "The full tuple preserves unanimous axes and represents directional preference as soft.", "confidence": 0.9,
            })
        batch_id = task.inputs["batch"]["batch_id"]
        return {"result": {"batch_id": batch_id, "decisions": decisions, "evidence_refs": list(task.allowed_evidence)}, "usage": {"input_tokens": 300, "output_tokens": 180}, "provenance_refs": list(task.allowed_evidence)}


def test_joint_surface_contains_only_three_observed_conflicts_and_hides_identity():
    surface, inputs = _surface()
    validate_joint_coordinator_surface(surface, **inputs)
    assert surface["observed_conflict_count"] == 3
    public = json.dumps(surface["public_conflicts"], sort_keys=True).casefold()
    assert "gpt-5.6" not in public and "gemini-3.1" not in public and "deepseek" not in public


def test_joint_runtime_accepts_coherent_consensus_preserving_repairs_without_authority():
    surface, _ = _surface()
    adapter = FixtureCoordinatorAdapter()
    run = ClarificationJointCoordinatorRuntime(surface=surface).evaluate(experiment_id="fixture-v012", adapter=adapter)
    validate_joint_coordinator_run(run, surface=surface)
    report = build_joint_coordinator_report(surface=surface, run=run)
    validate_joint_coordinator_report(report, surface=surface, run=run)
    assert report["accepted_repair_count"] == 3
    assert report["consensus_changed_count"] == 0
    assert report["candidate_state"] == "OBSERVED_CONFLICT_REPAIR_DIAGNOSTIC_ONLY"
    assert report["selection_authority"] is False
    analysis = build_joint_coordinator_analysis(report, run=run)
    assert analysis["next_required_evidence"] == "FRESH_CROSS_AXIS_CONFLICT_HOLDOUT"
    assert adapter.seen_inputs[0]["source_identity"] == "WITHHELD"


def test_joint_policy_rejects_incoherent_preservation_and_requires_explicit_reopen():
    locked = {"SELECTED_OBJECT": "NONE", "PRAGMATIC_PREFERENCE": "CANDIDATE_A", "AXIS_ASSESSMENT_COMPLETE": "COMPLETE"}
    decision = {
        "disposition": "PRESERVE_CONSENSUS_REPAIR", "final_selected_object": "NONE",
        "final_selection_basis": "COMPOSITIONAL_ENTAILMENT", "final_pragmatic_preference": "CANDIDATE_A",
        "final_assessment_completeness": "COMPLETE", "preserved_consensus_axes": list(locked), "reopened_consensus_axes": [],
    }
    assessment = assess_joint_decision(decision, locked_consensus_axes=locked)
    assert assessment["mechanical_state"] == "INVALID_PRESERVATION_PROPOSAL"
    assert assessment["coherence_violations"] == ["HARD_BASIS_WITHOUT_SELECTED_OBJECT"]
    reopened = dict(decision, disposition="REOPEN_CONSENSUS_AXIS", final_selected_object="CANDIDATE_A", preserved_consensus_axes=["PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"], reopened_consensus_axes=["SELECTED_OBJECT"])
    assessment = assess_joint_decision(reopened, locked_consensus_axes=locked)
    assert assessment["mechanical_state"] == "REOPEN_REQUIRES_NEW_PANEL"
    assert assessment["proposal_accepted"] is True


def test_joint_run_rejects_runtime_assessment_tamper():
    surface, _ = _surface()
    run = ClarificationJointCoordinatorRuntime(surface=surface).evaluate(experiment_id="fixture-tamper", adapter=FixtureCoordinatorAdapter())
    tampered = deepcopy(run)
    tampered["decisions"][0]["runtime_assessment"]["proposal_accepted"] = False
    from local_collective_cognition.provider_telemetry import hash_payload
    tampered["run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "run_hash"})
    with pytest.raises(ValueError, match="runtime_assessment_invalid"):
        validate_joint_coordinator_run(tampered, surface=surface)
