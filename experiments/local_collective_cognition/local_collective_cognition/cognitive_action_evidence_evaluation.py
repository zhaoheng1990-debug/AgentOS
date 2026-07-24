"""Freeze the v0.19 external reference and evaluate evidence calibration."""

from __future__ import annotations

from collections import Counter

from .cognitive_action_evidence_calibrator import ARMS
from .cognitive_action_evidence_panel import (
    ALLOWED_STATES,
    CRITERIA,
    selective_tuple_violations,
    validate_evidence_adjudication_response,
    validate_evidence_external_adjudication,
)
from .provider_telemetry import hash_payload


EVIDENCE_REFERENCE_VERSION = "cognitive_action_evidence_external_reference_v0_19"
EVIDENCE_EVALUATION_VERSION = "cognitive_action_evidence_external_evaluation_v0_19"
AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("evidence_state", "EVIDENCE_STATE"),
    ("assessment_process_state", "ASSESSMENT_PROCESS_STATE"),
)


def build_evidence_external_reference(*, adjudication_pack, adjudication_manifest, adjudication_response):
    validate_evidence_external_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    validate_evidence_adjudication_response(adjudication_response, pack=adjudication_pack)
    labels = [{
        "conflict_id": item["conflict_id"],
        "criteria": item["selected_tuple"],
        "reference_source": "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT",
        "source_refs": list(item["lane_annotation_ids"].values()),
    } for item in adjudication_manifest["agreement_records"]]
    bindings = adjudication_manifest["private_disagreement_bindings"]
    for decision in adjudication_response["decisions"]:
        labels.append({
            "conflict_id": bindings[decision["adjudication_id"]]["conflict_id"],
            "criteria": decision["criteria"],
            "reference_source": "KIMI_K3_WHOLE_TUPLE_ADJUDICATION",
            "source_refs": [decision["adjudication_id"]],
            "decision_basis": decision["decision_basis"],
            "confidence": decision["confidence"],
        })
    labels.sort(key=lambda item: item["conflict_id"])
    commitment = {
        "reference_version": EVIDENCE_REFERENCE_VERSION,
        "panel_id": adjudication_manifest["panel_id"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": hash_payload(adjudication_response),
        "labels": labels,
        "object_count": len(labels),
        "criterion_count": len(labels) * len(CRITERIA),
        "source_counts": dict(Counter(item["reference_source"] for item in labels)),
        "candidate_outputs_exposed_to_panel": False,
        "cross_axis_coherence_passed": True,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    reference = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_evidence_external_reference(reference)
    return reference


def validate_evidence_external_reference(reference):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version") != EVIDENCE_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({item.get("conflict_id") for item in labels}) != 24
        or reference.get("criterion_count") != 120
        or reference.get("candidate_outputs_exposed_to_panel") is not False
    ):
        raise ValueError("evidence_external_reference_invalid")
    for item in labels:
        criteria = item.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[key] not in ALLOWED_STATES[key] for key in CRITERIA)
            or selective_tuple_violations(criteria)
        ):
            raise ValueError("evidence_external_reference_tuple_invalid")


