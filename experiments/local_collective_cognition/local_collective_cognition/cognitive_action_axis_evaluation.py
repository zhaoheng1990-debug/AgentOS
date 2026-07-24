"""Freeze the v0.17 external reference and evaluate axis routing."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_coordinator_contracts import semantic_tuple_violations
from .clarification_semantic_basis_panel import ALLOWED_STATES, CRITERIA
from .cognitive_action_axis_panel import (
    validate_axis_adjudication_response,
    validate_axis_external_adjudication,
)
from .provider_telemetry import hash_payload


AXIS_REFERENCE_VERSION = "cognitive_action_axis_external_reference_v0_17"
AXIS_EVALUATION_VERSION = "cognitive_action_axis_external_evaluation_v0_17"
ARM_AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("assessment_completeness", "AXIS_ASSESSMENT_COMPLETE"),
)
PRIMARY_AXIS_MAP = ARM_AXIS_MAP[:3]


def build_axis_external_reference(*, adjudication_pack, adjudication_manifest, adjudication_response):
    validate_axis_external_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    validate_axis_adjudication_response(adjudication_response, pack=adjudication_pack)
    labels = []
    for agreement in adjudication_manifest["agreement_records"]:
        labels.append({
            "conflict_id": agreement["conflict_id"],
            "criteria": agreement["selected_tuple"],
            "reference_source": "INDEPENDENT_LANE_FULL_TUPLE_AGREEMENT",
            "source_refs": list(agreement["lane_annotation_ids"].values()),
        })
    bindings = adjudication_manifest["private_disagreement_bindings"]
    for decision in adjudication_response["decisions"]:
        binding = bindings[decision["adjudication_id"]]
        labels.append({
            "conflict_id": binding["conflict_id"],
            "criteria": decision["criteria"],
            "reference_source": "KIMI_K3_WHOLE_TUPLE_ADJUDICATION",
            "source_refs": [decision["adjudication_id"]],
            "decision_basis": decision["decision_basis"],
            "confidence": decision["confidence"],
        })
    labels.sort(key=lambda label: label["conflict_id"])
    commitment = {
        "reference_version": AXIS_REFERENCE_VERSION,
        "panel_id": adjudication_manifest["panel_id"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_response_hash": hash_payload(adjudication_response),
        "labels": labels,
        "object_count": len(labels),
        "criterion_count": len(labels) * len(CRITERIA),
        "source_counts": dict(Counter(label["reference_source"] for label in labels)),
        "candidate_outputs_exposed_to_panel": False,
        "cross_axis_coherence_passed": True,
        "reference_revision_allowed": False,
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    reference = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_axis_external_reference(reference)
    return reference


def validate_axis_external_reference(reference):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version") != AXIS_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({label.get("conflict_id") for label in labels}) != 24
        or reference.get("criterion_count") != 96
        or reference.get("cross_axis_coherence_passed") is not True
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get("reference_revision_allowed") is not False
    ):
        raise ValueError("axis_external_reference_invalid")
    for label in labels:
        criteria = label.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA)
        ):
            raise ValueError("axis_external_reference_criteria_invalid")
        if semantic_tuple_violations(
            selected=criteria["SELECTED_OBJECT"], basis=criteria["SELECTION_BASIS"],
            preference=criteria["PRAGMATIC_PREFERENCE"], completeness=criteria["AXIS_ASSESSMENT_COMPLETE"],
        ):
            raise ValueError("axis_external_reference_incoherent")


def build_axis_external_evaluation(*, reference, run, routing_analysis, preregistration):
    validate_axis_external_reference(reference)
    truth = {label["conflict_id"]: label["criteria"] for label in reference["labels"]}
    outputs = {
        "SINGLE_MODEL_BASELINE": {},
        "ROLE_INFORMED_COORDINATOR": {},
        "AXIS_ROUTED": {},
    }
    for output in run["tuple_outputs"]:
        outputs[output["arm"]][output["conflict_id"]] = output["payload"]
    for output in run["routed_outputs"]:
        outputs["AXIS_ROUTED"][output["conflict_id"]] = output["payload"]
    arm_metrics = {arm: _arm_metrics(values, truth) for arm, values in outputs.items()}
    correction_ledger, correction_counts, transition_counts_by_axis = _transition_ledger(
        baseline=outputs["SINGLE_MODEL_BASELINE"],
        routed=outputs["AXIS_ROUTED"],
        truth=truth,
    )
    baseline = arm_metrics["SINGLE_MODEL_BASELINE"]
    routed = arm_metrics["AXIS_ROUTED"]
    baseline_primary = baseline["primary_correct_cell_count"]
    routed_primary = routed["primary_correct_cell_count"]
    net_primary = routed_primary - baseline_primary
    selected_delta = routed["axis_correct"]["SELECTED_OBJECT"] - baseline["axis_correct"]["SELECTED_OBJECT"]
    basis_delta = routed["axis_correct"]["SELECTION_BASIS"] - baseline["axis_correct"]["SELECTION_BASIS"]
    preference_delta = routed["axis_correct"]["PRAGMATIC_PREFERENCE"] - baseline["axis_correct"]["PRAGMATIC_PREFERENCE"]
    incremental_tokens = routing_analysis["routed_path_total_tokens"] - routing_analysis["baseline_total_tokens"]
    tokens_per_net = round(incremental_tokens / net_primary, 6) if net_primary > 0 else None
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_primary_correct_cell_gain": net_primary >= gate["minimum_primary_correct_cell_gain_over_baseline"],
        "selected_object_loss_within_limit": selected_delta >= -gate["maximum_selected_object_case_loss"],
        "minimum_preference_case_gain": preference_delta >= gate["minimum_preference_case_gain"],
        "minimum_basis_case_gain": basis_delta >= gate["minimum_basis_case_gain"],
        "corrections_exceed_harms": correction_counts["corrections"] > correction_counts["harms"],
        "tokens_per_net_primary_cell_within_limit": tokens_per_net is not None and incremental_tokens > 0 and tokens_per_net <= gate["maximum_tokens_per_net_primary_correct_cell"],
        "coverage_gate": len(outputs["AXIS_ROUTED"]) / len(truth) >= 0.95,
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    reference_distributions = {
        criterion: dict(Counter(label["criteria"][criterion] for label in reference["labels"]))
        for criterion in CRITERIA
    }
    commitment = {
        "evaluation_version": AXIS_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "candidate_run_hash": run["run_hash"],
        "routing_analysis_hash": routing_analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "arm_metrics": arm_metrics,
        "primary_axis_deltas": {
            "correct_cell_delta": net_primary,
            "selected_object_delta": selected_delta,
            "selection_basis_delta": basis_delta,
            "pragmatic_preference_delta": preference_delta,
        },
        "primary_transition_counts": correction_counts,
        "primary_transition_counts_by_axis": transition_counts_by_axis,
        "primary_transition_ledger": correction_ledger,
        "cost_accounting": {
            "baseline_total_tokens": routing_analysis["baseline_total_tokens"],
            "routed_path_total_tokens": routing_analysis["routed_path_total_tokens"],
            "incremental_tokens_over_baseline": incremental_tokens,
            "routed_to_baseline_token_ratio": routing_analysis["routed_to_baseline_token_ratio"],
            "tokens_per_net_primary_correct_cell": tokens_per_net,
            "failed_invocation_accounting": routing_analysis["failed_invocation_accounting"],
        },
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "baseline_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "reference_state_distributions": reference_distributions,
        "missing_outputs_scored_as_incorrect": True,
        "claim_scope": "FROZEN_24_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "production_authority": False,
        "candidate_state": (
            "AXIS_ROUTING_POSITIVE_CANDIDATE_PENDING_SEPARATE_PROMOTION_AUDIT"
            if anti_additive == "PASS"
            else "AXIS_ROUTING_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_axis_external_evaluation(evaluation, *, reference, run, routing_analysis, preregistration):
    expected = build_axis_external_evaluation(
        reference=reference, run=run, routing_analysis=routing_analysis, preregistration=preregistration
    )
    if evaluation != expected:
        raise ValueError("axis_external_evaluation_invalid")


def render_axis_external_evaluation(evaluation):
    metrics = evaluation["arm_metrics"]
    baseline, coordinator, routed = (
        metrics["SINGLE_MODEL_BASELINE"], metrics["ROLE_INFORMED_COORDINATOR"], metrics["AXIS_ROUTED"]
    )
    deltas = evaluation["primary_axis_deltas"]
    transitions = evaluation["primary_transition_counts"]
    transitions_by_axis = evaluation["primary_transition_counts_by_axis"]
    cost = evaluation["cost_accounting"]
    observations = [
        f"Baseline primary-axis correctness is {baseline['primary_correct_cell_count']}/72; coordinator is {coordinator['primary_correct_cell_count']}/72; axis routing is {routed['primary_correct_cell_count']}/72.",
        f"Axis routing changes selected-object correctness by {deltas['selected_object_delta']}, basis by {deltas['selection_basis_delta']}, and preference by {deltas['pragmatic_preference_delta']} cases.",
        f"Across primary cells, routing makes {transitions['corrections']} corrections and {transitions['harms']} harms; {transitions['missing_output_cells']} cells are missing and conservatively incorrect.",
        f"Axis-specific transition counts are {transitions_by_axis}.",
        f"The routed path uses {cost['routed_path_total_tokens']} tokens versus {cost['baseline_total_tokens']} for baseline, ratio {cost['routed_to_baseline_token_ratio']:.3f}.",
        f"Preregistered conditions are {evaluation['preregistered_gate_conditions']}.",
    ]
    interpretations = [
        "Axis routing converts source complementarity into benefit only if its semantic corrections survive both missing-output penalties and the work-cost gate.",
        "The basis critic's all-LEXICAL behavior is evaluated directly against the frozen reference rather than judged by output diversity alone.",
        "The basis critic makes no corrections and introduces two harms, so the current basis source is directly anti-additive.",
        "Preference routing is active but weak: seven corrections are offset by five ordinary harms and one missing-output harm.",
        "Selected-object source ranking reverses relative to v0.16: the coordinator scores one more object than baseline on this holdout, invalidating static cross-holdout ownership.",
        "A gate rejection does not erase axis-level improvements; it identifies which source assignment or cost component remains anti-additive.",
    ]
    unknowns = [
        "The reference is a blinded three-model candidate reference, not human gold or a real-world benchmark.",
        "A new holdout would still be required before any positive route is treated as transferable reputation evidence.",
        "Completeness remains non-discriminating if K3 resolves every missing-specification object as a completed justified NONE.",
    ]
    intuition = [
        "If preference gains survive while basis does not, the organization should route preference selectively and retire the current basis critic.",
        "The current evidence supports retiring the basis critic and treating family-conditional source differences only as hypotheses for a new holdout.",
        "If semantic gain passes but cost fails, selective escalation becomes the next highest-Cbit optimization.",
        "If corrections and harms nearly cancel, static axis ownership is insufficient and credibility must be conditioned on object structure.",
    ]
    lines = ["# Axis Routing External Evaluation v0.17", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
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
    missing_ids = sorted(set(truth) - set(outputs))
    for conflict_id, expected in truth.items():
        payload = outputs.get(conflict_id)
        matches = []
        for arm_field, reference_field in ARM_AXIS_MAP:
            correct = payload is not None and payload[arm_field] == expected[reference_field]
            axis_correct[reference_field] += int(correct)
            matches.append(correct)
        full += int(all(matches))
    primary_correct = sum(axis_correct[reference_field] for _, reference_field in PRIMARY_AXIS_MAP)
    all_correct = sum(axis_correct.values())
    return {
        "observed_output_count": len(outputs),
        "missing_output_count": len(missing_ids),
        "missing_output_ids": missing_ids,
        "axis_correct": dict(axis_correct),
        "axis_accuracy": {reference_field: round(axis_correct[reference_field] / len(truth), 6) for _, reference_field in ARM_AXIS_MAP},
        "primary_correct_cell_count": primary_correct,
        "primary_correct_cell_accuracy": round(primary_correct / (len(truth) * len(PRIMARY_AXIS_MAP)), 6),
        "all_correct_cell_count": all_correct,
        "all_correct_cell_accuracy": round(all_correct / (len(truth) * len(ARM_AXIS_MAP)), 6),
        "full_tuple_correct": full,
        "full_tuple_accuracy": round(full / len(truth), 6),
    }


def _transition_ledger(*, baseline, routed, truth):
    records, counts = [], Counter()
    by_axis = {reference_field: Counter() for _, reference_field in PRIMARY_AXIS_MAP}
    for conflict_id in sorted(truth):
        transitions = {}
        routed_payload = routed.get(conflict_id)
        for arm_field, reference_field in PRIMARY_AXIS_MAP:
            baseline_correct = baseline.get(conflict_id) is not None and baseline[conflict_id][arm_field] == truth[conflict_id][reference_field]
            routed_correct = routed_payload is not None and routed_payload[arm_field] == truth[conflict_id][reference_field]
            if routed_payload is None:
                state = "MISSING_OUTPUT_HARM" if baseline_correct else "MISSING_OUTPUT_PRESERVED_WRONG"
                counts["missing_output_cells"] += 1
                counts["harms" if baseline_correct else "preserved_wrongs"] += 1
            elif not baseline_correct and routed_correct:
                state = "CORRECTION"
                counts["corrections"] += 1
            elif baseline_correct and not routed_correct:
                state = "HARM"
                counts["harms"] += 1
            elif baseline_correct:
                state = "PRESERVED_CORRECT"
                counts["preserved_corrects"] += 1
            else:
                state = "PRESERVED_WRONG"
                counts["preserved_wrongs"] += 1
            transitions[reference_field] = state
            by_axis[reference_field][state] += 1
        records.append({"conflict_id": conflict_id, "axis_transitions": transitions})
    for key in ("corrections", "harms", "preserved_corrects", "preserved_wrongs", "missing_output_cells"):
        counts[key] += 0
    return records, dict(counts), {axis: dict(values) for axis, values in by_axis.items()}
