"""Contrastive definition-source calibrator v0.19."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_holdout import validate_evidence_holdout
from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .cognitive_action_selective_runtime import (
    PROCESS_STATES,
    SELECTIONS,
    selective_tuple_schema,
    validate_selective_tuple,
)
from .provider_telemetry import hash_payload


EVIDENCE_CALIBRATOR_VERSION = "cognitive_action_evidence_calibrator_v0_19"
EVIDENCE_TASK_KIND = "COGNITIVE_ACTION_EVIDENCE_STATE_CALIBRATION"
SOURCE_EVALUATION_HASH = "7fb722edcd8df70ee16ea7706ccd0b6d05da96672cdb66b17d851ea0fdb88c0a"
SOURCE_REFERENCE_HASH = "efc6c9662da349112238ddbd7b68e43c3aa04cbece0aa45111b1918859f3c8aa"
ARMS = ("FREE_LABEL_CONTROL", "CONTRASTIVE_SOURCE_CALIBRATOR")
DEFINITION_SOURCES = (
    "EXPLICIT_REQUEST_DEFINITION",
    "ESTABLISHED_UNAMBIGUOUS_TERM",
    "COMPOSED_CONSTRAINTS",
    "MISSING_EXTERNAL_SPECIFICATION",
    "UNDERSPECIFIED_SURFACE",
    "CONFLICTING_SURFACE",
    "UNRESOLVED",
)
SOURCE_TO_STATE = {
    "EXPLICIT_REQUEST_DEFINITION": "DIRECTLY_DEFINED",
    "ESTABLISHED_UNAMBIGUOUS_TERM": "DIRECTLY_DEFINED",
    "COMPOSED_CONSTRAINTS": "COMPOSITIONALLY_DETERMINED",
    "MISSING_EXTERNAL_SPECIFICATION": "OPAQUE_REFERENCE",
    "UNDERSPECIFIED_SURFACE": "SOFT_AMBIGUITY",
    "CONFLICTING_SURFACE": "CONFLICTED",
    "UNRESOLVED": "UNCERTAIN",
}


def build_evidence_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state") != "SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("evidence_source_evaluation_invalid")
    commitment = {
        "preregistration_version": EVIDENCE_CALIBRATOR_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": "definition_source_contrast_reduces_false_direct_definition_and_recovers_soft_ambiguity",
        "arms": list(ARMS),
        "contrastive_rule": {
            "provider_selects_definition_source": True,
            "runtime_maps_source_to_evidence_state": True,
            "candidate_option_text_counts_as_definition": False,
            "direct_definition_requires_request_operator_or_unambiguous_established_term": True,
        },
        "success_gate": {
            "minimum_admission_precision": 0.75,
            "minimum_soft_ambiguity_recall": 0.67,
            "minimum_evidence_state_accuracy": 0.70,
            "minimum_evidence_correct_case_gain_over_control": 4,
            "maximum_selected_object_case_loss_vs_control": 1,
            "minimum_output_coverage": 0.95,
            "maximum_calibrator_to_control_token_ratio": 1.50,
        },
        "v0_18_labels_used_as_diagnostic_only": True,
        "fresh_v0_19_labels_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def source_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id", "selected_object", "definition_source",
            "pragmatic_preference", "assessment_process_state",
            "support_quote", "rationale", "confidence", "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "selected_object": {"type": "string", "enum": list(SELECTIONS)},
            "definition_source": {"type": "string", "enum": list(DEFINITION_SOURCES)},
            "pragmatic_preference": {"type": "string", "enum": list(SELECTIONS)},
            "assessment_process_state": {"type": "string", "enum": list(PROCESS_STATES)},
            "support_quote": {"type": "string", "minLength": 1, "maxLength": 400},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 800},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {"type": "array", "minItems": len(evidence_refs), "maxItems": len(evidence_refs), "items": {"type": "string", "enum": list(evidence_refs)}},
        },
    }


def run_evidence_arms(*, corpus, preregistration, adapter):
    validate_evidence_holdout(corpus)
    if preregistration.get("preregistration_version") != EVIDENCE_CALIBRATOR_VERSION:
        raise ValueError("evidence_preregistration_missing")
    outputs, failures = [], []
    refs = tuple(corpus["evidence_refs"])
    for item in corpus["public_surface"]["items"]:
        order = ARMS if int(hash_payload([EVIDENCE_CALIBRATOR_VERSION, item["conflict_id"]])[:2], 16) % 2 == 0 else tuple(reversed(ARMS))
        for arm in order:
            task = _task(item=item, arm=arm, evidence_refs=refs, adapter=adapter)
            envelope = ProviderTaskRouter([adapter]).route(task)
            invocation = envelope.invocation_receipt.as_dict()
            if envelope.status != "COMPLETED":
                failures.append(_failure(arm, item["conflict_id"], envelope, invocation))
                continue
            try:
                if arm == "FREE_LABEL_CONTROL":
                    payload = envelope.normalized_result
                    validate_selective_tuple(payload, conflict_id=item["conflict_id"], evidence_refs=refs)
                    source_receipt = None
                else:
                    source_receipt = envelope.normalized_result
                    payload = normalize_source_receipt(source_receipt, conflict_id=item["conflict_id"], evidence_refs=refs)
            except ValueError as exc:
                failures.append({
                    "arm": arm, "conflict_id": item["conflict_id"],
                    "status": "SEMANTIC_VALIDATION_FAILED",
                    "validation_errors": [str(exc)],
                    "provider_payload": envelope.normalized_result,
                    "invocation_receipt": invocation,
                })
                continue
            usage = invocation.get("token_usage") or {}
            receipt = build_action_receipt(
                action_id="action-" + hash_payload([EVIDENCE_CALIBRATOR_VERSION, arm, item["conflict_id"]])[:18],
                action_type="SYNTHESIZE",
                object_ref="object://" + item["conflict_id"],
                actor_role="COORDINATOR",
                actor_instance=f"{adapter.profile.model_id}:{arm}",
                method=EVIDENCE_CALIBRATOR_VERSION,
                result_state="CANDIDATE",
                result={key: payload[key] for key in ("selected_object", "selection_basis", "pragmatic_preference", "evidence_state", "assessment_process_state", "action")},
                evidence_refs=refs,
                support=(payload["rationale"],),
                uncertainty=round(1 - payload["confidence"], 6),
                recommended_next_actions=("CLARIFY",) if payload["action"] == "CLARIFY" else ("ABSTAIN",) if payload["action"] == "ABSTAIN" else ("FALSIFY",),
                cost=_usage_cost(usage),
            )
            commitment = {
                "arm": arm,
                "conflict_id": item["conflict_id"],
                "payload": payload,
                "definition_source_receipt": source_receipt,
                "action_receipt": receipt,
                "invocation_receipt": invocation,
                "task_contract_hash": task.contract_hash(),
                "reference_available": False,
            }
            outputs.append({**commitment, "output_hash": hash_payload(commitment)})
    commitment = {
        "runtime_version": EVIDENCE_CALIBRATOR_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "outputs": outputs,
        "failures": failures,
        "arm_order_counterbalanced": True,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def normalize_source_receipt(receipt, *, conflict_id, evidence_refs):
    required = set(source_schema(conflict_id, evidence_refs)["required"])
    if (
        not isinstance(receipt, dict) or set(receipt) != required
        or receipt.get("conflict_id") != conflict_id
        or receipt.get("definition_source") not in DEFINITION_SOURCES
        or receipt.get("selected_object") not in SELECTIONS
        or receipt.get("pragmatic_preference") not in SELECTIONS
        or receipt.get("assessment_process_state") not in PROCESS_STATES
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("evidence_source_receipt_invalid")
    source = receipt["definition_source"]
    selected, preference = receipt["selected_object"], receipt["pragmatic_preference"]
    if source in ("EXPLICIT_REQUEST_DEFINITION", "ESTABLISHED_UNAMBIGUOUS_TERM", "COMPOSED_CONSTRAINTS") and selected not in ("CANDIDATE_A", "CANDIDATE_B"):
        raise ValueError("evidence_decisive_source_without_selection")
    if source == "UNDERSPECIFIED_SURFACE" and selected != "NONE":
        raise ValueError("evidence_soft_source_selected_object")
    if source == "MISSING_EXTERNAL_SPECIFICATION" and (selected != "NONE" or preference != "NONE"):
        raise ValueError("evidence_opaque_source_not_open")
    if source in ("CONFLICTING_SURFACE", "UNRESOLVED") and (selected != "UNCERTAIN" or preference != "UNCERTAIN"):
        raise ValueError("evidence_uncertain_source_mismatch")
    state = SOURCE_TO_STATE[source]
    if state == "DIRECTLY_DEFINED":
        basis = "LEXICAL_EXACT"
    elif state == "COMPOSITIONALLY_DETERMINED":
        basis = "COMPOSITIONAL_ENTAILMENT"
    elif state == "SOFT_AMBIGUITY":
        basis = "PRAGMATIC_DEFAULT" if preference in ("CANDIDATE_A", "CANDIDATE_B") else "NO_PREFERENCE" if preference == "NONE" else "UNCERTAIN"
    elif state == "OPAQUE_REFERENCE":
        basis = "NO_PREFERENCE"
    else:
        basis = "UNCERTAIN"
    action = "ACCEPT" if selected in ("CANDIDATE_A", "CANDIDATE_B") else "CLARIFY" if selected == "NONE" else "ABSTAIN"
    payload = {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "selection_basis": basis,
        "pragmatic_preference": preference,
        "evidence_state": state,
        "assessment_process_state": receipt["assessment_process_state"],
        "action": action,
        "rationale": receipt["rationale"],
        "confidence": receipt["confidence"],
        "evidence_refs": list(evidence_refs),
    }
    validate_selective_tuple(payload, conflict_id=conflict_id, evidence_refs=evidence_refs)
    return payload


def analyze_evidence_run(*, corpus, run):
    by_arm = {arm: {} for arm in ARMS}
    accounting = {arm: Counter() for arm in ARMS}
    for output in run["outputs"]:
        by_arm[output["arm"]][output["conflict_id"]] = output["payload"]
        accounting[output["arm"]].update(output["action_receipt"]["cost"])
    common = set(by_arm[ARMS[0]]) & set(by_arm[ARMS[1]])
    disagreements = {
        field: sum(by_arm[ARMS[0]][case][field] != by_arm[ARMS[1]][case][field] for case in common)
        for field in ("selected_object", "selection_basis", "pragmatic_preference", "evidence_state", "assessment_process_state")
    }
    tokens = {arm: accounting[arm]["input_tokens"] + accounting[arm]["output_tokens"] for arm in ARMS}
    commitment = {
        "analysis_version": EVIDENCE_CALIBRATOR_VERSION,
        "source_run_hash": run["run_hash"],
        "coverage": {arm: round(len(by_arm[arm]) / corpus["case_count"], 6) for arm in ARMS},
        "common_case_count": len(common),
        "axis_disagreement_counts": disagreements,
        "evidence_state_distributions": {arm: dict(Counter(value["evidence_state"] for value in by_arm[arm].values())) for arm in ARMS},
        "definition_source_distribution": dict(Counter(output["definition_source_receipt"]["definition_source"] for output in run["outputs"] if output["arm"] == "CONTRASTIVE_SOURCE_CALIBRATOR")),
        "accounting": {arm: dict(value) for arm, value in accounting.items()},
        "total_tokens": tokens,
        "calibrator_to_control_token_ratio": round(tokens[ARMS[1]] / tokens[ARMS[0]], 6) if tokens[ARMS[0]] else None,
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": "EVIDENCE_CALIBRATION_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL",
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _task(*, item, arm, evidence_refs, adapter):
    if arm == "FREE_LABEL_CONTROL":
        objective = (
            "Assess the semantic tuple and evidence state directly. Keep semantic selection separate from pragmatic preference. "
            "A justified open or opaque conclusion can have a COMPLETE assessment process."
        )
        schema = selective_tuple_schema(item["conflict_id"], evidence_refs)
    else:
        objective = (
            "Identify the operative source that determines or fails to determine the requested object. "
            "EXPLICIT_REQUEST_DEFINITION requires an explicit defining clause in the request; ESTABLISHED_UNAMBIGUOUS_TERM requires "
            "a genuinely standard term with one relevant meaning; COMPOSED_CONSTRAINTS requires combining multiple constraints; "
            "MISSING_EXTERNAL_SPECIFICATION requires a named absent codebook, policy, calendar, or state model; "
            "UNDERSPECIFIED_SURFACE means the displayed request leaves multiple candidates open; CONFLICTING_SURFACE means displayed "
            "constraints clash; UNRESOLVED is residual uncertainty. Candidate option text is never itself definition evidence. "
            "Quote the request phrase supporting the source. Keep pragmatic preference separate from semantic selection."
        )
        schema = source_schema(item["conflict_id"], evidence_refs)
    return ProviderCognitiveTask(
        task_id=f"{EVIDENCE_CALIBRATOR_VERSION}-{arm.lower()}-{item['conflict_id']}",
        task_kind=EVIDENCE_TASK_KIND,
        objective=objective,
        inputs={"arm": arm, "public_object": item, "external_reference": "WITHHELD"},
        allowed_evidence=list(evidence_refs),
        expected_schema=schema,
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="retain_failed_arm_without_cross_arm_substitution",
    )


def _usage_cost(usage):
    return ActionCost(
        provider_calls=max(1, int(usage.get("provider_calls") or 1)),
        input_tokens=int(usage.get("prompt_tokens") or usage.get("input_tokens") or 0),
        output_tokens=int(usage.get("completion_tokens") or usage.get("output_tokens") or 0),
        latency_ms=int(usage.get("latency_ms") or 0),
    )


def _failure(arm, conflict_id, envelope, invocation):
    return {"arm": arm, "conflict_id": conflict_id, "status": envelope.status, "validation_errors": list(envelope.validation_errors), "invocation_receipt": invocation}
