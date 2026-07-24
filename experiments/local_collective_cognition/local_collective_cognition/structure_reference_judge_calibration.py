"""Calibrate historical semantic judges against the candidate model-panel reference."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


CALIBRATION_VERSION = "structure_reference_judge_calibration_v0_1"
MIN_CRITERION_EXACT_RATE = 0.80
LOW_CONFIDENCE_ESCALATION = 0.80


def build_reference_judge_calibration(*, reference_artifact, panel_manifest, semantic_artifact):
    _validate_sources(reference_artifact, panel_manifest, semantic_artifact)
    reference = {item["blind_candidate_id"]: item["criteria"] for item in reference_artifact["labels"]}
    profiles = [_judge_profile(run, reference) for run in semantic_artifact["judge_runs"]]
    profiles.sort(key=lambda item: item["judge_model_id"])
    ranked = sorted(
        profiles,
        key=lambda item: (item["exact_rate"], -item["direct_conflict_rate"], item["judge_model_id"]),
        reverse=True,
    )
    primary, secondary = ranked
    escalations = [
        item["criterion"] for item in primary["criterion_profiles"]
        if item["exact_rate"] < MIN_CRITERION_EXACT_RATE
    ]
    consensus = _consensus_profile(semantic_artifact["report"]["trials"], reference)
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "reference_artifact_hash": reference_artifact["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "semantic_artifact_hash": semantic_artifact["artifact_hash"],
        "reference_label_count": sum(len(item) for item in reference.values()),
        "reference_state_counts": {
            state: sum(value == state for item in reference.values() for value in item.values())
            for state in JUDGE_STATES
        },
        "judge_profiles": profiles, "historical_consensus_profile": consensus,
        "policy_candidate": {
            "primary_judge_provider_id": primary["judge_provider_id"],
            "primary_judge_model_id": primary["judge_model_id"],
            "secondary_judge_provider_id": secondary["judge_provider_id"],
            "secondary_judge_model_id": secondary["judge_model_id"],
            "primary_exact_rate": primary["exact_rate"],
            "primary_lead": primary["exact_rate"] - secondary["exact_rate"],
            "mandatory_criterion_escalations": escalations,
            "state_escalations": ["UNCERTAIN"],
            "confidence_below_escalation": LOW_CONFIDENCE_ESCALATION,
            "escalation_action": "SECOND_INDEPENDENT_JUDGE_THEN_MODEL_PANEL_IF_CONFLICT",
            "fresh_unstated_ambiguity_holdout_required": True,
        },
        "candidate_state": "REFERENCE_CALIBRATED_SEMANTIC_JUDGE_POLICY_CANDIDATE",
        "evidence_coordinate": "INTERNAL_PROJECT_MODEL_PANEL_CANDIDATE",
        "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_judge_calibration(artifact, *, reference_artifact,
                                         panel_manifest, semantic_artifact):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("reference_judge_calibration_hash_invalid")
    expected = build_reference_judge_calibration(
        reference_artifact=reference_artifact, panel_manifest=panel_manifest,
        semantic_artifact=semantic_artifact,
    )
    if artifact != expected:
        raise ValueError("reference_judge_calibration_semantics_invalid")


def _validate_sources(reference, manifest, semantic):
    for artifact, error in ((reference, "reference"), (manifest, "manifest"), (semantic, "semantic")):
        hash_key = "manifest_hash" if error == "manifest" else "artifact_hash"
        commitment = {key: value for key, value in artifact.items() if key != hash_key}
        if artifact.get(hash_key) != hash_payload(commitment):
            raise ValueError(f"reference_judge_calibration_{error}_hash_invalid")
    if (reference.get("panel_id") != manifest.get("panel_id")
            or reference.get("panel_manifest_hash") != manifest.get("manifest_hash")
            or manifest.get("source_semantic_artifact_hash") != semantic.get("artifact_hash")):
        raise ValueError("reference_judge_calibration_source_binding_invalid")
    blind_ids = {item["blind_candidate_id"] for item in reference.get("labels", [])}
    if blind_ids != set(manifest.get("private_source_bindings", {})):
        raise ValueError("reference_judge_calibration_candidate_surface_invalid")


def _judge_profile(run, reference):
    assessments = {
        item["blind_candidate_id"]: item
        for judgment in run["judgments"] for item in judgment["payload"]["assessments"]
    }
    if set(assessments) != set(reference):
        raise ValueError("reference_judge_calibration_assessment_surface_invalid")
    criterion_profiles = []
    all_pairs = []
    for criterion in JUDGE_CRITERIA:
        pairs = [(assessments[key]["criteria"][criterion], reference[key][criterion]) for key in reference]
        all_pairs.extend(pairs)
        criterion_profiles.append(_pair_profile(criterion, pairs))
    errors = sum(left != right for left, right in all_pairs)
    confidence_errors = sum(
        assessments[key]["confidence"] >= LOW_CONFIDENCE_ESCALATION
        and assessments[key]["criteria"][criterion] != reference[key][criterion]
        for key in reference for criterion in JUDGE_CRITERIA
    )
    return {
        "judge_provider_id": run["judge_provider_id"], "judge_model_id": run["judge_model_id"],
        "compared_labels": len(all_pairs), "exact_labels": len(all_pairs) - errors,
        "exact_rate": (len(all_pairs) - errors) / len(all_pairs),
        "direct_conflict_rate": sum(set(pair) == {"PRESENT", "ABSENT"} for pair in all_pairs) / len(all_pairs),
        "high_confidence_error_count": confidence_errors,
        "criterion_profiles": criterion_profiles,
    }


def _pair_profile(criterion, pairs):
    return {
        "criterion": criterion, "compared": len(pairs),
        "exact": sum(left == right for left, right in pairs),
        "exact_rate": sum(left == right for left, right in pairs) / len(pairs),
        "direct_conflicts": sum(set(pair) == {"PRESENT", "ABSENT"} for pair in pairs),
    }


def _consensus_profile(trials, reference):
    index = {item["blind_candidate_id"]: item["consensus"] for item in trials}
    if set(index) != set(reference):
        raise ValueError("reference_judge_calibration_consensus_surface_invalid")
    pairs = [(index[key][criterion], reference[key][criterion]) for key in reference for criterion in JUDGE_CRITERIA]
    return {
        "compared_labels": len(pairs), "exact_labels": sum(left == right for left, right in pairs),
        "exact_rate": sum(left == right for left, right in pairs) / len(pairs),
        "conflict_or_unresolved_count": sum(left in {"CONFLICT", "UNRESOLVED"} for left, _ in pairs),
    }
