"""Freeze the v0.18 external reference and evaluate selective escalation."""

from __future__ import annotations

from collections import Counter

from .cognitive_action_selective_panel import (
    ALLOWED_STATES,
    CRITERIA,
    selective_tuple_violations,
    validate_selective_adjudication_response,
    validate_selective_external_adjudication,
)
from .provider_telemetry import hash_payload


SELECTIVE_REFERENCE_VERSION = "cognitive_action_selective_external_reference_v0_18"
SELECTIVE_EVALUATION_VERSION = "cognitive_action_selective_external_evaluation_v0_18"
AXIS_MAP = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("evidence_state", "EVIDENCE_STATE"),
    ("assessment_process_state", "ASSESSMENT_PROCESS_STATE"),
)
PRIMARY_AXIS_MAP = AXIS_MAP[:3]


def build_selective_external_reference(
    *, adjudication_pack, adjudication_manifest, adjudication_response
):
    validate_selective_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
    )
    validate_selective_adjudication_response(
        adjudication_response,
        pack=adjudication_pack,
    )
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
        "reference_version": SELECTIVE_REFERENCE_VERSION,
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
    validate_selective_external_reference(reference)
    return reference


def validate_selective_external_reference(reference):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version") != SELECTIVE_REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({label.get("conflict_id") for label in labels}) != 24
        or reference.get("criterion_count") != 120
        or reference.get("cross_axis_coherence_passed") is not True
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get("reference_revision_allowed") is not False
    ):
        raise ValueError("selective_external_reference_invalid")
    for label in labels:
        criteria = label.get("criteria")
        if (
            not isinstance(criteria, dict)
            or set(criteria) != set(CRITERIA)
            or any(
                criteria[criterion] not in ALLOWED_STATES[criterion]
                for criterion in CRITERIA
            )
            or selective_tuple_violations(criteria)
        ):
            raise ValueError("selective_external_reference_tuple_invalid")


