from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_judge_calibration import (  # noqa: E402
    build_reference_judge_calibration, validate_reference_judge_calibration,
)
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_CRITERIA  # noqa: E402


def _fixtures():
    reference_states = {
        "blind-a": {criterion: "PRESENT" for criterion in JUDGE_CRITERIA},
        "blind-b": {criterion: "PRESENT" for criterion in JUDGE_CRITERIA},
    }
    reference_states["blind-b"][JUDGE_CRITERIA[0]] = "ABSENT"
    reference_states["blind-b"]["NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE"] = "ABSENT"

    def run(provider, model, states):
        assessments = [{
            "blind_candidate_id": blind_id, "criteria": criteria,
            "confidence": 0.9, "audit_note": "fixture", "fatal_issue": "",
        } for blind_id, criteria in states.items()]
        return {
            "judge_provider_id": provider, "judge_model_id": model,
            "judgments": [{"payload": {"assessments": assessments}}],
        }

    all_present = {
        blind_id: {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
        for blind_id in reference_states
    }
    mostly_exact = {blind_id: dict(criteria) for blind_id, criteria in reference_states.items()}
    mostly_exact["blind-b"]["NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE"] = "PRESENT"
    trials = [{
        "blind_candidate_id": blind_id,
        "consensus": dict(all_present[blind_id]),
    } for blind_id in reference_states]
    semantic_commitment = {
        "judge_runs": [run("provider-a", "judge-a", all_present),
                       run("provider-b", "judge-b", mostly_exact)],
        "report": {"trials": trials},
    }
    semantic = {**semantic_commitment, "artifact_hash": hash_payload(semantic_commitment)}
    manifest_commitment = {
        "panel_version": "structure_model_reference_panel_v0_1", "panel_id": "panel-fixture",
        "source_semantic_artifact_hash": semantic["artifact_hash"],
        "private_source_bindings": {blind_id: {"model_id": "source"} for blind_id in reference_states},
    }
    manifest = {**manifest_commitment, "manifest_hash": hash_payload(manifest_commitment)}
    reference_commitment = {
        "panel_id": manifest["panel_id"], "panel_manifest_hash": manifest["manifest_hash"],
        "labels": [{"blind_candidate_id": blind_id, "criteria": criteria}
                   for blind_id, criteria in reference_states.items()],
    }
    reference = {**reference_commitment, "artifact_hash": hash_payload(reference_commitment)}
    return reference, manifest, semantic


def test_reference_calibration_selects_better_judge_and_escalates_weak_criterion():
    reference, manifest, semantic = _fixtures()
    artifact = build_reference_judge_calibration(
        reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
    )
    validate_reference_judge_calibration(
        artifact, reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
    )
    policy = artifact["policy_candidate"]
    assert policy["primary_judge_model_id"] == "judge-b"
    assert policy["primary_exact_rate"] == 11 / 12
    assert policy["mandatory_criterion_escalations"] == [
        "NO_INVENTED_FACT_OR_SOLUTION_DEPENDENCE"
    ]
    assert policy["fresh_unstated_ambiguity_holdout_required"] is True
    assert not artifact["selection_authority"] and not artifact["production_authority"]


def test_reference_calibration_rejects_rehashed_policy_tamper():
    reference, manifest, semantic = _fixtures()
    artifact = build_reference_judge_calibration(
        reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
    )
    artifact["policy_candidate"]["primary_judge_model_id"] = "judge-a"
    artifact["artifact_hash"] = hash_payload({
        key: value for key, value in artifact.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="semantics_invalid"):
        validate_reference_judge_calibration(
            artifact, reference_artifact=reference, panel_manifest=manifest, semantic_artifact=semantic,
        )
