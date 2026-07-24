"""Construction-only diagnostics for fresh joint coordination v0.13."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_fresh_runtime import validate_joint_fresh_run
from .clarification_joint_holdout import validate_joint_holdout_artifact
from .provider_telemetry import hash_payload


EVAL_VERSION = "clarification_joint_fresh_eval_v0_13"
FROZEN_THRESHOLDS = {"minimum_tuple_accuracy": 0.75, "minimum_target_action_accuracy": 0.75, "minimum_coherence_rate": 0.95, "minimum_action_declaration_valid_rate": 0.95, "minimum_gain_over_preserve_all": 0.20, "maximum_false_reopen_rate": 0.15, "maximum_failed_batch_rate": 0.05}


def build_joint_fresh_report(*, corpus_artifact, run):
    validate_joint_holdout_artifact(corpus_artifact)
    validate_joint_fresh_run(run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    conflicts = {item["conflict_id"]: item for batch in corpus_artifact["public_surface"]["batches"] for item in batch["conflicts"]}
    predictions = {item["decision"]["conflict_id"]: item for judgment in run["judgments"] for item in judgment["decisions"]}
    rows = []
    for conflict_id, truth_record in sorted(oracle.items()):
        truth = truth_record["construction_truth"]
        conflict = conflicts[conflict_id]
        item = predictions.get(conflict_id)
        decision = item["decision"] if item else None
        assessment = item["runtime_assessment"] if item else None
        expected_actions = {axis: "REOPEN" if truth[axis] != conflict["locked_consensus_axes"][axis] else "PRESERVE" for axis in ("SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE")}
        expected_basis_action = "REVISE" if truth["SELECTION_BASIS"] != conflict["local_basis_outcome"]["selection_basis"] else "PRESERVE"
        rows.append({
            "conflict_id": conflict_id, "case_id": truth_record["case_id"], "target_axis": truth_record["target_axis"], "target_action": truth_record["target_action"],
            "construction_truth": truth, "expected_consensus_axis_actions": expected_actions, "expected_local_basis_action": expected_basis_action,
            "candidate_tuple": _tuple(decision) if decision else None,
            "candidate_consensus_axis_actions": decision["consensus_axis_actions"] if decision else None,
            "candidate_local_basis_action": decision["local_basis_action"] if decision else None,
            "runtime_assessment": assessment,
        })
    candidate = _candidate_metrics(rows, run)
    baseline = _preserve_all_metrics(rows, conflicts)
    gain = candidate["tuple_accuracy"] - baseline["tuple_accuracy"]
    failed_rate = len(run["failures"]) / len(corpus_artifact["public_surface"]["batches"])
    checks = {
        "tuple_accuracy": candidate["tuple_accuracy"] >= FROZEN_THRESHOLDS["minimum_tuple_accuracy"],
        "target_action_accuracy": candidate["target_action_accuracy"] >= FROZEN_THRESHOLDS["minimum_target_action_accuracy"],
        "coherence_rate": candidate["coherence_rate"] >= FROZEN_THRESHOLDS["minimum_coherence_rate"],
        "action_declaration_valid_rate": candidate["action_declaration_valid_rate"] >= FROZEN_THRESHOLDS["minimum_action_declaration_valid_rate"],
        "gain_over_preserve_all": gain >= FROZEN_THRESHOLDS["minimum_gain_over_preserve_all"],
        "false_reopen_rate": candidate["false_reopen_rate"] <= FROZEN_THRESHOLDS["maximum_false_reopen_rate"],
        "failed_batch_rate": failed_rate <= FROZEN_THRESHOLDS["maximum_failed_batch_rate"],
    }
    commitment = {
        "eval_version": EVAL_VERSION, "source_artifact_hash": corpus_artifact["artifact_hash"], "source_run_hash": run["run_hash"],
        "frozen_thresholds": FROZEN_THRESHOLDS, "rows": rows,
        "preserve_all_baseline": baseline, "candidate_metrics": candidate, "tuple_accuracy_gain_over_preserve_all": gain,
        "failed_batch_rate": failed_rate, "construction_diagnostic_results": checks, "construction_diagnostic_all_passed": all(checks.values()),
        "candidate_state": "AWAITING_JOINT_COORDINATOR_MODEL_PANEL", "construction_labels_are_reference": False,
        "generalization_claim": False, "action_credit_authority": False, "selection_authority": False, "retention_authority": False, "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_joint_fresh_report(report, *, corpus_artifact, run):
    if report != build_joint_fresh_report(corpus_artifact=corpus_artifact, run=run):
        raise ValueError("joint_fresh_report_invalid")


def build_joint_fresh_analysis(report):
    candidate, baseline = report["candidate_metrics"], report["preserve_all_baseline"]
    observations = [
        f"The fresh coordinator completed {candidate['receipt_coverage_count']}/24 decisions with a failed-batch rate of {report['failed_batch_rate']:.3f}.",
        f"Construction-only tuple accuracy was {candidate['tuple_accuracy']:.3f} versus {baseline['tuple_accuracy']:.3f} for preserve-all, a gain of {report['tuple_accuracy_gain_over_preserve_all']:+.3f}.",
        f"Target-action accuracy was {candidate['target_action_accuracy']:.3f}, coherence rate {candidate['coherence_rate']:.3f}, declaration-valid rate {candidate['action_declaration_valid_rate']:.3f}, and false-reopen rate {candidate['false_reopen_rate']:.3f}.",
        f"Target preservation accuracy was {candidate['target_preserve_accuracy']:.3f}, while target reopen-or-revise accuracy was {candidate['target_reopen_or_revise_accuracy']:.3f}; consensus-axis reopen recall was {candidate['reopen_recall']:.3f}.",
    ]
    interpretations = [
        "Removing the overall disposition largely fixes governance declaration syntax, but it does not produce reliable semantic coordination.",
        "The gap between preservation and reopen-or-revise accuracy shows strong consensus anchoring rather than calibrated evidence priority.",
        "Construction-only scores localize behavior but cannot establish final semantic truth without an independent model panel.",
    ]
    unknowns = [
        "Independent selected-object, basis, preference, completeness, and axis-action labels remain outstanding.",
        "The incomplete opaque-candidate controls are synthetic and do not establish natural incompleteness behavior.",
        "Action utility and transfer to unseen domain distributions remain disconnected.",
    ]
    intuition_triggers = [
        "If action declarations become reliable while tuple semantics remain weak, governance encoding was fixed but cognition was not.",
        "If preserve specificity is high and reopen recall low, consensus has become an anchoring prior rather than calibrated evidence.",
        "Per-axis disagreement patterns can become an organizational credit signal only after panel validation.",
    ]
    commitment = {"analysis_version": "clarification_joint_fresh_analysis_v0_13", "source_report_hash": report["artifact_hash"], "observations": observations, "interpretations": interpretations, "unknowns": unknowns, "intuition_triggers": intuition_triggers, "next_required_evidence": "INDEPENDENT_JOINT_COORDINATOR_MODEL_PANEL", "candidate_state": "PRE_PANEL_DIAGNOSTIC_ONLY"}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_joint_fresh_analysis(analysis):
    lines = ["# Clarification Joint Coordinator v0.13 Pre-Panel Analysis", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns"), ("Intuition Triggers", "intuition_triggers")):
        lines.extend((f"## {title}", "")); lines.extend(f"- {value}" for value in analysis[key]); lines.append("")
    lines.extend((f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)


def _tuple(decision):
    return {"SELECTED_OBJECT": decision["final_selected_object"], "SELECTION_BASIS": decision["final_selection_basis"], "PRAGMATIC_PREFERENCE": decision["final_pragmatic_preference"], "AXIS_ASSESSMENT_COMPLETE": decision["final_assessment_completeness"]}


def _candidate_metrics(rows, run):
    available = [row for row in rows if row["candidate_tuple"]]
    expected_preserve, false_reopen = 0, 0
    expected_reopen, true_reopen = 0, 0
    for row in available:
        for axis, expected in row["expected_consensus_axis_actions"].items():
            actual = row["candidate_consensus_axis_actions"][axis]
            if expected == "PRESERVE": expected_preserve += 1; false_reopen += actual == "REOPEN"
            else: expected_reopen += 1; true_reopen += actual == "REOPEN"
    by_target = {}
    for axis in ("SELECTION_BASIS", "SELECTED_OBJECT", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"):
        group = [row for row in rows if row["target_axis"] == axis]
        by_target[axis] = sum(_target_action_correct(row) for row in group) / len(group)
    target_preserve = [row for row in rows if row["target_action"] == "PRESERVE"]
    target_change = [row for row in rows if row["target_action"] != "PRESERVE"]
    return {
        "tuple_accuracy": sum(row["candidate_tuple"] == row["construction_truth"] for row in rows) / len(rows),
        "selected_object_accuracy": sum(row["candidate_tuple"] and row["candidate_tuple"]["SELECTED_OBJECT"] == row["construction_truth"]["SELECTED_OBJECT"] for row in rows) / len(rows),
        "selection_basis_accuracy": sum(row["candidate_tuple"] and row["candidate_tuple"]["SELECTION_BASIS"] == row["construction_truth"]["SELECTION_BASIS"] for row in rows) / len(rows),
        "pragmatic_preference_accuracy": sum(row["candidate_tuple"] and row["candidate_tuple"]["PRAGMATIC_PREFERENCE"] == row["construction_truth"]["PRAGMATIC_PREFERENCE"] for row in rows) / len(rows),
        "assessment_completeness_accuracy": sum(row["candidate_tuple"] and row["candidate_tuple"]["AXIS_ASSESSMENT_COMPLETE"] == row["construction_truth"]["AXIS_ASSESSMENT_COMPLETE"] for row in rows) / len(rows),
        "target_action_accuracy": sum(_target_action_correct(row) for row in rows) / len(rows),
        "target_action_accuracy_by_axis": by_target,
        "target_preserve_accuracy": sum(_target_action_correct(row) for row in target_preserve) / len(target_preserve),
        "target_reopen_or_revise_accuracy": sum(_target_action_correct(row) for row in target_change) / len(target_change),
        "coherence_rate": sum(row["runtime_assessment"] and row["runtime_assessment"]["coherent"] for row in rows) / len(rows),
        "action_declaration_valid_rate": sum(row["runtime_assessment"] and row["runtime_assessment"]["action_declaration_valid"] for row in rows) / len(rows),
        "false_reopen_rate": false_reopen / expected_preserve if expected_preserve else 0.0,
        "reopen_recall": true_reopen / expected_reopen if expected_reopen else 0.0,
        "expected_preserve_axis_count": expected_preserve, "expected_reopen_axis_count": expected_reopen,
        "mechanical_state_counts": dict(sorted(Counter(row["runtime_assessment"]["mechanical_state"] if row["runtime_assessment"] else "UNAVAILABLE" for row in rows).items())),
        "receipt_coverage_count": len(available), "accounting": run["accounting"],
    }


def _target_action_correct(row):
    if not row["candidate_tuple"] or not row["runtime_assessment"]["action_declaration_valid"]:
        return False
    axis = row["target_axis"]
    if axis == "SELECTION_BASIS":
        return row["candidate_local_basis_action"] == row["expected_local_basis_action"]
    return row["candidate_consensus_axis_actions"][axis] == row["expected_consensus_axis_actions"][axis]


def _preserve_all_metrics(rows, conflicts):
    correct = 0
    for row in rows:
        conflict = conflicts[row["conflict_id"]]
        baseline = {**conflict["locked_consensus_axes"], "SELECTION_BASIS": conflict["local_basis_outcome"]["selection_basis"]}
        correct += baseline == row["construction_truth"]
    return {"tuple_accuracy": correct / len(rows), "target_action_accuracy": 0.5, "strategy": "PRESERVE_ALL_CONSENSUS_AND_LOCAL_BASIS"}