def build_evidence_external_evaluation(*, reference, run, analysis, preregistration):
    validate_evidence_external_reference(reference)
    truth = {item["conflict_id"]: item["criteria"] for item in reference["labels"]}
    outputs = {arm: {} for arm in ARMS}
    for output in run["outputs"]:
        outputs[output["arm"]][output["conflict_id"]] = output["payload"]
    metrics = {arm: _metrics(outputs[arm], truth) for arm in ARMS}
    admission = {arm: _admission(outputs[arm], truth) for arm in ARMS}
    failures = {
        (item["arm"], item["conflict_id"]): item
        for item in run.get("failures", [])
    }
    admission_records = {
        arm: _admission_records(outputs[arm], truth, failures, arm)
        for arm in ARMS
    }
    control, calibrated = metrics[ARMS[0]], metrics[ARMS[1]]
    evidence_gain = calibrated["axis_correct"]["EVIDENCE_STATE"] - control["axis_correct"]["EVIDENCE_STATE"]
    selected_delta = calibrated["axis_correct"]["SELECTED_OBJECT"] - control["axis_correct"]["SELECTED_OBJECT"]
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_admission_precision": admission[ARMS[1]]["precision"] is not None and admission[ARMS[1]]["precision"] >= gate["minimum_admission_precision"],
        "minimum_soft_ambiguity_recall": admission[ARMS[1]]["recall"] is not None and admission[ARMS[1]]["recall"] >= gate["minimum_soft_ambiguity_recall"],
        "minimum_evidence_state_accuracy": calibrated["axis_accuracy"]["EVIDENCE_STATE"] >= gate["minimum_evidence_state_accuracy"],
        "minimum_evidence_correct_case_gain_over_control": evidence_gain >= gate["minimum_evidence_correct_case_gain_over_control"],
        "selected_object_loss_within_limit": selected_delta >= -gate["maximum_selected_object_case_loss_vs_control"],
        "minimum_output_coverage": calibrated["output_coverage"] >= gate["minimum_output_coverage"],
        "calibrator_to_control_token_ratio_within_limit": analysis["calibrator_to_control_token_ratio"] <= gate["maximum_calibrator_to_control_token_ratio"],
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    commitment = {
        "evaluation_version": EVIDENCE_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "arm_metrics": metrics,
        "admission_metrics": admission,
        "admission_records": admission_records,
        "evidence_correct_case_gain_over_control": evidence_gain,
        "selected_object_correct_case_delta_vs_control": selected_delta,
        "cost_accounting": {
            "arm_total_tokens": analysis["total_tokens"],
            "calibrator_to_control_token_ratio": analysis["calibrator_to_control_token_ratio"],
        },
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "baseline_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "reference_state_distributions": {
            axis: dict(Counter(item["criteria"][axis] for item in reference["labels"]))
            for axis in CRITERIA
        },
        "missing_outputs_scored_as_incorrect": True,
        "claim_scope": "FROZEN_24_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "production_authority": False,
        "candidate_state": (
            "EVIDENCE_CALIBRATOR_POSITIVE_CANDIDATE_PENDING_PROMOTION_AUDIT"
            if anti_additive == "PASS"
            else "EVIDENCE_CALIBRATOR_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_evidence_external_evaluation(
    evaluation, *, reference, run, analysis, preregistration
):
    expected = build_evidence_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    if evaluation != expected:
        raise ValueError("evidence_external_evaluation_invalid")


def render_evidence_external_evaluation(evaluation):
    control = evaluation["arm_metrics"][ARMS[0]]
    calibrated = evaluation["arm_metrics"][ARMS[1]]
    admission = evaluation["admission_metrics"]
    calibrated_admission = admission[ARMS[1]]
    calibrated_records = evaluation["admission_records"][ARMS[1]]
    missing_false_negatives = sum(
        item["outcome"] == "FALSE_NEGATIVE" and item["output_missing"]
        for item in calibrated_records
    )
    semantic_false_negatives = calibrated_admission["false_negative"] - missing_false_negatives
    observations = [
        f"Control evidence-state correctness is {control['axis_correct']['EVIDENCE_STATE']}/24; calibrator is {calibrated['axis_correct']['EVIDENCE_STATE']}/24, gain {evaluation['evidence_correct_case_gain_over_control']}.",
        f"Control admission metrics are {admission[ARMS[0]]}; calibrator admission metrics are {admission[ARMS[1]]}.",
        f"The calibrator's {calibrated_admission['false_negative']} soft-ambiguity misses split into {missing_false_negatives} rejected/missing outputs and {semantic_false_negatives} retained semantic misclassifications.",
        f"Control output coverage is {control['output_coverage']:.3f}; calibrator coverage is {calibrated['output_coverage']:.3f}.",
        f"Selected-object correctness changes by {evaluation['selected_object_correct_case_delta_vs_control']} cases.",
        f"Calibrator/control token ratio is {evaluation['cost_accounting']['calibrator_to_control_token_ratio']:.3f}.",
        f"Preregistered conditions are {evaluation['preregistered_gate_conditions']}.",
    ]
    interpretations = [
        "Definition-source contrast produces real local semantic gain, but that gain is not yet a reliable admission policy.",
        "Recall loss is jointly caused by Provider classification and Runtime coherence rejection; changing only one layer cannot close this holdout.",
        "A partial evidence-state gain cannot compensate for failed precision, recall, accuracy, or coverage gates.",
        "The panel treats a conclusive missing specification as a completed justified NONE. That convention explains why incomplete opaque outputs lose process-state credit, but it remains model-panel evidence rather than ground truth.",
        "This evaluates admission cognition before specialist collaboration; no downstream role gain is inferred.",
    ]
    unknowns = [
        "Whether a corrected coherence gate preserves fail-closed behavior on direct and compositional objects.",
        "Whether the same semantic and coverage gains survive a new frozen holdout after the current 24 labels are retired from tuning.",
        "Whether soft-ambiguity admission creates positive downstream Cbit once specialist collaboration is restored.",
    ]
    intuition = [
        "Separate source recognition from tuple-state policy: 'the request says the term is undefined' is evidence of underspecification, not an explicit definition.",
        "Preserve the rejected Provider receipts as counterexamples for gate calibration; do not silently convert them into accepted outputs.",
        "The next fresh test should distinguish semantic recovery from gate recovery with a frozen two-stage ablation.",
    ]
    lines = ["# Evidence-State Calibrator External Evaluation v0.19", ""]
    for title, values in (
        ("Observations", observations),
        ("Interpretations", interpretations),
        ("Unknowns", unknowns),
        ("Intuition Triggers", intuition),
    ):
        lines.extend((f"## {title}", "", *[f"- {value}" for value in values], ""))
    lines.extend((f"Anti-Additive gate: `{evaluation['anti_additive_gate']}`", f"State: `{evaluation['candidate_state']}`", f"Artifact hash: `{evaluation['artifact_hash']}`", ""))
    return "\n".join(lines)


