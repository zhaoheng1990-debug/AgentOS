"""Freeze the v0.22 candidate reference and evaluate evidence-first routing."""

from __future__ import annotations

from collections import Counter

from .cognitive_action_evidence_first import (
    BASELINE_CELL,
    CELLS,
    SELECTIVE_CELL,
)
from .cognitive_action_evidence_first_panel import (
    validate_evidence_first_adjudication_response,
    validate_evidence_first_external_adjudication,
)
from .cognitive_action_selective_panel import (
    ALLOWED_STATES,
    CRITERIA,
    selective_tuple_violations,
)
from .provider_telemetry import hash_payload


EVIDENCE_FIRST_REFERENCE_VERSION = (
    "cognitive_action_evidence_first_external_reference_v0_22"
)
EVIDENCE_FIRST_EVALUATION_VERSION = (
    "cognitive_action_evidence_first_external_evaluation_v0_22"
)
AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("evidence_state", "EVIDENCE_STATE"),
    ("assessment_process_state", "ASSESSMENT_PROCESS_STATE"),
)


def build_evidence_first_external_reference(
    *, adjudication_pack, adjudication_manifest, adjudication_response
):
    validate_evidence_first_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    validate_evidence_first_adjudication_response(
        adjudication_response,
        pack=adjudication_pack,
    )
    labels = [{
        "conflict_id": agreement["conflict_id"],
        "criteria": agreement["selected_tuple"],
        "reference_source": "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT",
        "source_refs": list(agreement["lane_annotation_ids"].values()),
    } for agreement in adjudication_manifest["agreement_records"]]
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
        "reference_version": EVIDENCE_FIRST_REFERENCE_VERSION,
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
        "challenge_plan_exposed_to_panel": False,
        "witness_receipts_exposed_to_panel": False,
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
    validate_evidence_first_external_reference(reference)
    return reference


def validate_evidence_first_external_reference(reference):
    commitment = {
        key: value for key, value in reference.items()
        if key != "artifact_hash"
    }
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version")
        != EVIDENCE_FIRST_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 16
        or len({item.get("conflict_id") for item in labels}) != 16
        or reference.get("criterion_count") != 80
        or reference.get("cross_axis_coherence_passed") is not True
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get("challenge_plan_exposed_to_panel") is not False
        or reference.get("witness_receipts_exposed_to_panel") is not False
    ):
        raise ValueError("evidence_first_reference_invalid")
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
            raise ValueError("evidence_first_reference_tuple_invalid")


