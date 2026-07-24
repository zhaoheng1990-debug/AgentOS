"""Diagnostic-only recalibration of v0.10 against the model-panel reference."""

from __future__ import annotations

from collections import Counter

from .clarification_warrant_calibration import validate_warrant_calibration
from .clarification_warrant_holdout import validate_warrant_holdout_artifact
from .clarification_warrant_panel import validate_warrant_reference
from .clarification_warrant_runtime import validate_warrant_run
from .provider_telemetry import hash_payload


AUDIT_VERSION = "clarification_warrant_panel_recalibration_v0_10"


def build_warrant_panel_recalibration(*, corpus_artifact, candidate_run, frozen_calibration, panel_reference):
    validate_warrant_holdout_artifact(corpus_artifact)
    validate_warrant_run(candidate_run, corpus_artifact=corpus_artifact)
    validate_warrant_calibration(frozen_calibration, corpus_artifact=corpus_artifact, candidate_run=candidate_run)
    validate_warrant_reference(panel_reference)
    panel = {item["blind_case_id"]: item for item in panel_reference["labels"]}
    frozen = {item["blind_case_id"]: item for item in frozen_calibration["rows"]}
    if set(panel) != set(frozen):
        raise ValueError("warrant_panel_recalibration_surface_invalid")
    rows = []
    for blind_id in sorted(panel):
        source = frozen[blind_id]
        criteria = panel[blind_id]["criteria"]
        panel_category = _category(criteria["EXPLICIT_SELECTION"])
        deepseek_completeness = "COMPLETE" if source["WARRANT_assessment_status"] == "RESOLVED" else "INCOMPLETE"
        rows.append({
            "blind_case_id": blind_id,
            "construction": source["construction"],
            "constructed_explicit_selection": source["truth_explicit_selection"],
            "constructed_pragmatic_preference": source["truth_pragmatic_preference"],
            "panel_explicit_selection": criteria["EXPLICIT_SELECTION"],
            "panel_pragmatic_preference": criteria["PRAGMATIC_PREFERENCE"],
            "panel_assessment_completeness": criteria["ASSESSMENT_COMPLETENESS"],
            "panel_runtime_category": panel_category,
            "deepseek_explicit_selection": source["WARRANT_explicit_selection"],
            "deepseek_pragmatic_preference": source["WARRANT_pragmatic_preference"],
            "deepseek_assessment_completeness": deepseek_completeness,
            "deepseek_warrant_type": source["WARRANT_type"],
            "deepseek_runtime_category": source["EXPLICIT_WARRANT"],
            "deepseek_hard_selection": source["WARRANT_hard_selection"],
        })
    metrics = _metrics(rows)
    errors = {
        "explicit_selection": _errors(rows, "deepseek_explicit_selection", "panel_explicit_selection"),
        "pragmatic_preference": _errors(rows, "deepseek_pragmatic_preference", "panel_pragmatic_preference"),
        "assessment_completeness": _errors(rows, "deepseek_assessment_completeness", "panel_assessment_completeness"),
        "runtime_category": _errors(rows, "deepseek_runtime_category", "panel_runtime_category"),
    }
    commitment = {
        "audit_version": AUDIT_VERSION,
        "source_corpus_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "frozen_calibration_hash": frozen_calibration["artifact_hash"],
        "panel_reference_hash": panel_reference["artifact_hash"],
        "rows": rows,
        "metrics": metrics,
        "error_clusters": errors,
        "panel_explicit_counts": dict(sorted(Counter(row["panel_explicit_selection"] for row in rows).items())),
        "panel_preference_counts": dict(sorted(Counter(row["panel_pragmatic_preference"] for row in rows).items())),
        "panel_completeness_counts": dict(sorted(Counter(row["panel_assessment_completeness"] for row in rows).items())),
        "candidate_state": "WARRANT_PANEL_RECALIBRATION_DIAGNOSTIC_ONLY",
        "transfer_recommendation": "REJECT_WARRANT_TRANSFER" if errors["runtime_category"] else "REQUIRE_FRESH_PREREGISTERED_TRANSFER_TEST",
        "post_hoc_admission_gate": False,
        "ground_truth_claim": False,
        "human_gold_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_panel_recalibration(artifact, *, corpus_artifact, candidate_run, frozen_calibration, panel_reference):
    if artifact != build_warrant_panel_recalibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run, frozen_calibration=frozen_calibration, panel_reference=panel_reference):
        raise ValueError("warrant_panel_recalibration_invalid")


def _category(explicit_selection):
    if explicit_selection in ("CANDIDATE_A", "CANDIDATE_B"):
        return "PROMPT_FIXED"
    if explicit_selection == "NONE":
        return "OPEN_RIVALS"
    return "UNCERTAIN"


def _metrics(rows):
    total = len(rows)
    fixed = [row for row in rows if row["panel_runtime_category"] == "PROMPT_FIXED"]
    opened = [row for row in rows if row["panel_runtime_category"] == "OPEN_RIVALS"]
    predicted_fixed = [row for row in rows if row["deepseek_runtime_category"] == "PROMPT_FIXED"]
    return {
        "explicit_selection_accuracy": sum(row["deepseek_explicit_selection"] == row["panel_explicit_selection"] for row in rows) / total,
        "pragmatic_preference_accuracy": sum(row["deepseek_pragmatic_preference"] == row["panel_pragmatic_preference"] for row in rows) / total,
        "assessment_completeness_accuracy": sum(row["deepseek_assessment_completeness"] == row["panel_assessment_completeness"] for row in rows) / total,
        "runtime_category_accuracy": sum(row["deepseek_runtime_category"] == row["panel_runtime_category"] for row in rows) / total,
        "panel_fixed_recall": sum(row["deepseek_runtime_category"] == "PROMPT_FIXED" for row in fixed) / len(fixed),
        "panel_open_recall": sum(row["deepseek_runtime_category"] == "OPEN_RIVALS" for row in opened) / len(opened),
        "hard_warrant_precision": sum(row["panel_runtime_category"] == "PROMPT_FIXED" for row in predicted_fixed) / len(predicted_fixed) if predicted_fixed else 0.0,
        "unresolved_rate": sum(row["deepseek_runtime_category"] == "UNCERTAIN" for row in rows) / total,
        "constructed_explicit_alignment": sum(row["constructed_explicit_selection"] == row["panel_explicit_selection"] for row in rows) / total,
        "constructed_pragmatic_alignment": sum(row["constructed_pragmatic_preference"] == row["panel_pragmatic_preference"] for row in rows) / total,
    }


def _errors(rows, predicted, reference):
    return [{"blind_case_id": row["blind_case_id"], "construction": row["construction"], "predicted": row[predicted], "reference": row[reference]} for row in rows if row[predicted] != row[reference]]