def _metrics(outputs, truth):
    axis_correct, full = Counter(), 0
    for conflict_id, expected in truth.items():
        payload = outputs.get(conflict_id)
        matches = []
        for field, axis in AXIS_MAP:
            correct = payload is not None and payload[field] == expected[axis]
            axis_correct[axis] += int(correct)
            matches.append(correct)
        full += int(all(matches))
    return {
        "observed_output_count": len(outputs),
        "missing_output_count": len(truth) - len(outputs),
        "output_coverage": round(len(outputs) / len(truth), 6),
        "axis_correct": dict(axis_correct),
        "axis_accuracy": {axis: round(axis_correct[axis] / len(truth), 6) for _, axis in AXIS_MAP},
        "all_correct_cell_count": sum(axis_correct.values()),
        "full_tuple_correct": full,
    }


def _admission(outputs, truth):
    predicted = {
        conflict_id for conflict_id, payload in outputs.items()
        if payload["evidence_state"] == "SOFT_AMBIGUITY" and payload["selected_object"] == "NONE"
    }
    eligible = {
        conflict_id for conflict_id, criteria in truth.items()
        if criteria["EVIDENCE_STATE"] == "SOFT_AMBIGUITY" and criteria["SELECTED_OBJECT"] == "NONE"
    }
    tp, fp, fn = len(predicted & eligible), len(predicted - eligible), len(eligible - predicted)
    tn = len(set(truth) - predicted - eligible)
    return {
        "predicted_count": len(predicted),
        "reference_eligible_count": len(eligible),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": round(tp / (tp + fp), 6) if tp + fp else None,
        "recall": round(tp / (tp + fn), 6) if tp + fn else None,
    }


def _admission_records(outputs, truth, failures, arm):
    records = []
    for conflict_id, criteria in sorted(truth.items()):
        payload = outputs.get(conflict_id)
        eligible = (
            criteria["EVIDENCE_STATE"] == "SOFT_AMBIGUITY"
            and criteria["SELECTED_OBJECT"] == "NONE"
        )
        predicted = bool(
            payload
            and payload["evidence_state"] == "SOFT_AMBIGUITY"
            and payload["selected_object"] == "NONE"
        )
        if not (eligible or predicted):
            continue
        if eligible and predicted:
            outcome = "TRUE_POSITIVE"
        elif predicted:
            outcome = "FALSE_POSITIVE"
        else:
            outcome = "FALSE_NEGATIVE"
        failure = failures.get((arm, conflict_id), {})
        records.append({
            "conflict_id": conflict_id,
            "outcome": outcome,
            "output_missing": payload is None,
            "reference_evidence_state": criteria["EVIDENCE_STATE"],
            "reference_pragmatic_preference": criteria["PRAGMATIC_PREFERENCE"],
            "predicted_evidence_state": (
                payload["evidence_state"] if payload else None
            ),
            "predicted_selected_object": (
                payload["selected_object"] if payload else None
            ),
            "failure_status": failure.get("status"),
            "validation_errors": list(failure.get("validation_errors", [])),
        })
    return records
