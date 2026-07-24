"""Construction-only pre-panel diagnostics for semantic-basis v0.11."""

from __future__ import annotations

from collections import Counter, defaultdict

from .clarification_semantic_basis_contracts import HARD_SELECTION_BASES
from .clarification_semantic_basis_holdout import validate_semantic_basis_holdout_artifact
from .clarification_semantic_basis_runtime import BASELINE_LANE, SEMANTIC_BASIS_LANE, validate_semantic_basis_run
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_semantic_basis_calibration_v0_11"
FROZEN_DIAGNOSTIC_THRESHOLDS = {
    "minimum_category_accuracy": 0.90,
    "minimum_basis_accuracy": 0.80,
    "minimum_fixed_recall": 0.90,
    "minimum_open_recall": 0.90,
    "minimum_fixed_direction_accuracy": 0.90,
    "minimum_hard_selection_precision": 0.90,
    "minimum_preference_alignment": 0.75,
    "minimum_completeness_rate": 0.95,
    "minimum_gain_over_baseline": 0.05,
    "maximum_call_multiplier": 1.10,
}


def build_semantic_basis_calibration(*, corpus_artifact, candidate_run):
    validate_semantic_basis_holdout_artifact(corpus_artifact)
    validate_semantic_basis_run(candidate_run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    predictions = {row["blind_case_id"]: row for row in candidate_run["predictions"]}
    rows = []
    for blind_id, truth in sorted(oracle.items()):
        prediction = predictions[blind_id]
        rows.append({
            "blind_case_id": blind_id,
            "case_id": truth["case_id"],
            "construction_basis": truth["construction_basis"],
            "construction_category": truth["truth_category"],
            "construction_selected_object": truth["selected_object"],
            "construction_pragmatic_preference": truth["pragmatic_preference"],
            "construction_axis_assessment_complete": truth["axis_assessment_complete"],
            "BASELINE_V0_10_WARRANT": prediction["baseline_derived_category"],
            "BASELINE_selected_object": prediction["baseline_hard_selection"],
            "BASELINE_warrant_type": prediction["baseline_warrant_type"],
            "SEMANTIC_BASIS_V0_11": prediction["semantic_derived_category"],
            "SEMANTIC_selected_object": prediction["semantic_selected_object"],
            "SEMANTIC_selection_basis": prediction["semantic_selection_basis"],
            "SEMANTIC_pragmatic_preference": prediction["semantic_pragmatic_preference"],
            "SEMANTIC_axis_assessment_complete": prediction["semantic_axis_assessment_complete"],
            "SEMANTIC_hard_selection": prediction["semantic_hard_selection"],
            "soft_selection_downgraded": prediction["soft_selection_downgraded"],
            "semantic_receipt_available": prediction["semantic_receipt_available"],
        })
    baseline = _score(rows, "BASELINE_V0_10_WARRANT", candidate_run["arm_accounting"][BASELINE_LANE], semantic=False)
    candidate = _score(rows, "SEMANTIC_BASIS_V0_11", candidate_run["arm_accounting"][SEMANTIC_BASIS_LANE], semantic=True)
    gain = candidate["category_accuracy"] - baseline["category_accuracy"]
    multiplier = _ratio(candidate["attributed_provider_calls"], baseline["attributed_provider_calls"])
    checks = {
        "category_accuracy": candidate["category_accuracy"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_category_accuracy"],
        "basis_accuracy": candidate["basis_accuracy"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_basis_accuracy"],
        "fixed_recall": candidate["fixed_recall"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_fixed_recall"],
        "open_recall": candidate["open_recall"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_open_recall"],
        "fixed_direction_accuracy": candidate["fixed_direction_accuracy"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_fixed_direction_accuracy"],
        "hard_selection_precision": candidate["hard_selection_precision"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_hard_selection_precision"],
        "preference_alignment": candidate["preference_alignment"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_preference_alignment"],
        "completeness_rate": candidate["completeness_rate"] >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_completeness_rate"],
        "gain_over_baseline": gain >= FROZEN_DIAGNOSTIC_THRESHOLDS["minimum_gain_over_baseline"],
        "call_multiplier": multiplier <= FROZEN_DIAGNOSTIC_THRESHOLDS["maximum_call_multiplier"],
    }
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "source_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "frozen_diagnostic_thresholds": FROZEN_DIAGNOSTIC_THRESHOLDS,
        "rows": rows,
        "arm_metrics": {"BASELINE_V0_10_WARRANT": baseline, "SEMANTIC_BASIS_V0_11": candidate},
        "category_accuracy_gain_over_baseline": gain,
        "call_multiplier": multiplier,
        "construction_diagnostic_results": checks,
        "construction_diagnostic_all_passed": all(checks.values()),
        "candidate_state": "AWAITING_SEMANTIC_WARRANT_MODEL_PANEL",
        "construction_labels_are_reference": False,
        "construction_labels_are_pre_panel_diagnostics_only": True,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "real_world_ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_semantic_basis_calibration(artifact, *, corpus_artifact, candidate_run):
    if artifact != build_semantic_basis_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run):
        raise ValueError("clarification_semantic_basis_calibration_invalid")


def build_semantic_basis_analysis(calibration, *, candidate_run):
    if calibration.get("candidate_run_hash") != candidate_run.get("candidate_run_hash"):
        raise ValueError("clarification_semantic_basis_analysis_binding_invalid")
    rows = calibration["rows"]
    errors = defaultdict(list)
    for row in rows:
        if row["SEMANTIC_BASIS_V0_11"] != row["construction_category"]:
            errors["category"].append(row["case_id"])
        if row["SEMANTIC_selection_basis"] != row["construction_basis"]:
            errors["basis"].append(row["case_id"])
        if row["SEMANTIC_selected_object"] != row["construction_selected_object"]:
            errors["selected_object"].append(row["case_id"])
        if row["SEMANTIC_pragmatic_preference"] != row["construction_pragmatic_preference"]:
            errors["pragmatic_preference"].append(row["case_id"])
        if row["SEMANTIC_axis_assessment_complete"] != row["construction_axis_assessment_complete"]:
            errors["assessment_completeness"].append(row["case_id"])
    candidate = calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"]
    observations = [
        f"The candidate completed {candidate['receipt_coverage_count']}/24 case receipts with {sum(len(candidate_run['lanes'][lane]['failures']) for lane in candidate_run['lanes'])} failed batches across both arms.",
        f"Against construction labels, category accuracy was {candidate['category_accuracy']:.3f}, basis accuracy was {candidate['basis_accuracy']:.3f}, and hard-selection precision was {candidate['hard_selection_precision']:.3f}.",
        f"The equal-call category gain over the frozen v0.10 warrant baseline was {calibration['category_accuracy_gain_over_baseline']:+.3f} at a call multiplier of {calibration['call_multiplier']:.3f}.",
    ]
    interpretations = [
        "Basis errors localize whether the provider confuses entailment with default preference; category accuracy alone cannot expose that mechanism.",
        "A complete assessment may legitimately return OPEN_RIVALS, so incompleteness is not a substitute for task openness.",
        "Construction scores are diagnostic evidence only. They cannot establish semantic truth or authorize downstream clarification actions.",
    ]
    unknowns = [
        "Independent GPT-5.6 and Gemini-3.1 labels, followed by Kimi-K3 adjudication of disagreements, are still required.",
        "Transfer to action credit remains unknown because this experiment evaluates semantic receipts, not intervention outcomes.",
        "The six NO_PREFERENCE prompts are explicit neutral controls; generalization to naturally neutral requests remains untested.",
    ]
    intuition_triggers = [
        "If compositional entailment improves while lexical cases stay stable, the former hard-warrant gate was underpowered rather than merely noisy.",
        "If preference direction is accurate but selected_object is overcommitted, the main bottleneck is authority separation, not domain understanding.",
        "If NO_PREFERENCE controls pass but pragmatic defaults fail, the provider can abstain when instructed yet still lacks calibrated contextual preference.",
    ]
    commitment = {
        "analysis_version": "clarification_semantic_basis_analysis_v0_11",
        "source_calibration_hash": calibration["artifact_hash"],
        "source_candidate_run_hash": candidate_run["candidate_run_hash"],
        "observations": observations,
        "error_case_ids": {key: value for key, value in sorted(errors.items())},
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "INDEPENDENT_MODEL_PANEL",
        "candidate_state": "PRE_PANEL_DIAGNOSTIC_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_semantic_basis_analysis(analysis):
    sections = [
        ("Observations", analysis["observations"]),
        ("Interpretations", analysis["interpretations"]),
        ("Unknowns", analysis["unknowns"]),
        ("Intuition Triggers", analysis["intuition_triggers"]),
    ]
    lines = ["# Clarification Semantic-Basis v0.11 Pre-Panel Analysis", ""]
    for title, values in sections:
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend(("## Error Cases", ""))
    if analysis["error_case_ids"]:
        lines.extend(f"- `{key}`: {', '.join(value)}" for key, value in analysis["error_case_ids"].items())
    else:
        lines.append("- None against construction-only diagnostics.")
    lines.extend(("", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)


def _score(rows, arm, accounting, *, semantic):
    fixed = [row for row in rows if row["construction_category"] == "PROMPT_FIXED"]
    open_rows = [row for row in rows if row["construction_category"] == "OPEN_RIVALS"]
    predicted_fixed = [row for row in rows if row[arm] == "PROMPT_FIXED"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    result = {
        "category_accuracy": sum(row[arm] == row["construction_category"] for row in rows) / len(rows),
        "fixed_recall": sum(row[arm] == "PROMPT_FIXED" for row in fixed) / len(fixed),
        "open_recall": sum(row[arm] == "OPEN_RIVALS" for row in open_rows) / len(open_rows),
        "unresolved_rate": sum(row[arm] == "UNCERTAIN" for row in rows) / len(rows),
        "prediction_counts": dict(sorted(Counter(row[arm] for row in rows).items())),
        "attributed_provider_calls": accounting["attributed_provider_calls"],
        "attributed_tokens": tokens,
        "tokens_per_item": tokens / len(rows),
    }
    if not semantic:
        result.update({"basis_accuracy": 0.0, "fixed_direction_accuracy": sum(row["BASELINE_selected_object"] == row["construction_selected_object"] for row in fixed) / len(fixed), "hard_selection_precision": sum(row["construction_category"] == "PROMPT_FIXED" for row in predicted_fixed) / len(predicted_fixed) if predicted_fixed else 0.0, "preference_alignment": 0.0, "completeness_rate": 0.0, "receipt_coverage_count": len(rows)})
        return result
    result.update({
        "basis_accuracy": sum(row["SEMANTIC_selection_basis"] == row["construction_basis"] for row in rows) / len(rows),
        "fixed_direction_accuracy": sum(row["SEMANTIC_hard_selection"] == row["construction_selected_object"] for row in fixed) / len(fixed),
        "hard_selection_precision": sum(row["construction_basis"] in HARD_SELECTION_BASES for row in predicted_fixed) / len(predicted_fixed) if predicted_fixed else 0.0,
        "preference_alignment": sum(row["SEMANTIC_pragmatic_preference"] == row["construction_pragmatic_preference"] for row in rows) / len(rows),
        "completeness_rate": sum(row["SEMANTIC_axis_assessment_complete"] for row in rows) / len(rows),
        "receipt_coverage_count": sum(row["semantic_receipt_available"] for row in rows),
        "basis_counts": dict(sorted(Counter(row["SEMANTIC_selection_basis"] for row in rows).items())),
        "soft_selection_downgrade_count": sum(row["soft_selection_downgraded"] for row in rows),
    })
    return result


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else float("inf")
