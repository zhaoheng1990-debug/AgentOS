"""Freeze the v0.21 source-ontology reference and score all three arms."""

from __future__ import annotations

from collections import Counter

from .cognitive_action_selective_panel import (
    ALLOWED_STATES,
    CRITERIA,
    selective_tuple_violations,
)
from .cognitive_action_source_ontology import (
    BASELINE_CELL,
    CELLS,
    COLLAPSED_CELL,
    NATIVE_CELL,
)
from .cognitive_action_source_ontology_panel import (
    validate_source_ontology_adjudication_response,
    validate_source_ontology_external_adjudication,
)
from .provider_telemetry import hash_payload


SOURCE_ONTOLOGY_REFERENCE_VERSION = (
    "cognitive_action_source_ontology_external_reference_v0_21"
)
SOURCE_ONTOLOGY_EVALUATION_VERSION = (
    "cognitive_action_source_ontology_external_evaluation_v0_21"
)
AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("evidence_state", "EVIDENCE_STATE"),
    ("assessment_process_state", "ASSESSMENT_PROCESS_STATE"),
)


def build_source_ontology_external_reference(
    *, adjudication_pack, adjudication_manifest, adjudication_response
):
    validate_source_ontology_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    validate_source_ontology_adjudication_response(
        adjudication_response,
        pack=adjudication_pack,
    )
    labels = [{
        "conflict_id": item["conflict_id"],
        "criteria": item["selected_tuple"],
        "reference_source": "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT",
        "source_refs": list(item["lane_annotation_ids"].values()),
    } for item in adjudication_manifest["agreement_records"]]
    bindings = adjudication_manifest["private_disagreement_bindings"]
    for decision in adjudication_response["decisions"]:
        labels.append({
            "conflict_id": bindings[
                decision["adjudication_id"]
            ]["conflict_id"],
            "criteria": decision["criteria"],
            "reference_source": "KIMI_K3_WHOLE_TUPLE_ADJUDICATION",
            "source_refs": [decision["adjudication_id"]],
            "decision_basis": decision["decision_basis"],
            "confidence": decision["confidence"],
        })
    labels.sort(key=lambda item: item["conflict_id"])
    commitment = {
        "reference_version": SOURCE_ONTOLOGY_REFERENCE_VERSION,
        "panel_id": adjudication_manifest["panel_id"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": hash_payload(adjudication_response),
        "labels": labels,
        "object_count": len(labels),
        "criterion_count": len(labels) * len(CRITERIA),
        "source_counts": dict(Counter(
            item["reference_source"] for item in labels
        )),
        "candidate_outputs_exposed_to_panel": False,
        "source_ontology_policies_exposed_to_panel": False,
        "cross_axis_coherence_passed": True,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    reference = {
        **commitment,
        "artifact_hash": hash_payload(commitment),
    }
    validate_source_ontology_external_reference(reference)
    return reference


def validate_source_ontology_external_reference(reference):
    commitment = {
        key: value for key, value in reference.items()
        if key != "artifact_hash"
    }
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version")
        != SOURCE_ONTOLOGY_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({item.get("conflict_id") for item in labels}) != 24
        or reference.get("criterion_count") != 120
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get(
            "source_ontology_policies_exposed_to_panel"
        ) is not False
    ):
        raise ValueError("source_ontology_reference_invalid")
    for item in labels:
        criteria = item.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(
                criteria[key] not in ALLOWED_STATES[key]
                for key in CRITERIA
            )
            or selective_tuple_violations(criteria)
        ):
            raise ValueError("source_ontology_reference_tuple_invalid")


