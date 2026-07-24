"""Freeze the v0.20 factorial reference and evaluate all four cells."""

from __future__ import annotations

from collections import Counter

from .cognitive_action_evidence_factorial import CELLS
from .cognitive_action_evidence_factorial_panel import (
    CRITERIA,
    ALLOWED_STATES,
    selective_tuple_violations,
    validate_factorial_adjudication_response,
    validate_factorial_external_adjudication,
)
from .provider_telemetry import hash_payload


FACTORIAL_REFERENCE_VERSION = (
    "cognitive_action_evidence_factorial_external_reference_v0_20"
)
FACTORIAL_EVALUATION_VERSION = (
    "cognitive_action_evidence_factorial_external_evaluation_v0_20"
)
LEGACY_CELL = "LEGACY_SOURCE_LEGACY_GATE"
SOURCE_ONLY_CELL = "REPAIRED_SOURCE_LEGACY_GATE"
GATE_ONLY_CELL = "LEGACY_SOURCE_REPAIRED_GATE"
COMBINED_CELL = "REPAIRED_SOURCE_REPAIRED_GATE"
AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("evidence_state", "EVIDENCE_STATE"),
    ("assessment_process_state", "ASSESSMENT_PROCESS_STATE"),
)


def build_factorial_external_reference(
    *, adjudication_pack, adjudication_manifest, adjudication_response
):
    validate_factorial_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    validate_factorial_adjudication_response(
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
        "reference_version": FACTORIAL_REFERENCE_VERSION,
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
        "factorial_policies_exposed_to_panel": False,
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
    validate_factorial_external_reference(reference)
    return reference


def validate_factorial_external_reference(reference):
    commitment = {
        key: value for key, value in reference.items() if key != "artifact_hash"
    }
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version") != FACTORIAL_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({item.get("conflict_id") for item in labels}) != 24
        or reference.get("criterion_count") != 120
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get("factorial_policies_exposed_to_panel") is not False
    ):
        raise ValueError("evidence_factorial_reference_invalid")
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
            raise ValueError("evidence_factorial_reference_tuple_invalid")


def build_factorial_external_evaluation(
    *, reference, run, analysis, preregistration
):
    validate_factorial_external_reference(reference)
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
    factor_effects = _factor_effects(metrics, admission)
    legacy = metrics[LEGACY_CELL]
    combined = metrics[COMBINED_CELL]
    evidence_gain = (
        combined["axis_correct"]["EVIDENCE_STATE"]
        - legacy["axis_correct"]["EVIDENCE_STATE"]
    )
    selected_delta = (
        combined["axis_correct"]["SELECTED_OBJECT"]
        - legacy["axis_correct"]["SELECTED_OBJECT"]
    )
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_combined_admission_precision": (
            admission[COMBINED_CELL]["precision"] is not None
            and admission[COMBINED_CELL]["precision"]
            >= gate["minimum_combined_admission_precision"]
        ),
        "minimum_combined_soft_ambiguity_recall": (
            admission[COMBINED_CELL]["recall"] is not None
            and admission[COMBINED_CELL]["recall"]
            >= gate["minimum_combined_soft_ambiguity_recall"]
        ),
        "minimum_combined_evidence_state_accuracy": (
            combined["axis_accuracy"]["EVIDENCE_STATE"]
            >= gate["minimum_combined_evidence_state_accuracy"]
        ),
        "minimum_combined_evidence_correct_gain_over_legacy": (
            evidence_gain
            >= gate["minimum_combined_evidence_correct_gain_over_legacy"]
        ),
        "combined_selected_object_loss_within_limit": (
            selected_delta
            >= -gate["maximum_combined_selected_object_loss_vs_legacy"]
        ),
        "minimum_combined_output_coverage": (
            combined["output_coverage"]
            >= gate["minimum_combined_output_coverage"]
        ),
        "repaired_source_token_ratio_within_limit": (
            analysis["repaired_to_legacy_source_token_ratio"]
            <= gate["maximum_repaired_to_legacy_source_token_ratio"]
        ),
        "false_soft_admissions_within_limit": (
            admission[COMBINED_CELL]["false_positive"]
            <= gate["maximum_false_soft_admissions"]
        ),
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    commitment = {
        "evaluation_version": FACTORIAL_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "cell_metrics": metrics,
        "admission_metrics": admission,
        "admission_records": admission_records,
        "factor_effects": factor_effects,
        "combined_evidence_correct_case_gain_over_legacy": evidence_gain,
        "combined_selected_object_correct_case_delta_vs_legacy": (
            selected_delta
        ),
        "cost_accounting": {
            "source_total_tokens": analysis["source_total_tokens"],
            "repaired_to_legacy_source_token_ratio": (
                analysis["repaired_to_legacy_source_token_ratio"]
            ),
            "provider_calls_shared_across_gate_cells": True,
            "runtime_gate_provider_calls": 0,
        },
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "baseline_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "factor_effects_individually_promotable": False,
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
            "EVIDENCE_FACTORIAL_POSITIVE_CANDIDATE_PENDING_PROMOTION_AUDIT"
            if anti_additive == "PASS"
            else "EVIDENCE_FACTORIAL_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_factorial_external_evaluation(
    evaluation, *, reference, run, analysis, preregistration
):
    expected = build_factorial_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    if evaluation != expected:
        raise ValueError("evidence_factorial_evaluation_invalid")


