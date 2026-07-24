"""Two-by-two Provider-source and Runtime-gate factorial v0.20."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_calibrator import source_schema
from .cognitive_action_evidence_factorial_holdout import (
    validate_factorial_holdout,
)
from .cognitive_action_evidence_gate_policies import (
    GATE_POLICIES,
    LEGACY_GATE,
    REPAIRED_GATE,
    apply_gate_policy,
)
from .cognitive_action_protocol import ActionCost, build_action_receipt
from .provider_telemetry import hash_payload


FACTORIAL_VERSION = "cognitive_action_evidence_factorial_v0_20"
FACTORIAL_TASK_KIND = "COGNITIVE_ACTION_EVIDENCE_FACTORIAL"
SOURCE_EVALUATION_HASH = "f8d6659d252223baeac88e20d1dac038a333fc1a74f4840939e32a870a83e6bd"
SOURCE_REFERENCE_HASH = "8f52da416faa5999018f766939961433191725ccb1ea62556146ae3fac02fd07"
LEGACY_SOURCE_PROMPT = "LEGACY_SOURCE_PROMPT_V0_19"
REPAIRED_SOURCE_PROMPT = "REPAIRED_SOURCE_PROMPT_V0_20"
SOURCE_PROMPTS = (LEGACY_SOURCE_PROMPT, REPAIRED_SOURCE_PROMPT)
CELL_MAP = {
    (LEGACY_SOURCE_PROMPT, LEGACY_GATE): "LEGACY_SOURCE_LEGACY_GATE",
    (REPAIRED_SOURCE_PROMPT, LEGACY_GATE): "REPAIRED_SOURCE_LEGACY_GATE",
    (LEGACY_SOURCE_PROMPT, REPAIRED_GATE): "LEGACY_SOURCE_REPAIRED_GATE",
    (REPAIRED_SOURCE_PROMPT, REPAIRED_GATE): "REPAIRED_SOURCE_REPAIRED_GATE",
}
CELLS = tuple(CELL_MAP.values())


def build_factorial_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state")
        != "EVIDENCE_CALIBRATOR_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("evidence_factorial_source_evaluation_invalid")
    commitment = {
        "preregistration_version": FACTORIAL_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": (
            "source-recognition repair and gate-policy repair address distinct "
            "components of soft-ambiguity admission loss"
        ),
        "factorial_design": {
            "source_prompt_policies": list(SOURCE_PROMPTS),
            "runtime_gate_policies": list(GATE_POLICIES),
            "cells": dict(
                sorted(
                    (
                        f"{source}|{gate}",
                        cell,
                    )
                    for (source, gate), cell in CELL_MAP.items()
                )
            ),
            "provider_calls_shared_across_gate_cells": True,
            "provider_call_count_per_object": 2,
            "runtime_gate_count_per_source_receipt": 2,
        },
        "repaired_source_invariants": {
            "negative_definition_statement_is_not_definition": True,
            "named_missing_external_spec_is_opaque": True,
            "ordinary_undefined_surface_is_soft": True,
            "candidate_option_text_is_not_definition_evidence": True,
            "assessment_completion_is_separate_from_object_selection": True,
        },
        "repaired_gate_invariants": {
            "recognized_soft_or_opaque_state_can_complete_assessment": True,
            "unsupported_uncertain_preference_maps_to_no_supported_default": True,
            "decisive_source_without_selected_object_is_rejected": True,
            "opaque_source_with_selected_object_is_rejected": True,
            "raw_provider_receipt_is_preserved": True,
        },
        "success_gate": {
            "minimum_combined_admission_precision": 0.75,
            "minimum_combined_soft_ambiguity_recall": 0.67,
            "minimum_combined_evidence_state_accuracy": 0.70,
            "minimum_combined_evidence_correct_gain_over_legacy": 4,
            "maximum_combined_selected_object_loss_vs_legacy": 1,
            "minimum_combined_output_coverage": 0.95,
            "maximum_repaired_to_legacy_source_token_ratio": 1.30,
            "maximum_false_soft_admissions": 1,
        },
        "factor_effects_are_diagnostic_not_individually_promotable": True,
        "v0_19_labels_used_as_failure_mechanism_only": True,
        "fresh_v0_20_labels_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def run_factorial(*, corpus, preregistration, adapter):
    validate_factorial_holdout(corpus)
    if (
        preregistration.get("preregistration_version") != FACTORIAL_VERSION
        or preregistration.get("artifact_hash")
        != hash_payload({
            key: value
            for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("evidence_factorial_preregistration_invalid")
    source_calls, outputs, failures = [], [], []
    evidence_refs = tuple(corpus["evidence_refs"])
    for item in corpus["public_surface"]["items"]:
        prompt_order = (
            SOURCE_PROMPTS
            if int(
                hash_payload([FACTORIAL_VERSION, item["conflict_id"]])[:2],
                16,
            )
            % 2
            == 0
            else tuple(reversed(SOURCE_PROMPTS))
        )
        for prompt_policy in prompt_order:
            task = _task(
                item=item,
                prompt_policy=prompt_policy,
                evidence_refs=evidence_refs,
                adapter=adapter,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            if envelope.status != "COMPLETED":
                source_call = _source_call(
                    item=item,
                    prompt_policy=prompt_policy,
                    task=task,
                    invocation=invocation,
                    status=envelope.status,
                    source_receipt=None,
                    source_action_receipt=None,
                )
                source_calls.append(source_call)
                failures.append({
                    "stage": "SOURCE_PROVIDER",
                    "source_prompt_policy": prompt_policy,
                    "conflict_id": item["conflict_id"],
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "source_call_hash": source_call["source_call_hash"],
                })
                continue
            source_receipt = envelope.normalized_result
            usage = invocation.get("token_usage") or {}
            source_action_receipt = build_action_receipt(
                action_id="action-" + hash_payload([
                    FACTORIAL_VERSION,
                    prompt_policy,
                    item["conflict_id"],
                    "source",
                ])[:18],
                action_type="SYNTHESIZE",
                object_ref="object://" + item["conflict_id"],
                actor_role="COORDINATOR",
                actor_instance=f"{adapter.profile.model_id}:{prompt_policy}",
                method=FACTORIAL_VERSION,
                result_state="CANDIDATE",
                result={
                    key: source_receipt[key]
                    for key in (
                        "selected_object",
                        "definition_source",
                        "pragmatic_preference",
                        "assessment_process_state",
                    )
                    if key in source_receipt
                },
                evidence_refs=evidence_refs,
                support=(str(source_receipt.get("rationale", "")),),
                uncertainty=round(
                    1 - float(source_receipt.get("confidence", 0)),
                    6,
                ),
                recommended_next_actions=("VALIDATE",),
                cost=_usage_cost(usage),
            )
            source_call = _source_call(
                item=item,
                prompt_policy=prompt_policy,
                task=task,
                invocation=invocation,
                status="COMPLETED",
                source_receipt=source_receipt,
                source_action_receipt=source_action_receipt,
            )
            source_calls.append(source_call)
            for gate_policy in GATE_POLICIES:
                cell = CELL_MAP[(prompt_policy, gate_policy)]
                try:
                    gated = apply_gate_policy(
                        gate_policy,
                        source_receipt,
                        conflict_id=item["conflict_id"],
                        evidence_refs=evidence_refs,
                    )
                except ValueError as exc:
                    failures.append({
                        "stage": "RUNTIME_GATE",
                        "cell": cell,
                        "source_prompt_policy": prompt_policy,
                        "gate_policy": gate_policy,
                        "conflict_id": item["conflict_id"],
                        "status": "SEMANTIC_VALIDATION_FAILED",
                        "validation_errors": [str(exc)],
                        "source_call_hash": source_call["source_call_hash"],
                        "provider_receipt_preserved": source_receipt,
                    })
                    continue
                payload = gated["payload"]
                gate_action_receipt = build_action_receipt(
                    action_id="action-" + hash_payload([
                        FACTORIAL_VERSION,
                        cell,
                        item["conflict_id"],
                        "gate",
                    ])[:18],
                    action_type="VALIDATE",
                    object_ref="object://" + item["conflict_id"],
                    actor_role="REPLICATOR",
                    actor_instance=gate_policy,
                    method=FACTORIAL_VERSION,
                    result_state="CANDIDATE",
                    result={
                        key: payload[key]
                        for key in (
                            "selected_object",
                            "selection_basis",
                            "pragmatic_preference",
                            "evidence_state",
                            "assessment_process_state",
                            "action",
                        )
                    },
                    evidence_refs=evidence_refs,
                    support=(payload["rationale"],),
                    uncertainty=round(1 - payload["confidence"], 6),
                    recommended_next_actions=(
                        ("CLARIFY",)
                        if payload["action"] == "CLARIFY"
                        else ("ABSTAIN",)
                        if payload["action"] == "ABSTAIN"
                        else ("FALSIFY",)
                    ),
                    cost=ActionCost(),
                )
                commitment = {
                    "cell": cell,
                    "source_prompt_policy": prompt_policy,
                    "gate_policy": gate_policy,
                    "conflict_id": item["conflict_id"],
                    "payload": payload,
                    "gate_transforms": gated["gate_transforms"],
                    "source_call_hash": source_call["source_call_hash"],
                    "gate_action_receipt": gate_action_receipt,
                    "reference_available": False,
                }
                outputs.append({
                    **commitment,
                    "output_hash": hash_payload(commitment),
                })
    commitment = {
        "runtime_version": FACTORIAL_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_calls": source_calls,
        "outputs": outputs,
        "failures": failures,
        "source_prompt_order_counterbalanced": True,
        "provider_calls_shared_across_gate_cells": True,
        "cross_cell_output_substitution": False,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_factorial_run(*, corpus, run):
    outputs = {cell: {} for cell in CELLS}
    for output in run["outputs"]:
        outputs[output["cell"]][output["conflict_id"]] = output
    source_accounting = {policy: Counter() for policy in SOURCE_PROMPTS}
    source_distribution = {policy: Counter() for policy in SOURCE_PROMPTS}
    source_coverage = {policy: 0 for policy in SOURCE_PROMPTS}
    for call in run["source_calls"]:
        if call["status"] != "COMPLETED":
            continue
        policy = call["source_prompt_policy"]
        source_coverage[policy] += 1
        source_distribution[policy][
            call["source_receipt"]["definition_source"]
        ] += 1
        source_accounting[policy].update(
            call["source_action_receipt"]["cost"]
        )
    cell_coverage = {
        cell: round(len(values) / corpus["case_count"], 6)
        for cell, values in outputs.items()
    }
    state_distribution = {
        cell: dict(Counter(
            output["payload"]["evidence_state"]
            for output in values.values()
        ))
        for cell, values in outputs.items()
    }
    transform_distribution = {
        cell: dict(Counter(
            transform
            for output in values.values()
            for transform in output["gate_transforms"]
        ))
        for cell, values in outputs.items()
    }
    source_tokens = {
        policy: (
            source_accounting[policy]["input_tokens"]
            + source_accounting[policy]["output_tokens"]
        )
        for policy in SOURCE_PROMPTS
    }
    structural_effects = {
        "gate_coverage_gain_under_legacy_source": round(
            cell_coverage["LEGACY_SOURCE_REPAIRED_GATE"]
            - cell_coverage["LEGACY_SOURCE_LEGACY_GATE"],
            6,
        ),
        "gate_coverage_gain_under_repaired_source": round(
            cell_coverage["REPAIRED_SOURCE_REPAIRED_GATE"]
            - cell_coverage["REPAIRED_SOURCE_LEGACY_GATE"],
            6,
        ),
        "source_coverage_gain_under_legacy_gate": round(
            cell_coverage["REPAIRED_SOURCE_LEGACY_GATE"]
            - cell_coverage["LEGACY_SOURCE_LEGACY_GATE"],
            6,
        ),
        "source_coverage_gain_under_repaired_gate": round(
            cell_coverage["REPAIRED_SOURCE_REPAIRED_GATE"]
            - cell_coverage["LEGACY_SOURCE_REPAIRED_GATE"],
            6,
        ),
    }
    failure_counts = Counter()
    for failure in run["failures"]:
        key = failure.get("cell") or failure.get("source_prompt_policy")
        failure_counts[key] += 1
    commitment = {
        "analysis_version": FACTORIAL_VERSION,
        "source_run_hash": run["run_hash"],
        "source_call_coverage": {
            policy: round(source_coverage[policy] / corpus["case_count"], 6)
            for policy in SOURCE_PROMPTS
        },
        "cell_coverage": cell_coverage,
        "evidence_state_distributions": state_distribution,
        "definition_source_distributions": {
            policy: dict(values)
            for policy, values in source_distribution.items()
        },
        "gate_transform_distributions": transform_distribution,
        "failure_counts": dict(failure_counts),
        "source_accounting": {
            policy: dict(values)
            for policy, values in source_accounting.items()
        },
        "source_total_tokens": source_tokens,
        "repaired_to_legacy_source_token_ratio": (
            round(
                source_tokens[REPAIRED_SOURCE_PROMPT]
                / source_tokens[LEGACY_SOURCE_PROMPT],
                6,
            )
            if source_tokens[LEGACY_SOURCE_PROMPT]
            else None
        ),
        "structural_factor_effects": structural_effects,
        "provider_calls_shared_across_gate_cells": True,
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": (
            "EVIDENCE_FACTORIAL_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(*, item, prompt_policy, evidence_refs, adapter):
    if prompt_policy == LEGACY_SOURCE_PROMPT:
        objective = (
            "Identify the operative source that determines or fails to determine "
            "the requested object. EXPLICIT_REQUEST_DEFINITION requires an explicit "
            "defining clause in the request; ESTABLISHED_UNAMBIGUOUS_TERM requires "
            "a genuinely standard term with one relevant meaning; "
            "COMPOSED_CONSTRAINTS requires combining multiple constraints; "
            "MISSING_EXTERNAL_SPECIFICATION requires a named absent codebook, "
            "policy, calendar, or state model; UNDERSPECIFIED_SURFACE means the "
            "displayed request leaves multiple candidates open; CONFLICTING_SURFACE "
            "means displayed constraints clash; UNRESOLVED is residual uncertainty. "
            "Candidate option text is never itself definition evidence. Quote the "
            "request phrase supporting the source. Keep pragmatic preference "
            "separate from semantic selection."
        )
    elif prompt_policy == REPAIRED_SOURCE_PROMPT:
        objective = (
            "Identify the operative definition source before selecting an object. "
            "EXPLICIT_REQUEST_DEFINITION requires a positive clause that assigns an "
            "operational meaning. A sentence saying a term is undefined, unspecified, "
            "missing, unavailable, or not operationally defined is evidence of absent "
            "definition and must never count as an explicit definition. Use "
            "MISSING_EXTERNAL_SPECIFICATION only when a named external rule, token, "
            "profile, dictionary, catalog, or state model is required but absent. Use "
            "UNDERSPECIFIED_SURFACE when an ordinary displayed term leaves multiple "
            "candidate meanings open. Use COMPOSED_CONSTRAINTS only when combining "
            "displayed constraints determines one candidate. Candidate option text is "
            "never definition evidence. For recognized soft ambiguity or a missing "
            "external specification, select NONE; use a candidate pragmatic preference "
            "only when context supports a default, otherwise use NONE. Assessment "
            "completion means the evidence status can be justified, not that a "
            "candidate was selected, so a justified open or opaque conclusion may be "
            "COMPLETE. Quote the exact source phrase and explain the distinction."
        )
    else:
        raise ValueError("evidence_source_prompt_unknown")
    return ProviderCognitiveTask(
        task_id=(
            f"{FACTORIAL_VERSION}-{prompt_policy.lower()}-"
            f"{item['conflict_id']}"
        ),
        task_kind=FACTORIAL_TASK_KIND,
        objective=objective,
        inputs={
            "source_prompt_policy": prompt_policy,
            "public_object": item,
            "external_reference": "WITHHELD",
        },
        allowed_evidence=list(evidence_refs),
        expected_schema=source_schema(item["conflict_id"], evidence_refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics=(
            "preserve_source_failure_without_cross_cell_substitution"
        ),
    )


def _source_call(
    *,
    item,
    prompt_policy,
    task,
    invocation,
    status,
    source_receipt,
    source_action_receipt,
):
    commitment = {
        "source_prompt_policy": prompt_policy,
        "conflict_id": item["conflict_id"],
        "status": status,
        "source_receipt": source_receipt,
        "source_action_receipt": source_action_receipt,
        "invocation_receipt": invocation,
        "task_contract_hash": task.contract_hash(),
        "reference_available": False,
    }
    return {**commitment, "source_call_hash": hash_payload(commitment)}


def _usage_cost(usage):
    return ActionCost(
        provider_calls=max(1, int(usage.get("provider_calls") or 1)),
        input_tokens=int(
            usage.get("prompt_tokens") or usage.get("input_tokens") or 0
        ),
        output_tokens=int(
            usage.get("completion_tokens") or usage.get("output_tokens") or 0
        ),
        latency_ms=int(usage.get("latency_ms") or 0),
    )