def build_evidence_first_external_evaluation(
    *, reference, run, analysis, preregistration
):
    validate_evidence_first_external_reference(reference)
    truth = {
        item["conflict_id"]: item["criteria"]
        for item in reference["labels"]
    }
    outputs = {cell: {} for cell in CELLS}
    for output in run["outputs"]:
        outputs[output["cell"]][output["conflict_id"]] = output["payload"]
    metrics = {
        cell: _arm_metrics(outputs[cell], truth) for cell in CELLS
    }
    baseline = metrics[BASELINE_CELL]
    selective = metrics[SELECTIVE_CELL]
    transitions, transition_counts, transitions_by_axis = (
        _transition_ledger(
            baseline=outputs[BASELINE_CELL],
            selective=outputs[SELECTIVE_CELL],
            truth=truth,
        )
    )
    challenged_ids = set(run["challenge_plan"]["admitted_conflict_ids"])
    challenged = _challenged_metrics(
        baseline=outputs[BASELINE_CELL],
        selective=outputs[SELECTIVE_CELL],
        truth=truth,
        challenged_ids=challenged_ids,
    )
    deltas = {
        axis: (
            selective["axis_correct"][axis]
            - baseline["axis_correct"][axis]
        )
        for _, axis in AXIS_MAP
    }
    net_gain = (
        selective["all_correct_cell_count"]
        - baseline["all_correct_cell_count"]
    )
    incremental_tokens = (
        analysis["selective_total_tokens"]
        - analysis["baseline_total_tokens"]
    )
    gain_per_1000 = round(
        net_gain * 1000 / incremental_tokens,
        6,
    ) if incremental_tokens else None
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_net_correct_cell_gain": (
            net_gain >= gate["minimum_net_correct_cell_gain"]
        ),
        "minimum_evidence_state_correct_gain": (
            deltas["EVIDENCE_STATE"]
            >= gate["minimum_evidence_state_correct_gain"]
        ),
        "minimum_challenged_full_tuple_gain": (
            challenged["full_tuple_delta"]
            >= gate["minimum_challenged_full_tuple_gain"]
        ),
        "selected_object_loss_within_limit": (
            deltas["SELECTED_OBJECT"]
            >= -gate["maximum_selected_object_correct_loss"]
        ),
        "corrections_exceed_harms": (
            transition_counts["corrections"]
            > transition_counts["harms"]
        ),
        "required_output_coverage": (
            selective["output_coverage"]
            >= gate["required_output_coverage"]
        ),
        "selective_to_baseline_token_ratio_within_limit": (
            analysis["selective_to_baseline_token_ratio"]
            <= gate["maximum_selective_to_baseline_token_ratio"]
        ),
        "required_witness_validation_rate": (
            analysis["witness_validation_rate"]
            >= gate["required_witness_validation_rate"]
        ),
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    commitment = {
        "evaluation_version": EVIDENCE_FIRST_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "arm_metrics": metrics,
        "axis_correct_deltas": deltas,
        "net_correct_cell_gain": net_gain,
        "transition_counts": transition_counts,
        "transition_counts_by_axis": transitions_by_axis,
        "transition_ledger": transitions,
        "challenged_object_metrics": challenged,
        "cost_accounting": {
            "baseline_total_tokens": analysis["baseline_total_tokens"],
            "selective_total_tokens": analysis["selective_total_tokens"],
            "incremental_tokens_over_baseline": incremental_tokens,
            "selective_to_baseline_token_ratio": (
                analysis["selective_to_baseline_token_ratio"]
            ),
            "net_correct_cell_delta_per_1000_incremental_tokens": (
                gain_per_1000
            ),
        },
        "witness_validation_rate": analysis["witness_validation_rate"],
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "evidence_first_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "reference_state_distributions": {
            axis: dict(Counter(
                item["criteria"][axis] for item in reference["labels"]
            ))
            for axis in CRITERIA
        },
        "missing_outputs_scored_as_incorrect": True,
        "claim_scope": "FROZEN_16_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "production_authority": False,
        "candidate_state": (
            "EVIDENCE_FIRST_POSITIVE_CANDIDATE_PENDING_TRANSFER_AUDIT"
            if anti_additive == "PASS"
            else "EVIDENCE_FIRST_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_evidence_first_external_evaluation(
    evaluation, *, reference, run, analysis, preregistration
):
    expected = build_evidence_first_external_evaluation(
        reference=reference,
        run=run,
        analysis=analysis,
        preregistration=preregistration,
    )
    if evaluation != expected:
        raise ValueError("evidence_first_evaluation_invalid")


def render_evidence_first_external_evaluation(evaluation):
    baseline = evaluation["arm_metrics"][BASELINE_CELL]
    selective = evaluation["arm_metrics"][SELECTIVE_CELL]
    passed = [
        key for key, value
        in evaluation["preregistered_gate_conditions"].items() if value
    ]
    failed = [
        key for key, value
        in evaluation["preregistered_gate_conditions"].items() if not value
    ]
    cost = evaluation["cost_accounting"]
    observations = [
        f"Reference evidence states are {evaluation['reference_state_distributions']['EVIDENCE_STATE']}; all sixteen assessment processes are COMPLETE.",
        f"Baseline scores {baseline['all_correct_cell_count']}/80 cells and {baseline['full_tuple_correct']}/16 complete tuples; evidence-first scores {selective['all_correct_cell_count']}/80 and {selective['full_tuple_correct']}/16.",
        f"Axis deltas are {evaluation['axis_correct_deltas']}; net correct-cell gain is {evaluation['net_correct_cell_gain']}.",
        f"Changed-axis transitions contain {evaluation['transition_counts']['corrections']} corrections and {evaluation['transition_counts']['harms']} harms.",
        f"Challenged full-tuple delta is {evaluation['challenged_object_metrics']['full_tuple_delta']}.",
        f"The selective path uses {cost['incremental_tokens_over_baseline']} incremental tokens at ratio {cost['selective_to_baseline_token_ratio']}.",
        f"The gate passes {passed} and fails {failed}.",
    ]
    interpretations = [
        "Evidence-first sequencing limited churn, but the witness stage confused a named request with an available definition on both changed missing-specification objects.",
        "The selective arm produces no correction. It destroys previously correct selected-object and selection-basis cells while leaving the evidence-state errors unresolved.",
        "Exact-span validation proves provenance, not semantic relevance. A verbatim span can still witness the wrong relation between the request, the missing specification, and the candidate.",
        "The negative cell delta plus incremental token cost makes the observed Cbit proxy negative on this frozen panel.",
    ]
    unknowns = [
        "The reference is a blinded three-model candidate reference, not human gold or real-world validity.",
        "Whether a contradiction-aware witness gate transfers to a fresh holdout remains untested.",
        "These sixteen labels are retired from tuning and cannot validate the next mechanism.",
    ]
    intuition = [
        "Retire the current evidence-first challenge without promotion.",
        "The next mechanism should require a witness to bind subject, requested definition, available source, and candidate entailment as separate objects.",
        "A missing named specification should emit an explicit anti-entailment witness before any positive-definition route is allowed.",
        "Test that repair on a fresh holdout with the same challenge budget and a lower token ceiling.",
    ]
    lines = ["# Evidence-First External Evaluation v0.22", ""]
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


