"""Decomposed source-ontology ablation v0.21."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_calibrator import source_schema
from .cognitive_action_evidence_gate_policies import (
    REPAIRED_GATE,
    apply_gate_policy,
)
from .cognitive_action_protocol import ActionCost, build_action_receipt
from .cognitive_action_selective_runtime import (
    PROCESS_STATES,
    SELECTIONS,
    validate_selective_tuple,
)
from .cognitive_action_source_ontology_holdout import (
    validate_source_ontology_holdout,
)
from .provider_telemetry import hash_payload


SOURCE_ONTOLOGY_VERSION = "cognitive_action_source_ontology_ablation_v0_21"
SOURCE_ONTOLOGY_TASK_KIND = "COGNITIVE_ACTION_SOURCE_ONTOLOGY_ABLATION"
SOURCE_EVALUATION_HASH = (
    "21b9c1344d3f18b135ed1aa38625aaf42a187e3c147affbf012939d003186990"
)
SOURCE_REFERENCE_HASH = (
    "b63a0908ce9eb730501052f3e41e6a51bdc48688122dc513d596a50b41583d72"
)
BASELINE_SOURCE = "LEGACY_SOURCE_BASELINE_V0_20"
AXIS_SOURCE = "DECOMPOSED_AXIS_SOURCE_V0_21"
SOURCE_POLICIES = (BASELINE_SOURCE, AXIS_SOURCE)
BASELINE_CELL = "BASELINE_LEGACY_SOURCE_REPAIRED_GATE"
COLLAPSED_CELL = "AXIS_SOURCE_COLLAPSED_REPAIRED_GATE"
NATIVE_CELL = "AXIS_SOURCE_NATIVE_GATE"
CELLS = (BASELINE_CELL, COLLAPSED_CELL, NATIVE_CELL)
AXIS_VALUES = ("CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN")
EXTERNAL_DEPENDENCIES = (
    "NOT_REQUIRED",
    "REQUIRED_AVAILABLE",
    "REQUIRED_MISSING",
    "UNCERTAIN",
)


def build_source_ontology_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state")
        != "EVIDENCE_FACTORIAL_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("source_ontology_source_evaluation_invalid")
    commitment = {
        "preregistration_version": SOURCE_ONTOLOGY_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": (
            "independent lexical compositional and external-dependency axes "
            "preserve gate-only gains while reducing source-induced false "
            "soft admissions"
        ),
        "arms": list(CELLS),
        "design": {
            "provider_source_policies": list(SOURCE_POLICIES),
            "provider_call_count_per_object": 2,
            "axis_receipt_reused_by_two_runtime_paths": True,
            "baseline_gate": REPAIRED_GATE,
            "collapsed_path": (
                "axis receipt mechanically collapsed to legacy source enum "
                "before repaired gate"
            ),
            "native_path": (
                "runtime synthesizes evidence state from independent axes"
            ),
        },
        "axis_invariants": {
            "lexical_definition_requires_positive_defining_clause": True,
            "compositional_derivation_is_independent_of_lexical_definition": True,
            "external_spec_dependency_is_independent_of_surface_openness": True,
            "candidate_option_text_is_not_evidence": True,
            "assessment_completion_is_separate_from_object_selection": True,
            "runtime_resolves_cross_axis_conflict_fail_closed": True,
        },
        "success_gate": {
            "minimum_native_admission_precision": 0.75,
            "minimum_native_soft_ambiguity_recall": 0.67,
            "minimum_native_evidence_state_accuracy": 0.75,
            "minimum_native_evidence_correct_gain_over_baseline": 3,
            "maximum_native_selected_object_loss_vs_baseline": 1,
            "minimum_native_output_coverage": 0.95,
            "maximum_axis_to_baseline_source_token_ratio": 1.35,
            "maximum_native_false_soft_admissions": 1,
        },
        "collapsed_path_is_diagnostic_not_independently_promotable": True,
        "v0_20_labels_used_as_failure_mechanism_only": True,
        "fresh_v0_21_labels_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def axis_source_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "lexical_definition",
            "compositional_derivation",
            "external_spec_dependency",
            "pragmatic_preference",
            "assessment_process_state",
            "support_quotes",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "lexical_definition": {
                "type": "string",
                "enum": list(AXIS_VALUES),
            },
            "compositional_derivation": {
                "type": "string",
                "enum": list(AXIS_VALUES),
            },
            "external_spec_dependency": {
                "type": "string",
                "enum": list(EXTERNAL_DEPENDENCIES),
            },
            "pragmatic_preference": {
                "type": "string",
                "enum": list(SELECTIONS),
            },
            "assessment_process_state": {
                "type": "string",
                "enum": list(PROCESS_STATES),
            },
            "support_quotes": {
                "type": "object",
                "additionalProperties": False,
                "required": ["lexical", "compositional", "external"],
                "properties": {
                    key: {
                        "type": "string",
                        "minLength": 1,
                        "maxLength": 400,
                    }
                    for key in ("lexical", "compositional", "external")
                },
            },
            "rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 1000,
            },
            "confidence": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
            },
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {
                    "type": "string",
                    "enum": list(evidence_refs),
                },
            },
        },
    }


def validate_axis_source_receipt(receipt, *, conflict_id, evidence_refs):
    required = set(axis_source_schema(conflict_id, evidence_refs)["required"])
    quotes = receipt.get("support_quotes") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != conflict_id
        or receipt.get("lexical_definition") not in AXIS_VALUES
        or receipt.get("compositional_derivation") not in AXIS_VALUES
        or receipt.get("external_spec_dependency")
        not in EXTERNAL_DEPENDENCIES
        or receipt.get("pragmatic_preference") not in SELECTIONS
        or receipt.get("assessment_process_state") not in PROCESS_STATES
        or receipt.get("evidence_refs") != list(evidence_refs)
        or not isinstance(quotes, dict)
        or set(quotes) != {"lexical", "compositional", "external"}
        or any(
            not isinstance(value, str) or not value.strip()
            for value in quotes.values()
        )
        or not isinstance(receipt.get("rationale"), str)
        or not receipt["rationale"].strip()
        or not isinstance(receipt.get("confidence"), (int, float))
        or isinstance(receipt.get("confidence"), bool)
        or not 0 <= receipt["confidence"] <= 1
    ):
        raise ValueError("source_ontology_axis_receipt_invalid")


def normalize_axis_native(receipt, *, conflict_id, evidence_refs):
    validate_axis_source_receipt(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    lexical = receipt["lexical_definition"]
    composed = receipt["compositional_derivation"]
    external = receipt["external_spec_dependency"]
    preference = receipt["pragmatic_preference"]
    transforms = []
    decisive = ("CANDIDATE_A", "CANDIDATE_B")

    if external == "REQUIRED_MISSING":
        if lexical in decisive or composed in decisive:
            return _uncertain_payload(
                receipt,
                conflict_id,
                evidence_refs,
                "MISSING_SPEC_CONFLICTS_WITH_DECISIVE_AXIS",
            )
        if preference != "NONE":
            preference = "NONE"
            transforms.append("OPAQUE_PREFERENCE_TO_NONE")
        state, selected, basis, process = (
            "OPAQUE_REFERENCE",
            "NONE",
            "NO_PREFERENCE",
            "COMPLETE",
        )
    elif external == "UNCERTAIN":
        return _uncertain_payload(
            receipt,
            conflict_id,
            evidence_refs,
            "EXTERNAL_DEPENDENCY_UNCERTAIN",
        )
    elif lexical in decisive and composed in decisive and lexical != composed:
        return _uncertain_payload(
            receipt,
            conflict_id,
            evidence_refs,
            "LEXICAL_COMPOSITIONAL_CONFLICT",
            evidence_state="CONFLICTED",
        )
    elif lexical in decisive:
        state, selected, basis, process = (
            "DIRECTLY_DEFINED",
            lexical,
            "LEXICAL_EXACT",
            "COMPLETE",
        )
    elif lexical == "NONE" and composed in decisive:
        state, selected, basis, process = (
            "COMPOSITIONALLY_DETERMINED",
            composed,
            "COMPOSITIONAL_ENTAILMENT",
            "COMPLETE",
        )
    elif lexical == "NONE" and composed == "NONE" and external == "NOT_REQUIRED":
        if preference == "UNCERTAIN":
            preference = "NONE"
            transforms.append("UNSUPPORTED_PREFERENCE_TO_NONE")
        state, selected, basis, process = (
            "SOFT_AMBIGUITY",
            "NONE",
            (
                "PRAGMATIC_DEFAULT"
                if preference in decisive
                else "NO_PREFERENCE"
            ),
            "COMPLETE",
        )
    else:
        return _uncertain_payload(
            receipt,
            conflict_id,
            evidence_refs,
            "AXIS_COMBINATION_UNRESOLVED",
        )

    if receipt["assessment_process_state"] != process:
        transforms.append("RECOGNIZED_STATE_TO_COMPLETE_ASSESSMENT")
    payload = _payload(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
        selected=selected,
        basis=basis,
        preference=preference,
        state=state,
        process=process,
    )
    return {
        "payload": payload,
        "gate_transforms": transforms,
        "gate_policy": "AXIS_NATIVE_GATE_V0_21",
    }


def collapse_axis_to_legacy(receipt, *, conflict_id, evidence_refs):
    validate_axis_source_receipt(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    lexical = receipt["lexical_definition"]
    composed = receipt["compositional_derivation"]
    external = receipt["external_spec_dependency"]
    decisive = ("CANDIDATE_A", "CANDIDATE_B")
    if external == "REQUIRED_MISSING" and (
        lexical in decisive or composed in decisive
    ):
        source, selected, preference = (
            "CONFLICTING_SURFACE",
            "UNCERTAIN",
            "UNCERTAIN",
        )
    elif external == "REQUIRED_MISSING":
        source, selected, preference = (
            "MISSING_EXTERNAL_SPECIFICATION",
            "NONE",
            "NONE",
        )
    elif external == "UNCERTAIN":
        source, selected, preference = (
            "UNRESOLVED",
            "UNCERTAIN",
            "UNCERTAIN",
        )
    elif lexical in decisive and composed in decisive and lexical != composed:
        source, selected, preference = (
            "CONFLICTING_SURFACE",
            "UNCERTAIN",
            "UNCERTAIN",
        )
    elif lexical in decisive:
        source, selected, preference = (
            "EXPLICIT_REQUEST_DEFINITION",
            lexical,
            receipt["pragmatic_preference"],
        )
    elif lexical == "NONE" and composed in decisive:
        source, selected, preference = (
            "COMPOSED_CONSTRAINTS",
            composed,
            receipt["pragmatic_preference"],
        )
    elif lexical == "NONE" and composed == "NONE" and external == "NOT_REQUIRED":
        source, selected, preference = (
            "UNDERSPECIFIED_SURFACE",
            "NONE",
            receipt["pragmatic_preference"],
        )
    else:
        source, selected, preference = (
            "UNRESOLVED",
            "UNCERTAIN",
            "UNCERTAIN",
        )
    return {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "definition_source": source,
        "pragmatic_preference": preference,
        "assessment_process_state": receipt["assessment_process_state"],
        "support_quote": " | ".join(receipt["support_quotes"].values()),
        "rationale": receipt["rationale"],
        "confidence": receipt["confidence"],
        "evidence_refs": list(evidence_refs),
    }


def run_source_ontology_ablation(*, corpus, preregistration, adapter):
    validate_source_ontology_holdout(corpus)
    if (
        preregistration.get("preregistration_version")
        != SOURCE_ONTOLOGY_VERSION
        or preregistration.get("artifact_hash")
        != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("source_ontology_preregistration_invalid")
    refs = tuple(corpus["evidence_refs"])
    source_calls, outputs, failures = [], [], []
    for item in corpus["public_surface"]["items"]:
        order = (
            SOURCE_POLICIES
            if int(hash_payload([
                SOURCE_ONTOLOGY_VERSION,
                item["conflict_id"],
            ])[:2], 16) % 2 == 0
            else tuple(reversed(SOURCE_POLICIES))
        )
        for policy in order:
            task = _task(
                item=item,
                policy=policy,
                evidence_refs=refs,
                adapter=adapter,
            )
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            if envelope.status != "COMPLETED":
                call = _source_call(
                    policy,
                    item["conflict_id"],
                    task,
                    invocation,
                    envelope.status,
                    None,
                )
                source_calls.append(call)
                failures.append({
                    "stage": "SOURCE_PROVIDER",
                    "source_policy": policy,
                    "conflict_id": item["conflict_id"],
                    "status": envelope.status,
                    "validation_errors": list(envelope.validation_errors),
                    "source_call_hash": call["source_call_hash"],
                })
                continue
            receipt = envelope.normalized_result
            call = _source_call(
                policy,
                item["conflict_id"],
                task,
                invocation,
                "COMPLETED",
                receipt,
            )
            source_calls.append(call)
            if policy == BASELINE_SOURCE:
                paths = ((BASELINE_CELL, _baseline_gate),)
            else:
                paths = (
                    (COLLAPSED_CELL, _collapsed_gate),
                    (NATIVE_CELL, normalize_axis_native),
                )
            for cell, gate in paths:
                try:
                    gated = gate(
                        receipt,
                        conflict_id=item["conflict_id"],
                        evidence_refs=refs,
                    )
                except ValueError as exc:
                    failures.append({
                        "stage": "RUNTIME_GATE",
                        "cell": cell,
                        "source_policy": policy,
                        "conflict_id": item["conflict_id"],
                        "status": "SEMANTIC_VALIDATION_FAILED",
                        "validation_errors": [str(exc)],
                        "source_call_hash": call["source_call_hash"],
                        "provider_receipt_preserved": receipt,
                    })
                    continue
                outputs.append(_output(
                    cell=cell,
                    policy=policy,
                    conflict_id=item["conflict_id"],
                    gated=gated,
                    source_call=call,
                    invocation=invocation,
                    evidence_refs=refs,
                    model_id=adapter.profile.model_id,
                ))
    commitment = {
        "runtime_version": SOURCE_ONTOLOGY_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_calls": source_calls,
        "outputs": outputs,
        "failures": failures,
        "source_policy_order_counterbalanced": True,
        "axis_receipt_reused_across_runtime_paths": True,
        "cross_cell_output_substitution": False,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_source_ontology_run(*, corpus, run):
    by_cell = {cell: {} for cell in CELLS}
    accounting = {policy: Counter() for policy in SOURCE_POLICIES}
    source_coverage = {policy: 0 for policy in SOURCE_POLICIES}
    axis_distributions = {
        key: Counter()
        for key in (
            "lexical_definition",
            "compositional_derivation",
            "external_spec_dependency",
        )
    }
    for call in run["source_calls"]:
        if call["status"] != "COMPLETED":
            continue
        policy = call["source_policy"]
        source_coverage[policy] += 1
        usage = call["invocation_receipt"].get("token_usage") or {}
        accounting[policy].update({
            "provider_calls": int(usage.get("provider_calls") or 1),
            "input_tokens": int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            ),
            "output_tokens": int(
                usage.get("completion_tokens")
                or usage.get("output_tokens")
                or 0
            ),
            "latency_ms": int(usage.get("latency_ms") or 0),
        })
        if policy == AXIS_SOURCE:
            for axis in axis_distributions:
                axis_distributions[axis][call["source_receipt"][axis]] += 1
    for output in run["outputs"]:
        by_cell[output["cell"]][output["conflict_id"]] = output
    common = set.intersection(*(
        set(values) for values in by_cell.values()
    ))
    pairwise = {}
    for left, right in (
        (BASELINE_CELL, COLLAPSED_CELL),
        (BASELINE_CELL, NATIVE_CELL),
        (COLLAPSED_CELL, NATIVE_CELL),
    ):
        pairwise[f"{left}|{right}"] = {
            axis: sum(
                by_cell[left][case]["payload"][axis]
                != by_cell[right][case]["payload"][axis]
                for case in common
            )
            for axis in (
                "selected_object",
                "selection_basis",
                "pragmatic_preference",
                "evidence_state",
                "assessment_process_state",
            )
        }
    tokens = {
        policy: (
            accounting[policy]["input_tokens"]
            + accounting[policy]["output_tokens"]
        )
        for policy in SOURCE_POLICIES
    }
    failure_counts = Counter(
        failure.get("cell") or failure.get("source_policy")
        for failure in run["failures"]
    )
    commitment = {
        "analysis_version": SOURCE_ONTOLOGY_VERSION,
        "source_run_hash": run["run_hash"],
        "source_call_coverage": {
            policy: round(
                source_coverage[policy] / corpus["case_count"],
                6,
            )
            for policy in SOURCE_POLICIES
        },
        "cell_coverage": {
            cell: round(len(values) / corpus["case_count"], 6)
            for cell, values in by_cell.items()
        },
        "common_case_count": len(common),
        "evidence_state_distributions": {
            cell: dict(Counter(
                output["payload"]["evidence_state"]
                for output in values.values()
            ))
            for cell, values in by_cell.items()
        },
        "axis_source_distributions": {
            axis: dict(values)
            for axis, values in axis_distributions.items()
        },
        "pairwise_axis_disagreement_counts": pairwise,
        "failure_counts": dict(failure_counts),
        "source_accounting": {
            policy: dict(values)
            for policy, values in accounting.items()
        },
        "source_total_tokens": tokens,
        "axis_to_baseline_source_token_ratio": (
            round(tokens[AXIS_SOURCE] / tokens[BASELINE_SOURCE], 6)
            if tokens[BASELINE_SOURCE]
            else None
        ),
        "provider_calls_shared_across_axis_runtime_paths": True,
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": (
            "SOURCE_ONTOLOGY_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _baseline_gate(receipt, *, conflict_id, evidence_refs):
    return apply_gate_policy(
        REPAIRED_GATE,
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )


def _collapsed_gate(receipt, *, conflict_id, evidence_refs):
    collapsed = collapse_axis_to_legacy(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    gated = apply_gate_policy(
        REPAIRED_GATE,
        collapsed,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    return {
        **gated,
        "gate_policy": "AXIS_COLLAPSE_THEN_REPAIRED_GATE_V0_21",
        "collapsed_source_receipt": collapsed,
    }


def _uncertain_payload(
    receipt,
    conflict_id,
    evidence_refs,
    transform,
    *,
    evidence_state="UNCERTAIN",
):
    payload = _payload(
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
        selected="UNCERTAIN",
        basis="UNCERTAIN",
        preference="UNCERTAIN",
        state=evidence_state,
        process=receipt["assessment_process_state"],
    )
    return {
        "payload": payload,
        "gate_transforms": [transform],
        "gate_policy": "AXIS_NATIVE_GATE_V0_21",
    }


def _payload(
    receipt,
    *,
    conflict_id,
    evidence_refs,
    selected,
    basis,
    preference,
    state,
    process,
):
    payload = {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "selection_basis": basis,
        "pragmatic_preference": preference,
        "evidence_state": state,
        "assessment_process_state": process,
        "action": (
            "ACCEPT"
            if selected in ("CANDIDATE_A", "CANDIDATE_B")
            else "CLARIFY"
            if selected == "NONE"
            else "ABSTAIN"
        ),
        "rationale": receipt["rationale"],
        "confidence": receipt["confidence"],
        "evidence_refs": list(evidence_refs),
    }
    validate_selective_tuple(
        payload,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    return payload


def _task(*, item, policy, evidence_refs, adapter):
    if policy == BASELINE_SOURCE:
        objective = (
            "Identify the operative source that determines or fails to "
            "determine the requested object. EXPLICIT_REQUEST_DEFINITION "
            "requires a positive defining clause; COMPOSED_CONSTRAINTS "
            "requires combining displayed constraints; "
            "MISSING_EXTERNAL_SPECIFICATION requires a named absent rule, "
            "token, calendar, catalog, or state model; "
            "UNDERSPECIFIED_SURFACE means ordinary displayed wording leaves "
            "multiple candidates open. Candidate option text is not evidence. "
            "Keep semantic selection separate from pragmatic preference, and "
            "treat a justified open conclusion as a complete assessment."
        )
        schema = source_schema(item["conflict_id"], evidence_refs)
    elif policy == AXIS_SOURCE:
        objective = (
            "Assess the evidence through independent axes before any final "
            "evidence-state label. lexical_definition asks whether a positive "
            "displayed defining clause directly fixes candidate A or B; use "
            "NONE when no such clause exists. compositional_derivation asks "
            "separately whether combining displayed constraints entails A or "
            "B; absence of a lexical definition does not imply absence of a "
            "composition. external_spec_dependency asks independently whether "
            "a named external rule is required and available, required but "
            "missing, not required, or uncertain. A missing lexical definition "
            "is not automatically a missing external specification. Candidate "
            "option text is never evidence. pragmatic_preference records only "
            "a contextual default when neither semantic axis determines an "
            "object. Quote support for each axis; write NONE when the prompt "
            "contains no supporting phrase. Assessment completion is separate "
            "from object selection."
        )
        schema = axis_source_schema(item["conflict_id"], evidence_refs)
    else:
        raise ValueError("source_ontology_policy_unknown")
    return ProviderCognitiveTask(
        task_id=(
            f"{SOURCE_ONTOLOGY_VERSION}-{policy.lower()}-"
            f"{item['conflict_id']}"
        ),
        task_kind=SOURCE_ONTOLOGY_TASK_KIND,
        objective=objective,
        inputs={
            "source_policy": policy,
            "public_object": item,
            "external_reference": "WITHHELD",
        },
        allowed_evidence=list(evidence_refs),
        expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics=(
            "preserve_source_failure_without_cross_arm_substitution"
        ),
    )


def _source_call(
    policy,
    conflict_id,
    task,
    invocation,
    status,
    receipt,
):
    commitment = {
        "source_policy": policy,
        "conflict_id": conflict_id,
        "status": status,
        "source_receipt": receipt,
        "invocation_receipt": invocation,
        "task_contract_hash": task.contract_hash(),
        "reference_available": False,
    }
    return {**commitment, "source_call_hash": hash_payload(commitment)}


def _output(
    *,
    cell,
    policy,
    conflict_id,
    gated,
    source_call,
    invocation,
    evidence_refs,
    model_id,
):
    payload = gated["payload"]
    usage = invocation.get("token_usage") or {}
    receipt = build_action_receipt(
        action_id="action-" + hash_payload([
            SOURCE_ONTOLOGY_VERSION,
            cell,
            conflict_id,
        ])[:18],
        action_type="VALIDATE",
        object_ref="object://" + conflict_id,
        actor_role="REPLICATOR",
        actor_instance=f"{model_id}:{gated['gate_policy']}",
        method=SOURCE_ONTOLOGY_VERSION,
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
        cost=ActionCost(
            provider_calls=0,
            input_tokens=0,
            output_tokens=0,
            latency_ms=0,
        ),
    )
    commitment = {
        "cell": cell,
        "source_policy": policy,
        "gate_policy": gated["gate_policy"],
        "conflict_id": conflict_id,
        "payload": payload,
        "gate_transforms": gated["gate_transforms"],
        "collapsed_source_receipt": gated.get("collapsed_source_receipt"),
        "source_call_hash": source_call["source_call_hash"],
        "gate_action_receipt": receipt,
        "provider_cost_charged_on_source_call_only": True,
        "reference_available": False,
    }
    return {**commitment, "output_hash": hash_payload(commitment)}
