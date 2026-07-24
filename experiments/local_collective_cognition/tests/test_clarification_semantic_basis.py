from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_semantic_basis_calibration import build_semantic_basis_analysis, build_semantic_basis_calibration, validate_semantic_basis_calibration  # noqa: E402
from local_collective_cognition.clarification_semantic_basis_contracts import SEMANTIC_BASIS_TASK_KIND, derive_semantic_basis_decision  # noqa: E402
from local_collective_cognition.clarification_semantic_basis_holdout import build_semantic_basis_holdout_artifact, validate_semantic_basis_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_semantic_basis_runtime import BASELINE_LANE, LANES, ClarificationSemanticBasisRuntime, validate_semantic_basis_run  # noqa: E402
from local_collective_cognition.clarification_warrant_contracts import WARRANT_TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, oracle):
        self.lane = lane
        self.oracle = oracle
        task_kind = WARRANT_TASK_KIND if lane == BASELINE_LANE else SEMANTIC_BASIS_TASK_KIND
        self.profile = ProviderCapabilityProfile(provider_id="fixture-" + lane.lower(), model_id="fixture", task_kinds=(task_kind,), max_timeout_seconds=180)

    def invoke(self, task):
        items = []
        for case in task.inputs["public_cases"]:
            truth = self.oracle[case["blind_case_id"]]
            basis = truth["construction_basis"]
            if self.lane == BASELINE_LANE:
                hard = basis == "LEXICAL_EXACT"
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "explicit_selection": truth["selected_object"] if hard else "NONE",
                    "pragmatic_preference": truth["pragmatic_preference"],
                    "assessment_status": "RESOLVED",
                    "warrant_type": "EXACT_OBJECT_MENTION" if hard else ("DEFAULT_COMPATIBILITY" if basis != "NO_PREFERENCE" else "NO_EXPLICIT_WARRANT"),
                    "warrant_quote": case["public_prompt"] if hard else "NONE",
                    "preference_basis": "Fixture preference.",
                    "status_basis": "Fixture complete.",
                })
            else:
                items.append({
                    "blind_case_id": case["blind_case_id"],
                    "request_object_quote": case["public_prompt"],
                    "selected_object": truth["selected_object"],
                    "selection_basis": basis,
                    "pragmatic_preference": truth["pragmatic_preference"],
                    "axis_assessment_complete": True,
                    "entailment_evidence_quote": case["public_prompt"] if basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") else "NONE",
                    "entailment_explanation": "Fixture semantic basis.",
                    "preference_basis": "Fixture preference.",
                    "completeness_basis": "Fixture complete.",
                })
        return {
            "result": {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0], "assessments": items, "evidence_refs": list(task.allowed_evidence)},
            "usage": {"input_tokens": 70, "output_tokens": 50},
            "provenance_refs": list(task.allowed_evidence),
        }


def _fixture_run():
    corpus = build_semantic_basis_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationSemanticBasisRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-v011", adapters={lane: FixtureAdapter(lane, oracle) for lane in LANES})
    return corpus, run


def test_semantic_basis_fixture_separates_entailment_from_preference():
    corpus, run = _fixture_run()
    validate_semantic_basis_holdout_artifact(corpus)
    validate_semantic_basis_run(run, corpus_artifact=corpus)
    calibration = build_semantic_basis_calibration(corpus_artifact=corpus, candidate_run=run)
    validate_semantic_basis_calibration(calibration, corpus_artifact=corpus, candidate_run=run)
    assert calibration["candidate_state"] == "AWAITING_SEMANTIC_WARRANT_MODEL_PANEL"
    assert calibration["arm_metrics"]["BASELINE_V0_10_WARRANT"]["category_accuracy"] == 0.75
    assert calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"]["category_accuracy"] == 1.0
    assert calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"]["basis_accuracy"] == 1.0
    assert calibration["construction_diagnostic_all_passed"] is True
    assert calibration["action_credit_authority"] is False
    analysis = build_semantic_basis_analysis(calibration, candidate_run=run)
    assert analysis["candidate_state"] == "PRE_PANEL_DIAGNOSTIC_ONLY"


def test_semantic_basis_runtime_policy_preserves_soft_preference_without_authority():
    assert derive_semantic_basis_decision("CANDIDATE_A", "COMPOSITIONAL_ENTAILMENT", True) == ("PROMPT_FIXED", "CANDIDATE_A", False)
    assert derive_semantic_basis_decision("CANDIDATE_B", "PRAGMATIC_DEFAULT", True) == ("OPEN_RIVALS", "NONE", True)
    assert derive_semantic_basis_decision("NONE", "NO_PREFERENCE", True) == ("OPEN_RIVALS", "NONE", False)
    assert derive_semantic_basis_decision("CANDIDATE_A", "LEXICAL_EXACT", False) == ("UNCERTAIN", "NONE", False)


def test_semantic_basis_run_rejects_prediction_tamper():
    corpus, run = _fixture_run()
    tampered = deepcopy(run)
    tampered["predictions"][0]["semantic_selection_basis"] = "NO_PREFERENCE"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="predictions_invalid"):
        validate_semantic_basis_run(tampered, corpus_artifact=corpus)
