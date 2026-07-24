from copy import deepcopy
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.ambiguity_role_complementarity import (  # noqa: E402
    build_role_complementarity_candidate, validate_role_complementarity_candidate,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.unstated_ambiguity_holdout import NULL, POSITIVE  # noqa: E402


def _source_artifacts():
    expected = [POSITIVE, NULL] * 4
    specs = (
        ("small-proposer", "local-small", [POSITIVE] * 8, 1.0, 0.0, 8, 3200),
        ("small-runner-up", "local-small-2", [POSITIVE] * 8, 1.0, 0.0, 12, 4800),
        ("strong-skeptic", "local-strong", [NULL] * 8, 0.0, 1.0, 8, 3000),
    )
    runs, profiles = [], []
    for model_id, provider_id, observed, recall, specificity, calls, tokens in specs:
        trials = [{
            "item_id": f"U{index:02d}",
            "outcome": {"expected_state": truth, "observed_state": prediction},
        } for index, (truth, prediction) in enumerate(zip(expected, observed), 1)]
        profile = {
            "model_id": model_id, "provider_id": provider_id,
            "positive_recall": recall, "null_specificity": specificity,
            "balanced_accuracy": (recall + specificity) / 2,
            "total_provider_calls": calls, "total_tokens": tokens,
        }
        runs.append({"model_id": model_id, "trials": trials})
        profiles.append(profile)
    holdout_commitment = {
        "report": {"candidate_state": "UNSTATED_AMBIGUITY_DISCOVERY_GATE_FAILED", "profiles": profiles},
        "model_runs": runs,
        "construction_intervention": {
            "concrete_state_and_confidence_template_removed": True,
            "state_menu_order_counterbalanced_by_item": True,
        },
    }
    holdout = {**holdout_commitment, "artifact_hash": hash_payload(holdout_commitment)}
    judge_commitment = {"policy_candidate": {
        "primary_judge_provider_id": "moonshot", "primary_judge_model_id": "kimi-k2.5",
        "escalation_action": "SECOND_INDEPENDENT_JUDGE_THEN_MODEL_PANEL_IF_CONFLICT",
    }}
    judge = {**judge_commitment, "artifact_hash": hash_payload(judge_commitment)}
    return holdout, judge


def test_role_analysis_exposes_complementarity_without_claiming_gate_closure():
    holdout, judge = _source_artifacts()
    artifact = build_role_complementarity_candidate(
        holdout_artifact=holdout, judge_calibration_artifact=judge,
    )
    validate_role_complementarity_candidate(
        artifact, holdout_artifact=holdout, judge_calibration_artifact=judge,
    )
    assert artifact["proposer_skeptic_disagreement_rate"] == 1.0
    assert {item["balanced_accuracy"] for item in artifact["naive_ensemble_simulations"].values()} == {0.5}
    assert artifact["naive_ensemble_gate_passed"] is False
    assert artifact["oracle_choice_upper_bound"]["balanced_accuracy"] == 1.0
    assert artifact["oracle_choice_upper_bound"]["operational_policy"] is False
    assert artifact["role_candidates"]["ambiguity_proposer"]["model_id"] == "small-proposer"
    assert artifact["role_candidates"]["semantic_coordinator"]["binding_state"].startswith("UNVALIDATED")
    assert not artifact["selection_authority"] and not artifact["production_authority"]


def test_role_analysis_rejects_tampering_and_missing_prompt_controls():
    holdout, judge = _source_artifacts()
    artifact = build_role_complementarity_candidate(
        holdout_artifact=holdout, judge_calibration_artifact=judge,
    )
    tampered = deepcopy(artifact)
    tampered["production_authority"] = True
    with pytest.raises(ValueError, match="artifact_hash_invalid"):
        validate_role_complementarity_candidate(
            tampered, holdout_artifact=holdout, judge_calibration_artifact=judge,
        )
    commitment = {key: value for key, value in holdout.items() if key != "artifact_hash"}
    commitment["construction_intervention"]["state_menu_order_counterbalanced_by_item"] = False
    uncontrolled = {**commitment, "artifact_hash": hash_payload(commitment)}
    with pytest.raises(ValueError, match="prompt_control_missing"):
        build_role_complementarity_candidate(
            holdout_artifact=uncontrolled, judge_calibration_artifact=judge,
        )
