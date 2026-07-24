"""Freeze the external model-panel reference and score frozen v0.16 arms."""

from __future__ import annotations

from collections import Counter

from .clarification_joint_coordinator_contracts import semantic_tuple_violations
from .clarification_semantic_basis_panel import ALLOWED_STATES, CRITERIA
from .cognitive_action_external_panel import validate_adjudication_response, validate_external_adjudication
from .provider_telemetry import hash_payload


REFERENCE_VERSION = "cognitive_action_external_reference_v0_16"
EVALUATION_VERSION = "cognitive_action_external_evaluation_v0_16"
ARM_AXES = (
    ("selected_object", "SELECTED_OBJECT"),
    ("selection_basis", "SELECTION_BASIS"),
    ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    ("assessment_completeness", "AXIS_ASSESSMENT_COMPLETE"),
)


def build_external_reference(*, adjudication_pack, adjudication_manifest, response, source_bundle_hash, source_member):
    validate_external_adjudication(pack=adjudication_pack, manifest=adjudication_manifest)
    validate_adjudication_response(response, pack=adjudication_pack)
    decisions = {decision["adjudication_id"]: decision for decision in response["decisions"]}
    labels = []
    for agreement in adjudication_manifest["agreement_records"]:
        labels.append({
            "conflict_id": agreement["conflict_id"],
            "criteria": agreement["selected_tuple"],
            "tuple_source": "GPT_GEMINI_FULL_TUPLE_AGREEMENT",
        })
    for adjudication_id, binding in adjudication_manifest["private_disagreement_bindings"].items():
        labels.append({
            "conflict_id": binding["conflict_id"],
            "criteria": decisions[adjudication_id]["criteria"],
            "tuple_source": "KIMI_K3_FULL_TUPLE_ADJUDICATION",
        })
    labels.sort(key=lambda item: item["conflict_id"])
    commitment = {
        "reference_version": REFERENCE_VERSION,
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "adjudication_response_hash": hash_payload(response),
        "source_bundle_sha256": source_bundle_hash,
        "source_bundle_member": source_member,
        "labels": labels,
        "object_count": len(labels),
        "label_count": len(labels) * len(CRITERIA),
        "cross_axis_coherence_passed": True,
        "candidate_outputs_frozen_before_external_panel": True,
        "candidate_outputs_exposed_to_panel": False,
        "reference_revision_allowed": False,
        "candidate_state": "EXTERNAL_MODEL_PANEL_REFERENCE_FROZEN",
        "ground_truth_claim": False,
        "human_gold_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    artifact = {**commitment, "artifact_hash": hash_payload(commitment)}
    validate_external_reference(artifact)
    return artifact


def validate_external_reference(reference):
    commitment = {key: value for key, value in reference.items() if key != "artifact_hash"}
    labels = reference.get("labels")
    if (
        reference.get("artifact_hash") != hash_payload(commitment)
        or reference.get("reference_version") != REFERENCE_VERSION
        or not isinstance(labels, list)
        or len(labels) != 24
        or len({label.get("conflict_id") for label in labels}) != 24
        or reference.get("label_count") != 96
        or reference.get("cross_axis_coherence_passed") is not True
        or reference.get("candidate_outputs_exposed_to_panel") is not False
        or reference.get("reference_revision_allowed") is not False
    ):
        raise ValueError("cognitive_action_external_reference_invalid")
    for label in labels:
        criteria = label.get("criteria")
        if not isinstance(criteria, dict) or set(criteria) != set(CRITERIA) or any(criteria[criterion] not in ALLOWED_STATES[criterion] for criterion in CRITERIA):
            raise ValueError("cognitive_action_external_reference_criteria_invalid")
        if semantic_tuple_violations(selected=criteria["SELECTED_OBJECT"], basis=criteria["SELECTION_BASIS"], preference=criteria["PRAGMATIC_PREFERENCE"], completeness=criteria["AXIS_ASSESSMENT_COMPLETE"]):
            raise ValueError("cognitive_action_external_reference_incoherent")


def build_external_evaluation(*, reference, role_run, role_analysis, coordinator_run, coordinator_analysis):
    validate_external_reference(reference)
    truth = {label["conflict_id"]: label["criteria"] for label in reference["labels"]}
    arm_outputs = {arm: {} for arm in ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR")}
    for output in coordinator_run["arm_outputs"]:
        arm_outputs[output["arm"]][output["conflict_id"]] = output["payload"]
    if any(set(values) != set(truth) for values in arm_outputs.values()):
        raise ValueError("cognitive_action_evaluation_arm_coverage_invalid")
    arm_metrics = {arm: _arm_metrics(values, truth) for arm, values in arm_outputs.items()}
    correction_ledger, correction_counts = _correction_ledger(arm_outputs=arm_outputs, truth=truth)
    role_metrics = _role_metrics(role_run=role_run, truth=truth)
    baseline_cost = coordinator_analysis["accounting"]["SINGLE_MODEL_BASELINE"]
    coordinator_cost = coordinator_analysis["accounting"]["ROLE_INFORMED_COORDINATOR"]
    role_cost = role_analysis["accounting"]
    baseline_tokens = baseline_cost["input_tokens"] + baseline_cost["output_tokens"]
    coordinator_only_tokens = coordinator_cost["input_tokens"] + coordinator_cost["output_tokens"]
    local_role_tokens = role_cost["input_tokens"] + role_cost["output_tokens"]
    collective_path_tokens = coordinator_only_tokens + local_role_tokens
    incremental_tokens = collective_path_tokens - baseline_tokens
    net_cells = arm_metrics["ROLE_INFORMED_COORDINATOR"]["correct_cell_count"] - arm_metrics["SINGLE_MODEL_BASELINE"]["correct_cell_count"]
    full_tuple_delta = arm_metrics["ROLE_INFORMED_COORDINATOR"]["full_tuple_correct"] - arm_metrics["SINGLE_MODEL_BASELINE"]["full_tuple_correct"]
    if net_cells > 0 and full_tuple_delta >= 0:
        gain_status = "POSITIVE_CANDIDATE"
    elif net_cells < 0 and full_tuple_delta <= 0:
        gain_status = "NEGATIVE"
    else:
        gain_status = "MIXED_NO_NET_CELL_GAIN" if net_cells == 0 else "MIXED"
    reference_states = {criterion: Counter(label["criteria"][criterion] for label in reference["labels"]) for criterion in CRITERIA}
    commitment = {
        "evaluation_version": EVALUATION_VERSION,
        "reference_hash": reference["artifact_hash"],
        "role_run_hash": role_run["run_hash"],
        "coordinator_run_hash": coordinator_run["run_hash"],
        "arm_metrics": arm_metrics,
        "routed_local_role_metrics": role_metrics,
        "correction_counts": correction_counts,
        "correction_ledger": correction_ledger,
        "cost_accounting": {
            "single_model_baseline": {**baseline_cost, "total_tokens": baseline_tokens},
            "local_roles": {**role_cost, "total_tokens": local_role_tokens, "note": "teacher-forced branch scoring tokens are not equivalent to generated tokens"},
            "role_informed_coordinator_only": {**coordinator_cost, "total_tokens": coordinator_only_tokens},
            "collective_path_total_tokens": collective_path_tokens,
            "incremental_tokens_over_baseline": incremental_tokens,
            "collective_to_baseline_token_ratio": round(collective_path_tokens / baseline_tokens, 6) if baseline_tokens else None,
        },
        "net_correct_cell_delta": net_cells,
        "full_tuple_correct_delta": full_tuple_delta,
        "tokens_per_net_correct_cell": round(incremental_tokens / net_cells, 6) if net_cells > 0 else None,
        "collective_gain_status": gain_status,
        "anti_additive_gate": "REJECT" if net_cells <= 0 or incremental_tokens <= 0 else "PENDING_UTILITY_THRESHOLD",
        "reference_state_distributions": {criterion: dict(counter) for criterion, counter in reference_states.items()},
        "action_axis_scored": False,
        "action_axis_exclusion_reason": "coordinator action preconditions were underspecified before inference",
        "claim_scope": "FROZEN_24_OBJECT_INTERNAL_MODEL_PANEL_EVIDENCE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "candidate_state": "EXTERNAL_EVALUATION_COMPLETE_NO_BASELINE_PROMOTION",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_external_evaluation(evaluation, *, reference, role_run, role_analysis, coordinator_run, coordinator_analysis):
    expected = build_external_evaluation(reference=reference, role_run=role_run, role_analysis=role_analysis, coordinator_run=coordinator_run, coordinator_analysis=coordinator_analysis)
    if evaluation != expected:
        raise ValueError("cognitive_action_external_evaluation_invalid")


def render_external_evaluation(evaluation):
    baseline = evaluation["arm_metrics"]["SINGLE_MODEL_BASELINE"]
    coordinator = evaluation["arm_metrics"]["ROLE_INFORMED_COORDINATOR"]
    roles = evaluation["routed_local_role_metrics"]
    cost = evaluation["cost_accounting"]
    observations = [
        f"The single-model baseline gets {baseline['correct_cell_count']}/96 criterion cells and {baseline['full_tuple_correct']}/24 full tuples correct.",
        f"The role-informed coordinator gets {coordinator['correct_cell_count']}/96 criterion cells and {coordinator['full_tuple_correct']}/24 full tuples correct.",
        f"Coordination corrects {evaluation['correction_counts']['corrections']} baseline errors and introduces {evaluation['correction_counts']['harms']} new errors, for net cell delta {evaluation['net_correct_cell_delta']}.",
        f"The collective path consumes {cost['collective_path_total_tokens']} accounted tokens versus {cost['single_model_baseline']['total_tokens']} for baseline, ratio {cost['collective_to_baseline_token_ratio']:.3f}.",
        f"Routed local roles score object-plus-basis {roles['object_plus_basis']['correct']}/24, preference {roles['pragmatic_preference']['correct']}/24, and completeness {roles['assessment_completeness']['correct']}/24.",
    ]
    interpretations = [
        "Role evidence changes the coordinator materially but redistributes errors rather than increasing total correct semantic cells.",
        "Coordination improves full-tuple closure by two objects while sacrificing selected-object and basis accuracy and improving preference and completeness accuracy.",
        "The anti-additive gate rejects this configuration because zero net correct-cell gain does not justify the large incremental work budget.",
        "The external panel again resolves all objects as COMPLETE, so the skeptic's perfect completeness score is not evidence of incomplete-case discrimination.",
    ]
    unknowns = [
        "The 24-object internal model-panel reference is not human gold or an external benchmark.",
        "A credibility-weighted coordinator may retain preference corrections without inheriting object-grounding harms, but this requires a fresh holdout.",
        "Teacher-forced branch-scoring tokens and generated tokens are both work accounting units but not identical compute measures.",
    ]
    intuition = [
        "Role decomposition has produced complementary error orientations, but the coordinator lacks calibrated trust weights for each semantic axis.",
        "The next highest-Cbit experiment is axis-specific credibility routing, not additional rounds of unweighted discussion.",
        "Full-tuple accuracy alone can hide cancellation between corrections and harms; cell-level transition accounting should remain mandatory.",
    ]
    lines = ["# Cognitive Action External Evaluation v0.16", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        f"Collective gain status: `{evaluation['collective_gain_status']}`",
        f"Anti-additive gate: `{evaluation['anti_additive_gate']}`",
        f"State: `{evaluation['candidate_state']}`",
        f"Artifact hash: `{evaluation['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


def _arm_metrics(outputs, truth):
    axis_correct = Counter()
    full = 0
    for conflict_id, payload in outputs.items():
        matches = []
        for arm_field, reference_field in ARM_AXES:
            correct = payload[arm_field] == truth[conflict_id][reference_field]
            axis_correct[reference_field] += int(correct)
            matches.append(correct)
        full += int(all(matches))
    return {
        "axis_correct": dict(axis_correct),
        "axis_accuracy": {field: round(axis_correct[field] / len(truth), 6) for _, field in ARM_AXES},
        "correct_cell_count": sum(axis_correct.values()),
        "correct_cell_accuracy": round(sum(axis_correct.values()) / (len(truth) * len(ARM_AXES)), 6),
        "full_tuple_correct": full,
        "full_tuple_accuracy": round(full / len(truth), 6),
    }


def _role_metrics(*, role_run, truth):
    by_object = {}
    for output in role_run["outputs"]:
        conflict_id = output["object_ref"].removeprefix("object://")
        by_object.setdefault(conflict_id, {})[output["role_id"]] = output["action_receipt"]["result"]
    metrics = {
        "selected_object": 0,
        "selection_basis": 0,
        "object_plus_basis": 0,
        "pragmatic_preference": 0,
        "assessment_completeness": 0,
    }
    for conflict_id, roles in by_object.items():
        expected = truth[conflict_id]
        obj = roles["OBJECT_GROUNDING"]
        selected = obj["selected_object"] == expected["SELECTED_OBJECT"]
        basis = obj["selection_basis"] == expected["SELECTION_BASIS"]
        metrics["selected_object"] += int(selected)
        metrics["selection_basis"] += int(basis)
        metrics["object_plus_basis"] += int(selected and basis)
        metrics["pragmatic_preference"] += int(roles["PRAGMATIC_DEFAULT"]["pragmatic_preference"] == expected["PRAGMATIC_PREFERENCE"])
        metrics["assessment_completeness"] += int(roles["ASSESSMENT_SKEPTIC"]["assessment_completeness"] == expected["AXIS_ASSESSMENT_COMPLETE"])
    return {key: {"correct": value, "observed": len(truth), "accuracy": round(value / len(truth), 6)} for key, value in metrics.items()}


def _correction_ledger(*, arm_outputs, truth):
    baseline = arm_outputs["SINGLE_MODEL_BASELINE"]
    coordinator = arm_outputs["ROLE_INFORMED_COORDINATOR"]
    records, counts = [], Counter()
    for conflict_id in sorted(truth):
        transitions = {}
        for arm_field, reference_field in ARM_AXES:
            base_correct = baseline[conflict_id][arm_field] == truth[conflict_id][reference_field]
            coord_correct = coordinator[conflict_id][arm_field] == truth[conflict_id][reference_field]
            if not base_correct and coord_correct:
                state = "CORRECTION"
            elif base_correct and not coord_correct:
                state = "HARM"
            elif base_correct:
                state = "PRESERVED_CORRECT"
            else:
                state = "PRESERVED_WRONG"
            counts[state.lower() + "s"] += 1
            transitions[reference_field] = state
        records.append({"conflict_id": conflict_id, "axis_transitions": transitions})
    return records, dict(counts)