def build_source_ontology_external_evaluation(
    *, reference, run, analysis, preregistration
):
    validate_source_ontology_external_reference(reference)
    truth = {
        item["conflict_id"]: item["criteria"]
        for item in reference["labels"]
    }
    outputs = {cell: {} for cell in CELLS}
    for output in run["outputs"]:
        outputs[output["cell"]][output["conflict_id"]] = output["payload"]
    metrics = {
        cell: _metrics(outputs[cell], truth) for cell in CELLS
    }
    admission = {
        cell: _admission(outputs[cell], truth) for cell in CELLS
    }
    failures = {
        (item.get("cell"), item["conflict_id"]): item
        for item in run.get("failures", [])
        if item.get("cell")
    }
    admission_records = {
        cell: _admission_records(
            outputs[cell],
            truth,
            failures,
            cell,
        )
        for cell in CELLS
    }
    baseline = metrics[BASELINE_CELL]
    native = metrics[NATIVE_CELL]
    evidence_gain = (
        native["axis_correct"]["EVIDENCE_STATE"]
        - baseline["axis_correct"]["EVIDENCE_STATE"]
    )
    selected_delta = (
        native["axis_correct"]["SELECTED_OBJECT"]
        - baseline["axis_correct"]["SELECTED_OBJECT"]
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_native_admission_precision": (
            admission[NATIVE_CELL]["precision"] is not None
            and admission[NATIVE_CELL]["precision"]
            >= gate["minimum_native_admission_precision"]
        ),
        "minimum_native_soft_ambiguity_recall": (
            admission[NATIVE_CELL]["recall"] is not None
            and admission[NATIVE_CELL]["recall"]
            >= gate["minimum_native_soft_ambiguity_recall"]
        ),
        "minimum_native_evidence_state_accuracy": (
            native["axis_accuracy"]["EVIDENCE_STATE"]
            >= gate["minimum_native_evidence_state_accuracy"]
        ),
        "minimum_native_evidence_correct_gain_over_baseline": (
            evidence_gain
            >= gate["minimum_native_evidence_correct_gain_over_baseline"]
        ),
        "native_selected_object_loss_within_limit": (
            selected_delta
            >= -gate["maximum_native_selected_object_loss_vs_baseline"]
        ),
        "minimum_native_output_coverage": (
            native["output_coverage"]
            >= gate["minimum_native_output_coverage"]
        ),
        "axis_to_baseline_source_token_ratio_within_limit": (
            analysis["axis_to_baseline_source_token_ratio"]
            <= gate["maximum_axis_to_baseline_source_token_ratio"]
        ),
        "native_false_soft_admissions_within_limit": (
            admission[NATIVE_CELL]["false_positive"]
            <= gate["maximum_native_false_soft_admissions"]
        ),
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    deltas = {
        cell: _metric_delta(metrics[cell], baseline)
        for cell in (COLLAPSED_CELL, NATIVE_CELL)
    }
    deltas["NATIVE_VS_COLLAPSED"] = _metric_delta(
        metrics[NATIVE_CELL],
        metrics[COLLAPSED_CELL],
    )
    commitment = {
        "evaluation_version": SOURCE_ONTOLOGY_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "cell_metrics": metrics,
        "admission_metrics": admission,
        "admission_records": admission_records,
        "metric_deltas": deltas,
        "native_evidence_correct_case_gain_over_baseline": evidence_gain,
        "native_selected_object_correct_case_delta_vs_baseline": (
            selected_delta
        ),
        "cost_accounting": {
            "source_total_tokens": analysis["source_total_tokens"],
            "axis_to_baseline_source_token_ratio": (
                analysis["axis_to_baseline_source_token_ratio"]
            ),
            "provider_calls_shared_across_axis_runtime_paths": True,
            "runtime_gate_provider_calls": 0,
        },
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "baseline_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "collapsed_path_independently_promotable": False,
        "reference_state_distributions": {
            axis: dict(Counter(
                item["criteria"][axis] for item in reference["labels"]
            ))
            for axis in CRITERIA
        },
        "missing_outputs_scored_as_incorrect": True,
        "claim_scope": "FROZEN_24_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "production_authority": False,
        "candidate_state": (
            "SOURCE_ONTOLOGY_POSITIVE_CANDIDATE_PENDING_TRANSFER_AUDIT"
            if anti_additive == "PASS"
            else "SOURCE_ONTOLOGY_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_source_ontology_external_evaluation(
    evaluation, *, reference, run, analysis, preregistration
):
    expected = build_source_ontology_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    if evaluation != expected:
        raise ValueError("source_ontology_evaluation_invalid")


def render_source_ontology_external_evaluation(evaluation):
    metrics = evaluation["cell_metrics"]
    admission = evaluation["admission_metrics"]
    baseline = metrics[BASELINE_CELL]
    collapsed = metrics[COLLAPSED_CELL]
    native = metrics[NATIVE_CELL]
    native_admission = admission[NATIVE_CELL]
    baseline_admission = admission[BASELINE_CELL]
    passed = [
        key
        for key, value in evaluation["preregistered_gate_conditions"].items()
        if value
    ]
    failed = [
        key
        for key, value in evaluation["preregistered_gate_conditions"].items()
        if not value
    ]
    observations = [
        f"Reference evidence states are {evaluation['reference_state_distributions']['EVIDENCE_STATE']}; all 24 assessment processes are COMPLETE.",
        f"Correct five-axis cells are { {cell: value['all_correct_cell_count'] for cell, value in metrics.items()} }.",
        f"Full-tuple correctness is { {cell: value['full_tuple_correct'] for cell, value in metrics.items()} }.",
        f"Selected-object correctness is { {cell: value['axis_correct']['SELECTED_OBJECT'] for cell, value in metrics.items()} }.",
        f"Evidence-state correctness is { {cell: value['axis_correct']['EVIDENCE_STATE'] for cell, value in metrics.items()} }.",
        f"Admission metrics are {admission}.",
        f"The native cell passes {passed} and fails {failed}.",
    ]
    interpretations = [
        f"The baseline is strongly better: {baseline['all_correct_cell_count']}/120 correct cells, {baseline['full_tuple_correct']} complete tuples, 24/24 selected objects, and 18/24 evidence states.",
        f"Both decomposed-source paths have {native['all_correct_cell_count']}/120 correct cells, zero complete tuples, 12/24 selected objects, and 12/24 evidence states.",
        f"The axis arms predict no soft objects, yielding recall {native_admission['recall']} against six reference-eligible cases; the baseline predicts six with precision {baseline_admission['precision']} and recall {baseline_admission['recall']}.",
        f"Native and collapsed are identical: {evaluation['metric_deltas']['NATIVE_VS_COLLAPSED']}. Runtime synthesis adds no observed correction after the Provider receipt is formed.",
        "The decomposed prompt appears to convert absent evidence into candidate-supporting derivations. More output fields created correlated rationalizations rather than independent evidence.",
        "The baseline still has only seven fully correct tuples, so rejecting the axis intervention does not promote the baseline as a complete solution.",
    ]
    unknowns = [
        "The reference is a blinded three-model candidate reference, not human gold or real-world validity.",
        "Whether support-span extraction or explicit derivation witnesses can prevent cross-field rationalization remains untested.",
        "Admission-layer accuracy does not establish downstream collaboration Cbit.",
    ]
    intuition = [
        "Retire unconditional decomposed-axis prompting; it is slower and materially less accurate on this frozen panel.",
        "The next fresh mechanism should require evidence objects before labels: quoted support span, derivation steps, and an absence witness that cannot cite candidate option text.",
        "Use axis decomposition only as a selective challenge when a baseline receipt is low-confidence or internally inconsistent, not as the default path.",
        "Do not tune against these 24 labels.",
    ]
    lines = ["# Source Ontology External Evaluation v0.21", ""]
    for title, values in (
        ("Observations", observations),
        ("Interpretations", interpretations),
        ("Unknowns", unknowns),
        ("Intuition Triggers", intuition),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        f"Anti-Additive gate: `{evaluation['anti_additive_gate']}`",
        f"State: `{evaluation['candidate_state']}`",
        f"Artifact hash: `{evaluation['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


def _metrics(outputs, truth):
    axis_correct, full = Counter(), 0
    for conflict_id, expected in truth.items():
        payload = outputs.get(conflict_id)
        matches = []
        for field, axis in AXIS_MAP:
            correct = (
                payload is not None and payload[field] == expected[axis]
            )
            axis_correct[axis] += int(correct)
            matches.append(correct)
        full += int(all(matches))
    return {
        "observed_output_count": len(outputs),
        "missing_output_count": len(truth) - len(outputs),
        "output_coverage": round(len(outputs) / len(truth), 6),
        "axis_correct": dict(axis_correct),
        "axis_accuracy": {
            axis: round(axis_correct[axis] / len(truth), 6)
            for _, axis in AXIS_MAP
        },
        "all_correct_cell_count": sum(axis_correct.values()),
        "full_tuple_correct": full,
    }


def _admission(outputs, truth):
    predicted = {
        conflict_id
        for conflict_id, payload in outputs.items()
        if payload["evidence_state"] == "SOFT_AMBIGUITY"
        and payload["selected_object"] == "NONE"
    }
    eligible = {
        conflict_id
        for conflict_id, criteria in truth.items()
        if criteria["EVIDENCE_STATE"] == "SOFT_AMBIGUITY"
        and criteria["SELECTED_OBJECT"] == "NONE"
    }
    tp = len(predicted & eligible)
    fp = len(predicted - eligible)
    fn = len(eligible - predicted)
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


def _admission_records(outputs, truth, failures, cell):
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
        outcome = (
            "TRUE_POSITIVE"
            if eligible and predicted
            else "FALSE_POSITIVE"
            if predicted
            else "FALSE_NEGATIVE"
        )
        failure = failures.get((cell, conflict_id), {})
        records.append({
            "conflict_id": conflict_id,
            "outcome": outcome,
            "output_missing": payload is None,
            "reference_evidence_state": criteria["EVIDENCE_STATE"],
            "reference_pragmatic_preference": (
                criteria["PRAGMATIC_PREFERENCE"]
            ),
            "predicted_evidence_state": (
                payload["evidence_state"] if payload else None
            ),
            "predicted_selected_object": (
                payload["selected_object"] if payload else None
            ),
            "failure_status": failure.get("status"),
            "validation_errors": list(
                failure.get("validation_errors", [])
            ),
        })
    return records


def _metric_delta(left, right):
    return {
        "all_correct_cell_count": (
            left["all_correct_cell_count"] - right["all_correct_cell_count"]
        ),
        "full_tuple_correct": (
            left["full_tuple_correct"] - right["full_tuple_correct"]
        ),
        "observed_output_count": (
            left["observed_output_count"] - right["observed_output_count"]
        ),
        "axis_correct": {
            axis: left["axis_correct"][axis] - right["axis_correct"][axis]
            for _, axis in AXIS_MAP
        },
    }