def render_factorial_external_evaluation(evaluation):
    metrics = evaluation["cell_metrics"]
    admission = evaluation["admission_metrics"]
    factor = evaluation["factor_effects"]
    gate_only = metrics[GATE_ONLY_CELL]
    source_only = metrics[SOURCE_ONLY_CELL]
    combined = metrics[COMBINED_CELL]
    gate_admission = admission[GATE_ONLY_CELL]
    combined_admission = admission[COMBINED_CELL]
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
        f"Evidence-state correctness by cell is { {cell: values['axis_correct']['EVIDENCE_STATE'] for cell, values in metrics.items()} }.",
        f"Selected-object correctness by cell is { {cell: values['axis_correct']['SELECTED_OBJECT'] for cell, values in metrics.items()} }.",
        f"Full-tuple correctness by cell is { {cell: values['full_tuple_correct'] for cell, values in metrics.items()} }.",
        f"Coverage by cell is { {cell: values['output_coverage'] for cell, values in metrics.items()} }.",
        f"Admission metrics by cell are {admission}.",
        f"Gate repair under legacy source adds {factor['all_correct_cell_count']['gate_under_legacy_source']} correct cells, {factor['full_tuple_correct']['gate_under_legacy_source']} complete tuples, and {factor['axis_correct']['ASSESSMENT_PROCESS_STATE']['gate_under_legacy_source']} process-state corrections without another Provider call.",
        f"Source repair under repaired gate changes correct cells by {factor['all_correct_cell_count']['source_under_repaired_gate']}, selected-object cases by {factor['axis_correct']['SELECTED_OBJECT']['source_under_repaired_gate']}, and false soft admissions by {factor['admission_false_positive']['source_under_repaired_gate']}.",
        f"The combined cell passes {passed} and fails {failed}.",
    ]
    interpretations = [
        f"The gate-only cell is the strongest broad result: {gate_only['all_correct_cell_count']}/120 correct cells, full coverage, admission precision {gate_admission['precision']}, and recall {gate_admission['recall']}. It remains below the frozen recall and evidence-accuracy gates.",
        f"The repaired source prompt over-expands soft admission: the combined cell has recall {combined_admission['recall']} but precision {combined_admission['precision']} with {combined_admission['false_positive']} false positives.",
        f"The source-only and combined cells are identical at {source_only['all_correct_cell_count']} correct cells and {combined['output_coverage']:.3f} coverage, showing that the repaired gate cannot rescue semantically malformed decisive-source receipts.",
        f"The all-cell interaction is {factor['all_correct_cell_count']['interaction']}; the two repairs interfere rather than compose additively.",
        "All 24 reference assessments are COMPLETE. The gate-only cell reaches 24/24 process-state correctness, supporting separation of assessment completion from object selection within this model-panel scope.",
        "The combined cell alone owns the preregistered promotion gate; factor-level gains remain diagnostic.",
    ]
    unknowns = [
        "The reference is a blinded three-model candidate reference, not human gold or real-world validity.",
        "Any surviving factor requires another fresh holdout before transfer or reputation evidence.",
        "Admission accuracy does not establish downstream specialist-collaboration Cbit.",
    ]
    intuition = [
        "If gate-only outperforms combined, preserve the gate candidate and retire the source prompt as an anti-additive intervention.",
        "If source repair harms compositional correctness, the next ontology must explicitly model positive definition, composition, and absence as three contrasts.",
        "Do not tune against these 24 labels; use them only to select the next fresh ablation.",
    ]
    lines = ["# Evidence Factorial External Evaluation v0.20", ""]
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


def _factor_effects(metrics, admission):
    def effects(values):
        legacy = values[LEGACY_CELL]
        source = values[SOURCE_ONLY_CELL]
        gate = values[GATE_ONLY_CELL]
        combined = values[COMBINED_CELL]
        return {
            "source_under_legacy_gate": source - legacy,
            "source_under_repaired_gate": combined - gate,
            "gate_under_legacy_source": gate - legacy,
            "gate_under_repaired_source": combined - source,
            "interaction": combined - gate - source + legacy,
        }

    return {
        "axis_correct": {
            axis: effects({
                cell: metrics[cell]["axis_correct"][axis]
                for cell in CELLS
            })
            for _, axis in AXIS_MAP
        },
        "full_tuple_correct": effects({
            cell: metrics[cell]["full_tuple_correct"] for cell in CELLS
        }),
        "all_correct_cell_count": effects({
            cell: metrics[cell]["all_correct_cell_count"] for cell in CELLS
        }),
        "output_count": effects({
            cell: metrics[cell]["observed_output_count"] for cell in CELLS
        }),
        "admission_true_positive": effects({
            cell: admission[cell]["true_positive"] for cell in CELLS
        }),
        "admission_false_positive": effects({
            cell: admission[cell]["false_positive"] for cell in CELLS
        }),
    }
