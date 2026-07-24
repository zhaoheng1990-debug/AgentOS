"""Candidate-blind adaptive source-to-entailment funnel v0.24."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_gate_policies import (
    REPAIRED_GATE,
    apply_gate_policy,
)
from .cognitive_action_candidate_blind_funnel_holdout import (
    evidence_text,
    validate_candidate_blind_funnel_holdout,
)
from .provider_telemetry import hash_payload


FUNNEL_VERSION = "cognitive_action_candidate_blind_funnel_smoke_v0_24"
FUNNEL_TASK_KIND = "COGNITIVE_ACTION_CANDIDATE_BLIND_FUNNEL_SMOKE"
SOURCE_CLOSURE_HASH = (
    "47ea85f30bdc2a6f4f70b9dcc925d8a1050d3c01806352b91c73d7035088c347"
)
SOURCE_STATUSES = ("AVAILABLE", "MISSING", "UNSPECIFIED", "CONFLICTED")
STATUS_RELATIONS = (
    "DEFINITION_PRESENT",
    "NAMED_SOURCE_ABSENT",
    "NO_DEFINITION_GIVEN",
    "CONFLICTING_DEFINITIONS",
)
STATUS_RELATION_MAP = {
    "AVAILABLE": "DEFINITION_PRESENT",
    "MISSING": "NAMED_SOURCE_ABSENT",
    "UNSPECIFIED": "NO_DEFINITION_GIVEN",
    "CONFLICTED": "CONFLICTING_DEFINITIONS",
}
ENTAILMENT_RELATIONS = ("DEFINES", "JOINTLY_ENTAILS")
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN")


def build_candidate_blind_funnel_preregistration(*, source_closure):
    if (
        source_closure.get("artifact_hash") != SOURCE_CLOSURE_HASH
        or source_closure.get("candidate_state")
        != "RELATIONAL_WITNESS_STRUCTURAL_VALIDATION_FAILED_NO_EXTERNAL_PANEL"
        or source_closure.get("external_panel_generated") is not False
        or source_closure.get("promotion_allowed") is not False
    ):
        raise ValueError("candidate_blind_funnel_source_closure_invalid")
    commitment = {
        "preregistration_version": FUNNEL_VERSION,
        "source_closure_hash": SOURCE_CLOSURE_HASH,
        "frozen_hypothesis": (
            "candidate-blind source availability followed by adaptive "
            "candidate entailment removes candidate leakage and preserves "
            "source-status distinctions"
        ),
        "stage_contract": {
            "source_status_stage_receives_candidate_text": False,
            "entailment_stage_runs_only_for_available_sources": True,
            "entailment_stage_may_not_introduce_new_evidence_spans": True,
            "runtime_synthesizes_nonavailable_branches": True,
        },
        "success_gate": {
            "required_source_candidate_blind_rate": 1.0,
            "required_source_receipt_validation_rate": 1.0,
            "minimum_source_status_construction_match_rate": 0.875,
            "required_adaptive_route_match": True,
            "required_entailment_receipt_validation_rate": 1.0,
            "required_output_coverage": 1.0,
            "maximum_provider_calls": 12,
        },
        "claim_ceiling": (
            "SYNTHETIC_STRUCTURAL_SMOKE_ONLY_NO_EXTERNAL_SEMANTIC_VALIDITY"
        ),
        "v0_23_receipts_used_as_failure_mechanism_only": True,
        "fresh_v0_24_receipts_available_before_run": False,
        "full_holdout_authorized_on_pass_only": True,
        "external_panel_allowed": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def source_status_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "requested_object_quote",
            "source_status_quote",
            "definition_source_status",
            "status_relation",
            "support_spans",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "requested_object_quote": {
                "type": "string", "minLength": 1, "maxLength": 280,
            },
            "source_status_quote": {
                "type": "string", "minLength": 1, "maxLength": 360,
            },
            "definition_source_status": {
                "type": "string", "enum": list(SOURCE_STATUSES),
            },
            "status_relation": {
                "type": "string", "enum": list(STATUS_RELATIONS),
            },
            "support_spans": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "string", "minLength": 1, "maxLength": 360,
                },
            },
            "rationale": {
                "type": "string", "minLength": 1, "maxLength": 800,
            },
            "confidence": {
                "type": "number", "minimum": 0, "maximum": 1,
            },
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {
                    "type": "string", "enum": list(evidence_refs),
                },
            },
        },
    }


def entailment_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "candidate_entailment",
            "entailment_relation",
            "contextual_default",
            "derivation_steps",
            "candidate_option_text_used_as_evidence",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "candidate_entailment": {
                "type": "string",
                "enum": ["CANDIDATE_A", "CANDIDATE_B"],
            },
            "entailment_relation": {
                "type": "string", "enum": list(ENTAILMENT_RELATIONS),
            },
            "contextual_default": {
                "type": "string", "enum": list(SELECTIONS),
            },
            "derivation_steps": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "string", "minLength": 1, "maxLength": 420,
                },
            },
            "candidate_option_text_used_as_evidence": {
                "type": "boolean", "enum": [False],
            },
            "rationale": {
                "type": "string", "minLength": 1, "maxLength": 900,
            },
            "confidence": {
                "type": "number", "minimum": 0, "maximum": 1,
            },
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {
                    "type": "string", "enum": list(evidence_refs),
                },
            },
        },
    }


def validate_source_status_receipt(receipt, *, item, evidence_refs):
    required = set(
        source_status_schema(
            item["conflict_id"],
            evidence_refs,
        )["required"]
    )
    text = evidence_text(item)
    spans = receipt.get("support_spans") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != item["conflict_id"]
        or receipt.get("definition_source_status") not in SOURCE_STATUSES
        or receipt.get("status_relation") not in STATUS_RELATIONS
        or STATUS_RELATION_MAP.get(receipt.get("definition_source_status"))
        != receipt.get("status_relation")
        or receipt.get("requested_object_quote") not in text
        or receipt.get("source_status_quote") not in text
        or not isinstance(spans, list)
        or not 1 <= len(spans) <= 3
        or any(
            not isinstance(span, str) or not span.strip() or span not in text
            for span in spans
        )
        or not str(receipt.get("rationale", "")).strip()
        or not _confidence(receipt.get("confidence"))
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("candidate_blind_source_receipt_invalid")


def validate_entailment_receipt(receipt, *, conflict_id, evidence_refs):
    required = set(
        entailment_schema(conflict_id, evidence_refs)["required"]
    )
    steps = receipt.get("derivation_steps") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != conflict_id
        or receipt.get("candidate_entailment")
        not in ("CANDIDATE_A", "CANDIDATE_B")
        or receipt.get("entailment_relation") not in ENTAILMENT_RELATIONS
        or receipt.get("contextual_default") not in SELECTIONS
        or not isinstance(steps, list)
        or len(steps) > 4
        or any(not isinstance(step, str) or not step.strip() for step in steps)
        or receipt.get("candidate_option_text_used_as_evidence") is not False
        or not str(receipt.get("rationale", "")).strip()
        or not _confidence(receipt.get("confidence"))
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("candidate_blind_entailment_receipt_invalid")


def run_candidate_blind_funnel_smoke(*, corpus, preregistration, adapter):
    validate_candidate_blind_funnel_holdout(corpus)
    if (
        preregistration.get("preregistration_version") != FUNNEL_VERSION
        or preregistration.get("artifact_hash")
        != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("candidate_blind_funnel_preregistration_invalid")
    refs = tuple(corpus["evidence_refs"])
    calls, failures, source_receipts, outputs = [], [], {}, {}
    for item in corpus["public_surface"]["items"]:
        task = _source_status_task(item, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        calls.append(_call("SOURCE_STATUS", item["conflict_id"], task, envelope))
        if envelope.status != "COMPLETED":
            failures.append(_failure(
                "SOURCE_STATUS", item["conflict_id"], envelope
            ))
            continue
        receipt = envelope.normalized_result
        try:
            validate_source_status_receipt(
                receipt,
                item=item,
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "SOURCE_STATUS",
                "conflict_id": item["conflict_id"],
                "status": "SOURCE_RECEIPT_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "provider_receipt_preserved": receipt,
            })
            continue
        source_receipts[item["conflict_id"]] = receipt
        if receipt["definition_source_status"] != "AVAILABLE":
            outputs[item["conflict_id"]] = _synthesize_nonavailable(
                receipt,
                conflict_id=item["conflict_id"],
                evidence_refs=refs,
            )
            continue
        entailment_task = _entailment_task(item, receipt, refs, adapter)
        entailment_envelope = ProviderTaskRouter([adapter]).route(
            entailment_task
        )
        calls.append(_call(
            "CANDIDATE_ENTAILMENT",
            item["conflict_id"],
            entailment_task,
            entailment_envelope,
        ))
        if entailment_envelope.status != "COMPLETED":
            failures.append(_failure(
                "CANDIDATE_ENTAILMENT",
                item["conflict_id"],
                entailment_envelope,
            ))
            continue
        entailment = entailment_envelope.normalized_result
        try:
            validate_entailment_receipt(
                entailment,
                conflict_id=item["conflict_id"],
                evidence_refs=refs,
            )
            outputs[item["conflict_id"]] = _synthesize_available(
                receipt,
                entailment,
                conflict_id=item["conflict_id"],
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "CANDIDATE_ENTAILMENT",
                "conflict_id": item["conflict_id"],
                "status": "ENTAILMENT_RECEIPT_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "provider_receipt_preserved": entailment,
            })
    output_records = [
        _output(conflict_id, payload)
        for conflict_id, payload in outputs.items()
    ]
    commitment = {
        "runtime_version": FUNNEL_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_calls": calls,
        "source_status_receipts": source_receipts,
        "outputs": output_records,
        "failures": failures,
        "source_status_stage_candidate_blind": True,
        "adaptive_entailment_routing": True,
        "external_reference_available": False,
        "synthetic_structural_smoke_only": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_candidate_blind_funnel_smoke(*, corpus, run, preregistration):
    bindings = corpus["private_provenance"]["bindings"]
    source_calls = [
        call for call in run["provider_calls"]
        if call["stage"] == "SOURCE_STATUS"
    ]
    entailment_calls = [
        call for call in run["provider_calls"]
        if call["stage"] == "CANDIDATE_ENTAILMENT"
    ]
    valid_sources = run["source_status_receipts"]
    valid_entailments = {
        call["conflict_id"]
        for call in entailment_calls
        if call["status"] == "COMPLETED"
        and call["conflict_id"] in {
            output["conflict_id"] for output in run["outputs"]
        }
    }
    available = {
        conflict_id for conflict_id, receipt in valid_sources.items()
        if receipt["definition_source_status"] == "AVAILABLE"
    }
    source_match = sum(
        receipt["definition_source_status"]
        == bindings[conflict_id]["source_status"]
        for conflict_id, receipt in valid_sources.items()
    )
    candidate_blind = sum(
        call["candidate_fields_exposed"] is False
        and set(call["task_input_keys"])
        == {"stage", "evidence_text", "conflict_id"}
        for call in source_calls
    )
    source_rate = round(len(valid_sources) / corpus["case_count"], 6)
    match_rate = round(
        source_match / len(valid_sources), 6
    ) if valid_sources else None
    entailment_rate = round(
        len(valid_entailments) / len(entailment_calls), 6
    ) if entailment_calls else None
    output_coverage = round(
        len(run["outputs"]) / corpus["case_count"], 6
    )
    stage_costs = {
        stage: Counter()
        for stage in ("SOURCE_STATUS", "CANDIDATE_ENTAILMENT")
    }
    for call in run["provider_calls"]:
        usage = call["invocation_receipt"].get("token_usage") or {}
        stage_costs[call["stage"]].update({
            "provider_calls": int(usage.get("provider_calls") or 1),
            "input_tokens": int(
                usage.get("prompt_tokens") or usage.get("input_tokens") or 0
            ),
            "output_tokens": int(
                usage.get("completion_tokens")
                or usage.get("output_tokens") or 0
            ),
            "latency_ms": int(usage.get("latency_ms") or 0),
        })
    gate = preregistration["success_gate"]
    conditions = {
        "required_source_candidate_blind_rate": (
            round(candidate_blind / len(source_calls), 6)
            >= gate["required_source_candidate_blind_rate"]
        ),
        "required_source_receipt_validation_rate": (
            source_rate >= gate["required_source_receipt_validation_rate"]
        ),
        "minimum_source_status_construction_match_rate": (
            match_rate is not None
            and match_rate
            >= gate["minimum_source_status_construction_match_rate"]
        ),
        "required_adaptive_route_match": (
            set(call["conflict_id"] for call in entailment_calls) == available
            and gate["required_adaptive_route_match"] is True
        ),
        "required_entailment_receipt_validation_rate": (
            entailment_rate is not None
            and entailment_rate
            >= gate["required_entailment_receipt_validation_rate"]
        ),
        "required_output_coverage": (
            output_coverage >= gate["required_output_coverage"]
        ),
        "maximum_provider_calls": (
            len(run["provider_calls"]) <= gate["maximum_provider_calls"]
        ),
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": FUNNEL_VERSION,
        "source_run_hash": run["run_hash"],
        "source_candidate_blind_rate": round(
            candidate_blind / len(source_calls), 6
        ),
        "source_receipt_validation_rate": source_rate,
        "source_status_construction_match_rate": match_rate,
        "source_status_distribution": dict(Counter(
            receipt["definition_source_status"]
            for receipt in valid_sources.values()
        )),
        "expected_source_status_distribution": (
            corpus["source_status_counts"]
        ),
        "available_route_count": len(available),
        "entailment_call_count": len(entailment_calls),
        "entailment_receipt_validation_rate": entailment_rate,
        "output_coverage": output_coverage,
        "provider_call_count": len(run["provider_calls"]),
        "failure_counts": dict(Counter(
            f"{failure['stage']}:{failure['status']}"
            for failure in run["failures"]
        )),
        "stage_accounting": {
            stage: dict(value) for stage, value in stage_costs.items()
        },
        "total_tokens": sum(
            value["input_tokens"] + value["output_tokens"]
            for value in stage_costs.values()
        ),
        "preregistered_gate_conditions": conditions,
        "structural_smoke_gate": "PASS" if passed else "REJECT",
        "full_fresh_holdout_authorized": passed,
        "external_panel_allowed": False,
        "claim_scope": (
            "SYNTHETIC_STRUCTURAL_SMOKE_ONLY_NO_EXTERNAL_SEMANTIC_VALIDITY"
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "candidate_state": (
            "CANDIDATE_BLIND_FUNNEL_SMOKE_PASSED_READY_FULL_FRESH_HOLDOUT"
            if passed
            else "CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _source_status_task(item, refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{FUNNEL_VERSION}-source-{item['conflict_id']}",
        task_kind=FUNNEL_TASK_KIND,
        objective=(
            "Without seeing any candidate options, bind the requested object "
            "and classify only whether its definition is AVAILABLE in the "
            "displayed evidence, depends on a named MISSING source, is "
            "UNSPECIFIED, or has CONFLICTED displayed definitions. Quote exact "
            "text for the requested object and source status. Do not infer or "
            "invent any candidate."
        ),
        inputs={
            "stage": "SOURCE_STATUS",
            "evidence_text": evidence_text(item),
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=source_status_schema(item["conflict_id"], refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _entailment_task(item, source_receipt, refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{FUNNEL_VERSION}-entailment-{item['conflict_id']}",
        task_kind=FUNNEL_TASK_KIND,
        objective=(
            "Use only the validated candidate-blind source receipt as "
            "evidence. Determine which candidate is entailed and whether the "
            "relation is direct definition or joint compositional entailment. "
            "Candidate option text is a comparison target, never evidence. "
            "Explanatory derivation steps are allowed for either relation."
        ),
        inputs={
            "stage": "CANDIDATE_ENTAILMENT",
            "validated_source_receipt": source_receipt,
            "candidate_a": item["candidate_a"],
            "candidate_b": item["candidate_b"],
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=entailment_schema(item["conflict_id"], refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _synthesize_nonavailable(receipt, *, conflict_id, evidence_refs):
    status = receipt["definition_source_status"]
    if status == "MISSING":
        source, selected, preference = (
            "MISSING_EXTERNAL_SPECIFICATION", "NONE", "NONE"
        )
    elif status == "UNSPECIFIED":
        source, selected, preference = (
            "UNDERSPECIFIED_SURFACE", "NONE", "NONE"
        )
    else:
        source, selected, preference = (
            "CONFLICTING_SURFACE", "UNCERTAIN", "UNCERTAIN"
        )
    return _apply_source(
        conflict_id=conflict_id,
        source=source,
        selected=selected,
        preference=preference,
        support_quote=receipt["source_status_quote"],
        rationale=receipt["rationale"],
        confidence=receipt["confidence"],
        evidence_refs=evidence_refs,
    )


def _synthesize_available(
    source_receipt,
    entailment_receipt,
    *,
    conflict_id,
    evidence_refs,
):
    source = (
        "EXPLICIT_REQUEST_DEFINITION"
        if entailment_receipt["entailment_relation"] == "DEFINES"
        else "COMPOSED_CONSTRAINTS"
    )
    return _apply_source(
        conflict_id=conflict_id,
        source=source,
        selected=entailment_receipt["candidate_entailment"],
        preference=entailment_receipt["contextual_default"],
        support_quote=source_receipt["source_status_quote"],
        rationale=entailment_receipt["rationale"],
        confidence=entailment_receipt["confidence"],
        evidence_refs=evidence_refs,
    )


def _apply_source(
    *,
    conflict_id,
    source,
    selected,
    preference,
    support_quote,
    rationale,
    confidence,
    evidence_refs,
):
    receipt = {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "definition_source": source,
        "pragmatic_preference": preference,
        "assessment_process_state": "COMPLETE",
        "support_quote": support_quote,
        "rationale": rationale,
        "confidence": confidence,
        "evidence_refs": list(evidence_refs),
    }
    return apply_gate_policy(
        REPAIRED_GATE,
        receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )["payload"]


def _call(stage, conflict_id, task, envelope):
    keys = sorted(task.inputs)
    commitment = {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": envelope.status,
        "normalized_result": (
            envelope.normalized_result
            if envelope.status == "COMPLETED"
            else None
        ),
        "invocation_receipt": envelope.invocation_receipt.as_dict(),
        "task_contract_hash": task.contract_hash(),
        "task_input_keys": keys,
        "candidate_fields_exposed": any(
            key in {"candidate_a", "candidate_b"} for key in keys
        ),
        "reference_available": False,
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _failure(stage, conflict_id, envelope):
    return {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": envelope.status,
        "validation_errors": list(envelope.validation_errors),
    }


def _output(conflict_id, payload):
    commitment = {
        "conflict_id": conflict_id,
        "payload": payload,
        "reference_available": False,
        "synthetic_structural_smoke_only": True,
    }
    return {**commitment, "output_hash": hash_payload(commitment)}


def _confidence(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
    )
