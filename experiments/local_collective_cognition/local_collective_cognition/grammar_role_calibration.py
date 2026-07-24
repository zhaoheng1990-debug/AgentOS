"""Calibration analysis for grammar-backed local specialist actions."""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import permutations

from .clarification_reference_first_holdout import validate_reference_first_holdout
from .clarification_reference_first_panel import validate_reference_first_reference
from .clarification_reference_first_roles import MODEL_IDS, ROLE_IDS, validate_specialist_role_plan
from .grammar_backed_role_adapter import validate_grammar_output
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "grammar_backed_role_calibration_v0_16"


def run_grammar_calibration(*, corpus, reference, role_plan, adapters) -> dict:
    validate_reference_first_holdout(corpus)
    validate_reference_first_reference(reference)
    validate_specialist_role_plan(role_plan)
    adapter_index = {adapter.model_id: adapter for adapter in adapters}
    if set(adapter_index) != set(MODEL_IDS):
        raise ValueError("grammar_calibration_adapters_invalid")
    public = {item["conflict_id"]: item for batch in corpus["public_surface"]["batches"] for item in batch["conflicts"]}
    outputs, failures = [], []
    for assignment in role_plan["assignments"]:
        item = public[assignment["conflict_id"]]
        try:
            output = adapter_index[assignment["model_id"]].invoke(
                role_id=assignment["role_id"],
                item=item,
                evidence_refs=tuple(corpus["evidence_refs"]),
            )
            validate_grammar_output(output, item=item)
            outputs.append(output)
        except Exception as exc:
            failures.append({
                "conflict_id": assignment["conflict_id"],
                "model_id": assignment["model_id"],
                "role_id": assignment["role_id"],
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_hash": reference["artifact_hash"],
        "source_role_plan_hash": role_plan["plan_hash"],
        "outputs": outputs,
        "failures": failures,
        "reference_available_during_inference": False,
        "calibration_set_burned": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_grammar_calibration(*, corpus, reference, role_plan, run) -> dict:
    validate_grammar_calibration_run(run, corpus=corpus, reference=reference, role_plan=role_plan)
    truth = {item["conflict_id"]: item["criteria"] for item in reference["labels"]}
    assignments = {(item["conflict_id"], item["role_id"]): item for item in role_plan["assignments"]}
    correct = Counter()
    observed = Counter()
    model_coverage = Counter()
    role_coverage = Counter()
    cost = Counter()
    for output in run["outputs"]:
        conflict_id = output["object_ref"].removeprefix("object://")
        role_id = output["role_id"]
        model_id = output["model_id"]
        expected_assignment = assignments[(conflict_id, role_id)]
        if expected_assignment["model_id"] != model_id:
            raise ValueError("grammar_calibration_assignment_binding_invalid")
        result = output["action_receipt"]["result"]
        expected = truth[conflict_id]
        is_correct = _role_correct(role_id, result, expected)
        observed[(model_id, role_id)] += 1
        observed[("ALL", role_id)] += 1
        correct[(model_id, role_id)] += int(is_correct)
        correct[("ALL", role_id)] += int(is_correct)
        model_coverage[model_id] += 1
        role_coverage[role_id] += 1
        for key, value in output["action_receipt"]["cost"].items():
            cost[key] += value
    matrix = {
        model: {
            role: {
                "correct": correct[(model, role)],
                "observed": observed[(model, role)],
                "accuracy": _ratio(correct[(model, role)], observed[(model, role)]),
            }
            for role in ROLE_IDS
        }
        for model in MODEL_IDS
    }
    routing = _select_bijective_routing(matrix)
    routed_role_metrics = {role: matrix[model][role] for role, model in routing.items()}
    overall_coverage = _ratio(len(run["outputs"]), role_plan["assignment_count"])
    per_model_coverage = {model: _ratio(model_coverage[model], 24) for model in MODEL_IDS}
    role_metrics = {
        role: {
            "correct": correct[("ALL", role)],
            "observed": observed[("ALL", role)],
            "accuracy": _ratio(correct[("ALL", role)], observed[("ALL", role)]),
        }
        for role in ROLE_IDS
    }
    transport_gate = overall_coverage >= 0.95 and all(value >= 0.90 for value in per_model_coverage.values())
    pooled_viability_gate = role_metrics["OBJECT_GROUNDING"]["accuracy"] >= 0.30 and role_metrics["PRAGMATIC_DEFAULT"]["accuracy"] >= 0.40
    routed_viability_gate = routed_role_metrics["OBJECT_GROUNDING"]["accuracy"] >= 0.30 and routed_role_metrics["PRAGMATIC_DEFAULT"]["accuracy"] >= 0.40
    coordinator_eligible = transport_gate and routed_viability_gate
    commitment = {
        "analysis_version": CALIBRATION_VERSION,
        "run_hash": run["run_hash"],
        "overall_coverage": overall_coverage,
        "per_model_coverage": per_model_coverage,
        "per_role_coverage": {role: _ratio(role_coverage[role], 24) for role in ROLE_IDS},
        "role_metrics": role_metrics,
        "capability_matrix": matrix,
        "selected_bijective_routing": routing,
        "routed_role_metrics": routed_role_metrics,
        "accounting": dict(cost),
        "tokens_per_valid_receipt": _ratio(cost["input_tokens"] + cost["output_tokens"], len(run["outputs"])),
        "transport_gate_passed": transport_gate,
        "pooled_semantic_viability_gate_passed": pooled_viability_gate,
        "semantic_viability_gate_passed": routed_viability_gate,
        "fresh_blind_collection_allowed": coordinator_eligible,
        "coordinator_calibration_eligible": coordinator_eligible,
        "completeness_gate_disabled_reason": "v0.15 reference contains only COMPLETE labels",
        "claim_scope": "BURNED_CALIBRATION_ONLY",
        "gate_object_revision": "POOLED_INTERCHANGEABILITY_PRESERVED_SEPARATELY_FROM_ROUTED_SPECIALIZATION",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_grammar_calibration_run(run, *, corpus, reference, role_plan) -> None:
    commitment = {key: value for key, value in run.items() if key != "run_hash"}
    if (
        run.get("run_hash") != hash_payload(commitment)
        or run.get("calibration_version") != CALIBRATION_VERSION
        or run.get("source_corpus_hash") != corpus.get("artifact_hash")
        or run.get("source_reference_hash") != reference.get("artifact_hash")
        or run.get("source_role_plan_hash") != role_plan.get("plan_hash")
        or run.get("reference_available_during_inference") is not False
        or len(run.get("outputs", [])) + len(run.get("failures", [])) != role_plan.get("assignment_count")
    ):
        raise ValueError("grammar_calibration_run_invalid")
    seen = set()
    for output in run["outputs"]:
        validate_grammar_output(output)
        key = (output["object_ref"], output["model_id"], output["role_id"])
        if key in seen:
            raise ValueError("grammar_calibration_duplicate_output")
        seen.add(key)


def render_grammar_calibration_analysis(analysis: dict) -> str:
    role_lines = "\n".join(
        f"- {role}: {values['correct']}/{values['observed']} = {values['accuracy']:.3f}"
        for role, values in analysis["role_metrics"].items()
    )
    routing = "\n".join(f"- {role}: {model}" for role, model in analysis["selected_bijective_routing"].items())
    return f"""# Grammar-Backed Role Calibration v0.16

## Observations

- Strict canonical receipt coverage is {analysis['overall_coverage']:.3f}.
- Transport gate passed: {analysis['transport_gate_passed']}.
- Semantic viability gate passed: {analysis['semantic_viability_gate_passed']}.
- Total tokens per valid receipt: {analysis['tokens_per_valid_receipt']:.1f}.

Role accuracy on the burned calibration set:
{role_lines}

Selected one-to-one routing:
{routing}

## Interpretations

- A passed transport gate means the finite grammar removed the previously observed structured-output bottleneck; it does not establish fresh semantic generalization.
- The routing is a calibration policy, not a stable model reputation claim.
- Provider models choose semantics; the Harness supplies syntax and canonical lifting only.

## Unknowns

- Fresh-holdout correctness remains unknown until the external model panel is frozen.
- The v0.15 completeness axis is degenerate and cannot support a completeness capability claim.
- Coordinator gain remains unmeasured at this phase.

## Intuition Triggers

- Communication syntax can be treated as an execution-layer compilation problem while preserving Runtime-level cognitive objects.
- Stable actions and unstable model grammars should evolve at different rates.

State: {'CALIBRATION_GATE_PASSED' if analysis['fresh_blind_collection_allowed'] else 'CALIBRATION_GATE_FAILED'}
Artifact hash: {analysis['artifact_hash']}
"""


def _role_correct(role_id, result, expected):
    if role_id == "OBJECT_GROUNDING":
        return result.get("selected_object") == expected["SELECTED_OBJECT"] and result.get("selection_basis") == expected["SELECTION_BASIS"]
    if role_id == "PRAGMATIC_DEFAULT":
        return result.get("pragmatic_preference") == expected["PRAGMATIC_PREFERENCE"]
    return result.get("assessment_completeness") == expected["AXIS_ASSESSMENT_COMPLETE"]


def _select_bijective_routing(matrix):
    candidates = []
    for models in permutations(MODEL_IDS):
        mapping = dict(zip(ROLE_IDS, models))
        score = sum(matrix[model][role]["accuracy"] for role, model in mapping.items())
        candidates.append((score, tuple(mapping[role] for role in ROLE_IDS), mapping))
    return max(candidates, key=lambda item: (item[0], tuple(reversed(item[1]))))[2]


def _ratio(numerator, denominator):
    return round(numerator / denominator, 6) if denominator else 0.0
