"""Diagnostic recalibration of DeepSeek v0.11 against the model panel."""

from __future__ import annotations

from collections import Counter, defaultdict

from .clarification_semantic_basis_panel import validate_semantic_basis_reference
from .clarification_semantic_basis_runtime import BASELINE_LANE, SEMANTIC_BASIS_LANE, validate_semantic_basis_run
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_semantic_basis_panel_calibration_v0_11"


def build_semantic_basis_panel_calibration(*, corpus_artifact, candidate_run, panel_reference):
    validate_semantic_basis_run(candidate_run, corpus_artifact=corpus_artifact)
    validate_semantic_basis_reference(panel_reference)
    reference = {label["blind_case_id"]: label for label in panel_reference["labels"]}
    predictions = {row["blind_case_id"]: row for row in candidate_run["predictions"]}
    if set(reference) != set(predictions):
        raise ValueError("semantic_basis_panel_calibration_surface_invalid")
    rows = []
    for blind_id in sorted(reference):
        criteria = reference[blind_id]["criteria"]
        prediction = predictions[blind_id]
        reference_category = _reference_category(criteria["SELECTED_OBJECT"], criteria["AXIS_ASSESSMENT_COMPLETE"])
        rows.append({
            "blind_case_id": blind_id,
            "reference_selected_object": criteria["SELECTED_OBJECT"],
            "reference_selection_basis": criteria["SELECTION_BASIS"],
            "reference_pragmatic_preference": criteria["PRAGMATIC_PREFERENCE"],
            "reference_assessment_completeness": criteria["AXIS_ASSESSMENT_COMPLETE"],
            "reference_category": reference_category,
            "BASELINE_V0_10_WARRANT": prediction["baseline_derived_category"],
            "SEMANTIC_BASIS_V0_11": prediction["semantic_derived_category"],
            "candidate_selected_object": prediction["semantic_selected_object"],
            "candidate_selection_basis": prediction["semantic_selection_basis"],
            "candidate_pragmatic_preference": prediction["semantic_pragmatic_preference"],
            "candidate_assessment_completeness": "COMPLETE" if prediction["semantic_axis_assessment_complete"] else "INCOMPLETE",
            "candidate_hard_selection": prediction["semantic_hard_selection"],
        })
    baseline = _score(rows, "BASELINE_V0_10_WARRANT", candidate_run["arm_accounting"][BASELINE_LANE], semantic=False)
    candidate = _score(rows, "SEMANTIC_BASIS_V0_11", candidate_run["arm_accounting"][SEMANTIC_BASIS_LANE], semantic=True)
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "source_candidate_run_hash": candidate_run["candidate_run_hash"],
        "source_panel_reference_hash": panel_reference["artifact_hash"],
        "panel_reference_state": panel_reference["candidate_state"],
        "panel_reference_cross_axis_coherence_passed": panel_reference["cross_axis_coherence_passed"],
        "rows": rows,
        "arm_metrics": {"BASELINE_V0_10_WARRANT": baseline, "SEMANTIC_BASIS_V0_11": candidate},
        "category_accuracy_gain_over_baseline": candidate["category_accuracy"] - baseline["category_accuracy"],
        "call_multiplier": _ratio(candidate["attributed_provider_calls"], baseline["attributed_provider_calls"]),
        "transfer_recommendation": "REJECT_SEMANTIC_BASIS_TRANSFER",
        "candidate_state": "SEMANTIC_BASIS_PANEL_RECALIBRATION_DIAGNOSTIC_ONLY",
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_semantic_basis_panel_calibration(artifact, *, corpus_artifact, candidate_run, panel_reference):
    if artifact != build_semantic_basis_panel_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run, panel_reference=panel_reference):
        raise ValueError("semantic_basis_panel_calibration_invalid")


