"""Diagnostic v0.13 recalibration against the coherence-gated model panel."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_fresh_panel import validate_joint_fresh_reference
from .clarification_joint_fresh_runtime import validate_joint_fresh_run
from .clarification_joint_holdout import validate_joint_holdout_artifact
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_joint_fresh_panel_calibration_v0_13"
AXES = ("SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")


def build_joint_fresh_panel_calibration(*, corpus_artifact, run, panel_reference):
    validate_joint_holdout_artifact(corpus_artifact); validate_joint_fresh_run(run, corpus_artifact=corpus_artifact); validate_joint_fresh_reference(panel_reference)
    reference = {label["conflict_id"]: label["criteria"] for label in panel_reference["labels"]}; oracle = corpus_artifact["private_oracle"]["bindings"]
    conflicts = {item["conflict_id"]: item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]}; predictions = {item["decision"]["conflict_id"]: item for judgment in run["judgments"] for item in judgment["decisions"]}
    if set(reference) != set(conflicts): raise ValueError("joint_fresh_panel_calibration_surface_invalid")
    incoherent_ids = {item["conflict_id"] for item in panel_reference["cross_axis_inconsistency_records"]}; rows = []
    for conflict_id in sorted(reference):
        ref = reference[conflict_id]; item = predictions.get(conflict_id); decision = item["decision"] if item else None
        reference_actions = {axis: "REOPEN" if ref[axis] != conflicts[conflict_id]["locked_consensus_axes"][axis] else "PRESERVE" for axis in AXES}
        reference_basis_action = "REVISE" if ref["SELECTION_BASIS"] != conflicts[conflict_id]["local_basis_outcome"]["selection_basis"] else "PRESERVE"
        candidate_tuple = {"SELECTED_OBJECT": decision["final_selected_object"], "SELECTION_BASIS": decision["final_selection_basis"], "PRAGMATIC_PREFERENCE": decision["final_pragmatic_preference"], "AXIS_ASSESSMENT_COMPLETE": decision["final_assessment_completeness"]} if decision else None
        rows.append({"conflict_id": conflict_id, "case_id": oracle[conflict_id]["case_id"], "reference_tuple": ref, "reference_tuple_coherent": conflict_id not in incoherent_ids, "reference_consensus_axis_actions": reference_actions, "reference_local_basis_action": reference_basis_action, "candidate_tuple": candidate_tuple, "candidate_consensus_axis_actions": decision["consensus_axis_actions"] if decision else None, "candidate_local_basis_action": decision["local_basis_action"] if decision else None, "candidate_runtime_assessment": item["runtime_assessment"] if item else None, "construction_truth": oracle[conflict_id]["construction_truth"]})
    metrics = _metrics(rows, run); construction_alignment = _construction_alignment(rows)
    commitment = {"calibration_version": CALIBRATION_VERSION, "source_artifact_hash": corpus_artifact["artifact_hash"], "source_run_hash": run["run_hash"], "source_panel_reference_hash": panel_reference["artifact_hash"], "panel_reference_state": panel_reference["candidate_state"], "panel_reference_cross_axis_coherence_passed": panel_reference["cross_axis_coherence_passed"], "rows": rows, "candidate_metrics": metrics, "construction_panel_alignment": construction_alignment, "transfer_recommendation": "REJECT_JOINT_COORDINATOR_TRANSFER", "candidate_state": "JOINT_FRESH_PANEL_RECALIBRATION_DIAGNOSTIC_ONLY", "action_credit_authority": False, "selection_authority": False, "retention_authority": False, "production_authority": False}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_fresh_panel_calibration(artifact, *, corpus_artifact, run, panel_reference):
    if artifact != build_joint_fresh_panel_calibration(corpus_artifact=corpus_artifact, run=run, panel_reference=panel_reference): raise ValueError("joint_fresh_panel_calibration_invalid")


def build_joint_fresh_final_analysis(calibration, *, panel_reference):
    if calibration.get("source_panel_reference_hash") != panel_reference.get("artifact_hash"): raise ValueError("joint_fresh_final_analysis_binding_invalid")
    m = calibration["candidate_metrics"]
    observations = [f"The 96-cell model-panel reference contains {panel_reference['cross_axis_inconsistency_count']} incoherent tuples and is diagnostic-only.", f"DeepSeek full-tuple accuracy is {m['full_tuple_accuracy']:.3f}; on the {m['coherent_reference_count']} coherent reference tuples it is {m['coherent_subset_tuple_accuracy']:.3f}.", f"Consensus-action accuracy is {m['consensus_action_accuracy']:.3f}, preserve specificity {m['preserve_specificity']:.3f}, reopen recall {m['reopen_recall']:.3f}, and local-basis action accuracy {m['local_basis_action_accuracy']:.3f}.", f"Axis accuracies are selected object {m['selected_object_accuracy']:.3f}, basis {m['selection_basis_accuracy']:.3f}, preference {m['pragmatic_preference_accuracy']:.3f}, and completeness {m['assessment_completeness_accuracy']:.3f}."]
    interpretations = ["Panel-derived actions confirm whether the apparent preserve/reopen asymmetry survives removal of construction labels.", "Criterion-local adjudication again creates globally impossible tuples, so full-tuple transfer must remain blocked even when individual axis scores are informative.", "High preserve specificity paired with low reopen recall is evidence of consensus anchoring rather than cautious calibration when clear semantic counterevidence is present."]
    unknowns = ["Five incoherent reference tuples require joint tuple adjudication before a complete governance reference exists.", "Model-panel labels are not human gold or real-world truth.", "Downstream clarification-action utility remains disconnected."]
    intuition_triggers = ["Repeated coherence failure suggests the adjudication unit should be the semantic object, not the cell.", "Stable judge-specific error orientations can support role-aware routing, but only after out-of-sample calibration.", "Consensus reopening may need an explicit counterevidence receipt rather than a generic coordinator instruction."]
    commitment = {"analysis_version": "clarification_joint_fresh_final_analysis_v0_13", "source_calibration_hash": calibration["artifact_hash"], "source_panel_reference_hash": panel_reference["artifact_hash"], "observations": observations, "interpretations": interpretations, "unknowns": unknowns, "intuition_triggers": intuition_triggers, "next_required_evidence": "JOINT_TUPLE_ADJUDICATION_NOT_CELL_ADJUDICATION", "candidate_state": "PANEL_RECALIBRATION_DIAGNOSTIC_ONLY"}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_joint_fresh_final_analysis(analysis):
    lines = ["# Clarification Joint Coordinator v0.13 Final Panel Analysis", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns"), ("Intuition Triggers", "intuition_triggers")):
        lines.extend((f"## {title}", "")); lines.extend(f"- {value}" for value in analysis[key]); lines.append("")
    lines.extend((f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", "")); return "\n".join(lines)


def _metrics(rows, run):
    available = [row for row in rows if row["candidate_tuple"]]; coherent = [row for row in rows if row["reference_tuple_coherent"]]
    expected_preserve = expected_reopen = correct_preserve = correct_reopen = action_correct = 0
    for row in available:
        for axis in AXES:
            expected = row["reference_consensus_axis_actions"][axis]; actual = row["candidate_consensus_axis_actions"][axis]; action_correct += actual == expected
            if expected == "PRESERVE": expected_preserve += 1; correct_preserve += actual == expected
            else: expected_reopen += 1; correct_reopen += actual == expected
    return {"full_tuple_accuracy": sum(row["candidate_tuple"] == row["reference_tuple"] for row in rows) / len(rows), "coherent_reference_count": len(coherent), "coherent_subset_tuple_accuracy": sum(row["candidate_tuple"] == row["reference_tuple"] for row in coherent) / len(coherent), "selected_object_accuracy": _axis_accuracy(rows, "SELECTED_OBJECT"), "selection_basis_accuracy": _axis_accuracy(rows, "SELECTION_BASIS"), "pragmatic_preference_accuracy": _axis_accuracy(rows, "PRAGMATIC_PREFERENCE"), "assessment_completeness_accuracy": _axis_accuracy(rows, "AXIS_ASSESSMENT_COMPLETE"), "consensus_action_accuracy": action_correct / (len(available) * len(AXES)), "preserve_specificity": correct_preserve / expected_preserve if expected_preserve else 0.0, "reopen_recall": correct_reopen / expected_reopen if expected_reopen else 0.0, "reference_preserve_count": expected_preserve, "reference_reopen_count": expected_reopen, "local_basis_action_accuracy": sum(row["candidate_local_basis_action"] == row["reference_local_basis_action"] for row in available) / len(available), "candidate_mechanical_state_counts": dict(sorted(Counter(row["candidate_runtime_assessment"]["mechanical_state"] for row in available).items())), "accounting": run["accounting"]}


def _axis_accuracy(rows, axis): return sum(row["candidate_tuple"] and row["candidate_tuple"][axis] == row["reference_tuple"][axis] for row in rows) / len(rows)


def _construction_alignment(rows):
    return {axis: sum(row["construction_truth"][axis] == row["reference_tuple"][axis] for row in rows) / len(rows) for axis in ("SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")}