def build_selective_external_evaluation(
    *,
    reference,
    baseline_run,
    admission_plan,
    selective_run,
    runtime_analysis,
    preregistration,
):
    validate_selective_external_reference(reference)
    truth = {
        label["conflict_id"]: label["criteria"] for label in reference["labels"]
    }
    baseline = {
        output["conflict_id"]: output["payload"] for output in baseline_run["outputs"]
    }
    routed = {
        output["conflict_id"]: output["payload"]
        for output in selective_run["routed_outputs"]
    }
    baseline_metrics = _arm_metrics(baseline, truth)
    routed_metrics = _arm_metrics(routed, truth)
    transitions, transition_counts, transitions_by_axis = _transition_ledger(
        baseline=baseline,
        routed=routed,
        truth=truth,
    )
    predicted = set(admission_plan["admitted_conflict_ids"])
    reference_eligible = {
        conflict_id
        for conflict_id, criteria in truth.items()
        if criteria["EVIDENCE_STATE"] == "SOFT_AMBIGUITY"
        and criteria["SELECTED_OBJECT"] == "NONE"
    }
    tp = len(predicted & reference_eligible)
    fp = len(predicted - reference_eligible)
    fn = len(reference_eligible - predicted)
    tn = len(set(truth) - predicted - reference_eligible)
    precision = round(tp / (tp + fp), 6) if tp + fp else None
    recall = round(tp / (tp + fn), 6) if tp + fn else None
    admission = {
        "predicted_admission_count": len(predicted),
        "reference_eligible_count": len(reference_eligible),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "precision": precision,
        "recall": recall,
        "precision_state": "UNDEFINED_NO_PREDICTED_ADMISSIONS" if precision is None else "DEFINED",
        "reference_eligible_ids": sorted(reference_eligible),
        "predicted_admission_ids": sorted(predicted),
    }
    primary_delta = (
        routed_metrics["primary_correct_cell_count"]
        - baseline_metrics["primary_correct_cell_count"]
    )
    deltas = {
        reference_field: (
            routed_metrics["axis_correct"][reference_field]
            - baseline_metrics["axis_correct"][reference_field]
        )
        for _, reference_field in AXIS_MAP
    }
    incremental_tokens = (
        runtime_analysis["routed_path_total_tokens"]
        - runtime_analysis["baseline_total_tokens"]
    )
    tokens_per_net = (
        round(incremental_tokens / primary_delta, 6)
        if primary_delta > 0 else None
    )
    coverage = len(routed) / len(truth)
    ratio = runtime_analysis["routed_to_baseline_token_ratio"]
    gate = preregistration["success_gate"]
    conditions = {
        "minimum_admission_precision": (
            precision is not None
            and precision >= gate["minimum_admission_precision"]
        ),
        "minimum_soft_ambiguity_recall": (
            recall is not None
            and recall >= gate["minimum_soft_ambiguity_recall"]
        ),
        "minimum_preference_case_gain": (
            deltas["PRAGMATIC_PREFERENCE"]
            >= gate["minimum_preference_case_gain"]
        ),
        "minimum_basis_case_gain": (
            deltas["SELECTION_BASIS"] >= gate["minimum_basis_case_gain"]
        ),
        "minimum_selected_object_case_gain": (
            deltas["SELECTED_OBJECT"]
            >= gate["minimum_selected_object_case_gain"]
        ),
        "minimum_primary_correct_cell_gain": (
            primary_delta >= gate["minimum_primary_correct_cell_gain"]
        ),
        "corrections_exceed_harms": (
            transition_counts["corrections"] > transition_counts["harms"]
        ),
        "routed_to_baseline_token_ratio_within_limit": (
            ratio is not None
            and ratio <= gate["maximum_routed_to_baseline_token_ratio"]
        ),
        "tokens_per_net_primary_cell_within_limit": (
            tokens_per_net is not None
            and tokens_per_net
            <= gate["maximum_tokens_per_net_primary_correct_cell"]
        ),
        "required_output_coverage": coverage >= gate["required_output_coverage"],
    }
    anti_additive = "PASS" if all(conditions.values()) else "REJECT"
    reference_distributions = {
        criterion: dict(
            Counter(label["criteria"][criterion] for label in reference["labels"])
        )
        for criterion in CRITERIA
    }
    evidence_confusion = _confusion(
        outputs=baseline,
        truth=truth,
        arm_field="evidence_state",
        reference_field="EVIDENCE_STATE",
    )
    commitment = {
        "evaluation_version": SELECTIVE_EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "baseline_run_hash": baseline_run["run_hash"],
        "admission_plan_hash": admission_plan["plan_hash"],
        "selective_run_hash": selective_run["run_hash"],
        "runtime_analysis_hash": runtime_analysis["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "arm_metrics": {
            "SINGLE_MODEL_BASELINE": baseline_metrics,
            "SELECTIVE_ESCALATION": routed_metrics,
        },
        "admission_metrics": admission,
        "axis_correct_deltas": deltas,
        "primary_correct_cell_delta": primary_delta,
        "primary_transition_counts": transition_counts,
        "primary_transition_counts_by_axis": transitions_by_axis,
        "primary_transition_ledger": transitions,
        "baseline_evidence_state_confusion": evidence_confusion,
        "cost_accounting": {
            "baseline_total_tokens": runtime_analysis["baseline_total_tokens"],
            "routed_path_total_tokens": runtime_analysis["routed_path_total_tokens"],
            "incremental_tokens_over_baseline": incremental_tokens,
            "routed_to_baseline_token_ratio": ratio,
            "tokens_per_net_primary_correct_cell": tokens_per_net,
            "baseline_failed_invocation_accounting": runtime_analysis[
                "baseline_failed_invocation_accounting"
            ],
        },
        "preregistered_gate_conditions": conditions,
        "anti_additive_gate": anti_additive,
        "baseline_promotion_allowed": anti_additive == "PASS",
        "retention_write_allowed": False,
        "reference_state_distributions": reference_distributions,
        "missing_outputs_scored_as_incorrect": True,
        "output_coverage_against_reference": round(coverage, 6),
        "claim_scope": "FROZEN_24_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "production_authority": False,
        "candidate_state": (
            "SELECTIVE_ESCALATION_POSITIVE_CANDIDATE_PENDING_PROMOTION_AUDIT"
            if anti_additive == "PASS"
            else "SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_external_evaluation(
    evaluation,
    *,
    reference,
    baseline_run,
    admission_plan,
    selective_run,
    runtime_analysis,
    preregistration,
):
    expected = build_selective_external_evaluation(
        reference=reference,
        baseline_run=baseline_run,
        admission_plan=admission_plan,
        selective_run=selective_run,
        runtime_analysis=runtime_analysis,
        preregistration=preregistration,
    )
    if evaluation != expected:
        raise ValueError("selective_external_evaluation_invalid")


def render_selective_external_evaluation(evaluation):
    baseline = evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]
    routed = evaluation["arm_metrics"]["SELECTIVE_ESCALATION"]
    admission = evaluation["admission_metrics"]
    conditions = evaluation["preregistered_gate_conditions"]
    confusion = evaluation["baseline_evidence_state_confusion"]
    observations = [
        f"The final candidate reference contains {admission['reference_eligible_count']} collaboration-eligible soft-ambiguity objects; the frozen gate admits {admission['predicted_admission_count']}.",
        f"Admission precision is {admission['precision']} with state {admission['precision_state']}; recall is {admission['recall']} ({admission['true_positive']} TP, {admission['false_positive']} FP, {admission['false_negative']} FN, {admission['true_negative']} TN).",
        f"Baseline and selective routing both score {baseline['primary_correct_cell_count']}/72 primary cells because no object was admitted.",
        f"Baseline five-axis correctness is {baseline['all_correct_cell_count']}/120 with {baseline['full_tuple_correct']}/24 complete tuples; selective routing is {routed['all_correct_cell_count']}/120 and {routed['full_tuple_correct']}/24.",
        f"Baseline evidence-state correctness is {baseline['axis_correct']['EVIDENCE_STATE']}/24; its confusion table is {confusion}.",
        f"Output coverage against the 24-object reference is {evaluation['output_coverage_against_reference']:.3f}; three rejected baseline tuples are scored incorrect.",
        f"Cost remains {evaluation['cost_accounting']['routed_path_total_tokens']} tokens, ratio {evaluation['cost_accounting']['routed_to_baseline_token_ratio']:.3f}, because zero collaboration calls were made.",
        f"Preregistered conditions are {conditions}.",
    ]
    interpretations = [
        "The runtime prevented additive work but failed its more important cognitive purpose: it did not expose any of the six objects for which collaboration was designed.",
        "Undefined precision is not evidence of clean routing. With no predicted positives, recall and opportunity capture carry the operative signal.",
        "The evidence-state confusion localizes the bottleneck before role collaboration: the baseline over-promotes underdetermined and compositional surfaces into direct definition.",
        "Because baseline and routed outputs are identical, this round evaluates admission quality, not the latent value of the pragmatic specialist.",
        "K3's opaque decisions support a stable distinction between an unresolved object and an incomplete assessment process.",
    ]
    unknowns = [
        "The frozen reference is a blinded three-model candidate reference, not human gold.",
        "The current experiment cannot estimate preference-collaboration gain because the gate admitted no object.",
        "A fresh holdout is required after any evidence-state calibration; these 24 labels cannot be reused for tuning and validation.",
    ]
    intuition = [
        "The next highest-Cbit move is a contrastive evidence-state calibrator that compares direct definition against candidate paraphrase, compositional derivation, soft ambiguity, and opaque reference.",
        "Admission should be tested as its own prediction task before paying for downstream roles.",
        "A useful gate must optimize opportunity-sensitive recall under a hard false-positive budget, not merely avoid provider calls.",
        "Opaque references should route toward evidence acquisition or clarification, while soft ambiguity can route toward pragmatic collaboration.",
    ]
    lines = ["# Selective Escalation External Evaluation v0.18", ""]
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
    missing_ids = sorted(set(truth) - set(outputs))
    for conflict_id, expected in truth.items():
        payload = outputs.get(conflict_id)
        matches = []
        for arm_field, reference_field in AXIS_MAP:
            correct = (
                payload is not None
                and payload[arm_field] == expected[reference_field]
            )
            axis_correct[reference_field] += int(correct)
            matches.append(correct)
        full += int(all(matches))
    primary_correct = sum(
        axis_correct[reference_field] for _, reference_field in PRIMARY_AXIS_MAP
    )
    all_correct = sum(axis_correct.values())
    return {
        "observed_output_count": len(outputs),
        "missing_output_count": len(missing_ids),
        "missing_output_ids": missing_ids,
        "axis_correct": dict(axis_correct),
        "axis_accuracy": {
            reference_field: round(axis_correct[reference_field] / len(truth), 6)
            for _, reference_field in AXIS_MAP
        },
        "primary_correct_cell_count": primary_correct,
        "primary_correct_cell_accuracy": round(
            primary_correct / (len(truth) * len(PRIMARY_AXIS_MAP)), 6
        ),
        "all_correct_cell_count": all_correct,
        "all_correct_cell_accuracy": round(
            all_correct / (len(truth) * len(AXIS_MAP)), 6
        ),
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
            baseline_correct = (
                baseline.get(conflict_id) is not None
                and baseline[conflict_id][arm_field]
                == truth[conflict_id][reference_field]
            )
            routed_correct = (
                routed_payload is not None
                and routed_payload[arm_field]
                == truth[conflict_id][reference_field]
            )
            if routed_payload is None:
                state = (
                    "MISSING_OUTPUT_HARM"
                    if baseline_correct else "MISSING_OUTPUT_PRESERVED_WRONG"
                )
                counts["missing_output_cells"] += 1
                counts[
                    "harms" if baseline_correct else "preserved_wrongs"
                ] += 1
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
    for key in (
        "corrections", "harms", "preserved_corrects", "preserved_wrongs",
        "missing_output_cells",
    ):
        counts[key] += 0
    return (
        records,
        dict(counts),
        {axis: dict(values) for axis, values in by_axis.items()},
    )


def _confusion(*, outputs, truth, arm_field, reference_field):
    table = {}
    for conflict_id, expected in truth.items():
        predicted = (
            outputs[conflict_id][arm_field]
            if conflict_id in outputs else "MISSING_OUTPUT"
        )
        actual = expected[reference_field]
        table.setdefault(actual, Counter())
        table[actual][predicted] += 1
    return {actual: dict(values) for actual, values in sorted(table.items())}