def build_semantic_basis_panel_analysis(calibration, *, panel_reference):
    if calibration.get("source_panel_reference_hash") != panel_reference.get("artifact_hash"):
        raise ValueError("semantic_basis_panel_analysis_binding_invalid")
    candidate = calibration["arm_metrics"]["SEMANTIC_BASIS_V0_11"]
    errors = defaultdict(list)
    for row in calibration["rows"]:
        if row["candidate_selected_object"] != row["reference_selected_object"]:
            errors["selected_object"].append(row["blind_case_id"])
        if row["candidate_selection_basis"] != row["reference_selection_basis"]:
            errors["selection_basis"].append(row["blind_case_id"])
        if row["candidate_pragmatic_preference"] != row["reference_pragmatic_preference"]:
            errors["pragmatic_preference"].append(row["blind_case_id"])
    observations = [
        f"The final 96-cell panel reference contains {panel_reference['cross_axis_inconsistency_count']} cross-axis inconsistencies and is therefore diagnostic-only.",
        f"DeepSeek selected-object and Runtime-category accuracy are both {candidate['selected_object_accuracy']:.3f} and {candidate['category_accuracy']:.3f}; hard-selection precision is {candidate['hard_selection_precision']:.3f}.",
        f"Selection-basis accuracy is {candidate['selection_basis_accuracy']:.3f}, pragmatic-preference accuracy is {candidate['pragmatic_preference_accuracy']:.3f}, and assessment-completeness accuracy is {candidate['assessment_completeness_accuracy']:.3f}.",
        f"The equal-call category gain over the valid v0.10 baseline is {calibration['category_accuracy_gain_over_baseline']:+.3f}.",
    ]
    interpretations = [
        "Independent agreement on selected object confirms that DeepSeek over-promotes generic contextual defaults into hard semantic selection.",
        "Criterion-local adjudication can create a globally incoherent receipt even when every individual decision is schema-valid; semantic panels need a post-adjudication coherence gate.",
        "The high basis score is not sufficient for transfer because two K3 compositional labels conflict with the panel's selected-object labels.",
    ]
    unknowns = [
        "A coherent resolution of the three conflicting K3 cells is still absent; no axis should be silently overwritten.",
        "The value of these semantic distinctions for clarification actions remains unmeasured.",
        "Natural no-preference cases without explicit neutral wording remain outside this holdout.",
    ]
    intuition_triggers = [
        "The next useful architecture may be joint receipt adjudication rather than independent cell adjudication, because cognition lives partly in relations among axes.",
        "A coordinator should preserve local expert judgments but reject globally impossible combinations before they acquire Runtime authority.",
        "The group produced more knowledge than a scalar vote: agreement identified the overcommitment, while disagreement exposed a missing coordination invariant.",
    ]
    commitment = {
        "analysis_version": "clarification_semantic_basis_panel_analysis_v0_11",
        "source_calibration_hash": calibration["artifact_hash"],
        "source_panel_reference_hash": panel_reference["artifact_hash"],
        "observations": observations,
        "error_blind_case_ids": {key: value for key, value in sorted(errors.items())},
        "reference_coherence_records": panel_reference["cross_axis_inconsistency_records"],
        "interpretations": interpretations,
        "unknowns": unknowns,
        "intuition_triggers": intuition_triggers,
        "next_required_evidence": "JOINT_CROSS_AXIS_COHERENCE_RESOLUTION",
        "candidate_state": "PANEL_RECALIBRATION_DIAGNOSTIC_ONLY",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_semantic_basis_panel_analysis(analysis):
    lines = ["# Clarification Semantic-Basis v0.11 Final Panel Analysis", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns"), ("Intuition Triggers", "intuition_triggers")):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend(("## Coherence Violations", ""))
    lines.extend(f"- `{record['blind_case_id']}`: `{record['violation']}`" for record in analysis["reference_coherence_records"])
    lines.extend(("", f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)


def _reference_category(selected_object, completeness):
    if completeness != "COMPLETE" or selected_object == "UNCERTAIN":
        return "UNCERTAIN"
    return "PROMPT_FIXED" if selected_object in ("CANDIDATE_A", "CANDIDATE_B") else "OPEN_RIVALS"


def _score(rows, arm, accounting, *, semantic):
    fixed = [row for row in rows if row["reference_category"] == "PROMPT_FIXED"]
    open_rows = [row for row in rows if row["reference_category"] == "OPEN_RIVALS"]
    predicted_fixed = [row for row in rows if row[arm] == "PROMPT_FIXED"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    result = {
        "category_accuracy": sum(row[arm] == row["reference_category"] for row in rows) / len(rows),
        "fixed_recall": sum(row[arm] == "PROMPT_FIXED" for row in fixed) / len(fixed),
        "open_recall": sum(row[arm] == "OPEN_RIVALS" for row in open_rows) / len(open_rows),
        "unresolved_rate": sum(row[arm] == "UNCERTAIN" for row in rows) / len(rows),
        "prediction_counts": dict(sorted(Counter(row[arm] for row in rows).items())),
        "attributed_provider_calls": accounting["attributed_provider_calls"],
        "attributed_tokens": tokens,
    }
    if semantic:
        result.update({
            "selected_object_accuracy": sum(row["candidate_selected_object"] == row["reference_selected_object"] for row in rows) / len(rows),
            "selection_basis_accuracy": sum(row["candidate_selection_basis"] == row["reference_selection_basis"] for row in rows) / len(rows),
            "pragmatic_preference_accuracy": sum(row["candidate_pragmatic_preference"] == row["reference_pragmatic_preference"] for row in rows) / len(rows),
            "assessment_completeness_accuracy": sum(row["candidate_assessment_completeness"] == row["reference_assessment_completeness"] for row in rows) / len(rows),
            "fixed_direction_accuracy": sum(row["candidate_hard_selection"] == row["reference_selected_object"] for row in fixed) / len(fixed),
            "hard_selection_precision": sum(row["reference_category"] == "PROMPT_FIXED" for row in predicted_fixed) / len(predicted_fixed) if predicted_fixed else 0.0,
        })
    return result


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else float("inf")