def _arm_metrics(outputs, truth):
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
        "axis_correct": {
            axis: axis_correct[axis] for _, axis in AXIS_MAP
        },
        "axis_accuracy": {
            axis: round(axis_correct[axis] / len(truth), 6)
            for _, axis in AXIS_MAP
        },
        "all_correct_cell_count": sum(axis_correct.values()),
        "full_tuple_correct": full,
    }


def _transition_ledger(*, baseline, selective, truth):
    records, counts = [], Counter()
    by_axis = {axis: Counter() for _, axis in AXIS_MAP}
    for conflict_id in sorted(truth):
        transitions = {}
        for field, axis in AXIS_MAP:
            baseline_correct = (
                conflict_id in baseline
                and baseline[conflict_id][field] == truth[conflict_id][axis]
            )
            selective_correct = (
                conflict_id in selective
                and selective[conflict_id][field] == truth[conflict_id][axis]
            )
            if not baseline_correct and selective_correct:
                state = "CORRECTION"
                counts["corrections"] += 1
            elif baseline_correct and not selective_correct:
                state = "HARM"
                counts["harms"] += 1
            elif baseline_correct:
                state = "PRESERVED_CORRECT"
                counts["preserved_corrects"] += 1
            else:
                state = "PRESERVED_WRONG"
                counts["preserved_wrongs"] += 1
            transitions[axis] = state
            by_axis[axis][state] += 1
        records.append({
            "conflict_id": conflict_id,
            "axis_transitions": transitions,
        })
    for key in (
        "corrections", "harms", "preserved_corrects", "preserved_wrongs"
    ):
        counts[key] += 0
    return (
        records,
        dict(counts),
        {axis: dict(values) for axis, values in by_axis.items()},
    )


def _challenged_metrics(*, baseline, selective, truth, challenged_ids):
    records, baseline_full, selective_full = [], 0, 0
    for conflict_id in sorted(challenged_ids):
        expected = truth[conflict_id]
        baseline_matches = [
            baseline[conflict_id][field] == expected[axis]
            for field, axis in AXIS_MAP
        ]
        selective_matches = [
            selective[conflict_id][field] == expected[axis]
            for field, axis in AXIS_MAP
        ]
        baseline_full += int(all(baseline_matches))
        selective_full += int(all(selective_matches))
        records.append({
            "conflict_id": conflict_id,
            "baseline_correct_cells": sum(baseline_matches),
            "selective_correct_cells": sum(selective_matches),
            "correct_cell_delta": (
                sum(selective_matches) - sum(baseline_matches)
            ),
            "baseline_full_tuple_correct": all(baseline_matches),
            "selective_full_tuple_correct": all(selective_matches),
        })
    return {
        "challenged_object_count": len(challenged_ids),
        "baseline_full_tuple_correct": baseline_full,
        "selective_full_tuple_correct": selective_full,
        "full_tuple_delta": selective_full - baseline_full,
        "records": records,
    }
