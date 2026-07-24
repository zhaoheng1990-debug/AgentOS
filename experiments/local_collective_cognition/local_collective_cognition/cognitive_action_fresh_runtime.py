"""Blind routed role collection and structural analysis for v0.16."""

from __future__ import annotations

from collections import Counter

from .clarification_reference_first_roles import MODEL_IDS, ROLE_IDS
from .cognitive_action_fresh_holdout import validate_fresh_action_holdout
from .grammar_backed_role_adapter import validate_grammar_output
from .provider_telemetry import hash_payload


FRESH_RUNTIME_VERSION = "cognitive_action_fresh_runtime_v0_16"


def build_fresh_role_plan(*, corpus, calibration_analysis):
    validate_fresh_action_holdout(corpus)
    if not calibration_analysis.get("fresh_blind_collection_allowed"):
        raise ValueError("fresh_action_calibration_gate_closed")
    routing = calibration_analysis["selected_bijective_routing"]
    if set(routing) != set(ROLE_IDS) or set(routing.values()) != set(MODEL_IDS):
        raise ValueError("fresh_action_routing_invalid")
    assignments = [
        {"conflict_id": item["conflict_id"], "role_id": role, "model_id": routing[role], "public_item_hash": hash_payload(item)}
        for item in corpus["public_surface"]["items"] for role in ROLE_IDS
    ]
    commitment = {
        "runtime_version": FRESH_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_calibration_hash": calibration_analysis["artifact_hash"],
        "routing": routing,
        "assignments": assignments,
        "assignment_count": len(assignments),
        "reference_available": False,
        "routing_frozen_before_fresh_inference": True,
        "coordinator_run_allowed": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def run_fresh_roles(*, corpus, plan, adapters):
    validate_fresh_action_holdout(corpus)
    adapter_index = {adapter.model_id: adapter for adapter in adapters}
    if set(adapter_index) != set(MODEL_IDS):
        raise ValueError("fresh_action_adapters_invalid")
    public = {item["conflict_id"]: item for item in corpus["public_surface"]["items"]}
    outputs, failures = [], []
    for assignment in plan["assignments"]:
        item = public[assignment["conflict_id"]]
        try:
            output = adapter_index[assignment["model_id"]].invoke(role_id=assignment["role_id"], item=item, evidence_refs=tuple(corpus["evidence_refs"]))
            validate_grammar_output(output, item=item)
            outputs.append(output)
        except Exception as exc:
            failures.append({**assignment, "error_type": type(exc).__name__, "error": str(exc)})
    commitment = {
        "runtime_version": FRESH_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_plan_hash": plan["plan_hash"],
        "outputs": outputs,
        "failures": failures,
        "reference_available_during_inference": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_fresh_roles(*, corpus, plan, run):
    validate_fresh_role_run(corpus=corpus, plan=plan, run=run)
    model_counts, role_counts, result_counts, cost = Counter(), Counter(), Counter(), Counter()
    for output in run["outputs"]:
        model_counts[output["model_id"]] += 1
        role_counts[output["role_id"]] += 1
        result_counts[(output["role_id"], str(sorted(output["action_receipt"]["result"].items())))] += 1
        for key, value in output["action_receipt"]["cost"].items():
            cost[key] += value
    coverage = round(len(run["outputs"]) / plan["assignment_count"], 6)
    coordinator_allowed = coverage >= 0.95 and all(role_counts[role] >= 22 for role in ROLE_IDS)
    commitment = {
        "analysis_version": FRESH_RUNTIME_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_plan_hash": plan["plan_hash"],
        "source_run_hash": run["run_hash"],
        "strict_receipt_coverage": coverage,
        "model_counts": dict(model_counts),
        "role_counts": dict(role_counts),
        "result_distribution": {f"{role}|{result}": count for (role, result), count in sorted(result_counts.items())},
        "accounting": dict(cost),
        "coordinator_run_allowed": coordinator_allowed,
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": "BLIND_ROLE_RECEIPTS_FROZEN" if coordinator_allowed else "BLIND_ROLE_COLLECTION_INCOMPLETE",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_fresh_role_run(*, corpus, plan, run):
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if run.get("run_hash") != hash_payload(commitment) or run.get("source_corpus_hash") != corpus.get("artifact_hash") or run.get("source_plan_hash") != plan.get("plan_hash") or run.get("reference_available_during_inference") is not False:
        raise ValueError("fresh_action_run_invalid")
    if len(run.get("outputs", [])) + len(run.get("failures", [])) != plan.get("assignment_count"):
        raise ValueError("fresh_action_run_coverage_invalid")
    observed = set()
    for output in run["outputs"]:
        validate_grammar_output(output)
        key = (output["object_ref"], output["role_id"])
        if key in observed:
            raise ValueError("fresh_action_run_duplicate")
        observed.add(key)


def build_external_annotation_pack(*, corpus, role_run):
    validate_fresh_action_holdout(corpus)
    commitment = {
        "pack_version": "cognitive_action_external_annotation_pack_v0_16",
        "source_corpus_hash": corpus["artifact_hash"],
        "candidate_role_run_hash_commitment": role_run["run_hash"],
        "instructions": {
            "task": "Independently label each public object as one coherent full tuple.",
            "criteria": ["SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE", "AXIS_ASSESSMENT_COMPLETE"],
            "selected_values": ["CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN"],
            "basis_values": ["LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_DEFAULT", "NO_PREFERENCE", "UNCERTAIN"],
            "preference_values": ["CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN"],
            "completeness_values": ["COMPLETE", "INCOMPLETE", "UNCERTAIN"],
            "important": "A justified open result can be COMPLETE. Use INCOMPLETE only when missing material prevents even deciding whether openness is warranted.",
        },
        "public_items": corpus["public_surface"]["items"],
        "candidate_outputs_exposed": False,
        "construction_truth_exposed": False,
        "ground_truth_claim": False,
    }
    return {**commitment, "pack_hash": hash_payload(commitment)}

