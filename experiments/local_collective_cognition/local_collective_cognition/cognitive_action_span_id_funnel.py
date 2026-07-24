"""Candidate-blind immutable span-ID source-to-entailment funnel v0.25."""

from __future__ import annotations

import re
from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_gate_policies import REPAIRED_GATE, apply_gate_policy
from .cognitive_action_span_id_funnel_holdout import (
    evidence_text,
    validate_span_id_funnel_holdout,
)
from .provider_telemetry import hash_payload


FUNNEL_VERSION = "cognitive_action_span_id_funnel_smoke_v0_25"
FUNNEL_TASK_KIND = "COGNITIVE_ACTION_SPAN_ID_FUNNEL_SMOKE"
SOURCE_CLOSURE_HASH = (
    "aba62feb3c5802a40802e2add535af0e421577612c0f270023c08d90a0c7d447"
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


def build_span_id_funnel_preregistration(*, source_closure):
    if (
        source_closure.get("artifact_hash") != SOURCE_CLOSURE_HASH
        or source_closure.get("candidate_state")
        != "CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP"
        or source_closure.get("external_panel_generated") is not False
        or source_closure.get("promotion_allowed") is not False
    ):
        raise ValueError("span_id_funnel_source_closure_invalid")
    commitment = {
        "preregistration_version": FUNNEL_VERSION,
        "source_closure_hash": SOURCE_CLOSURE_HASH,
        "frozen_hypothesis": (
            "Runtime-owned immutable span identifiers remove quote-copy "
            "failures while preserving candidate-blind source judgment"
        ),
        "stage_contract": {
            "runtime_owns_segmentation_and_text_hashes": True,
            "provider_may_select_span_ids_but_not_copy_quotes": True,
            "source_status_stage_receives_candidate_text": False,
            "entailment_stage_runs_only_for_available_sources": True,
            "entailment_stage_may_not_introduce_new_span_ids": True,
            "conflicted_requires_two_source_status_span_ids": True,
            "runtime_synthesizes_nonavailable_branches": True,
        },
        "success_gate": {
            "required_span_pack_validation_rate": 1.0,
            "required_source_candidate_blind_rate": 1.0,
            "required_source_receipt_validation_rate": 1.0,
            "minimum_source_status_construction_match_rate": 0.875,
            "maximum_false_available_promotions": 0,
            "required_adaptive_route_match": True,
            "required_entailment_receipt_validation_rate": 1.0,
            "required_no_new_span_id_rate": 1.0,
            "required_output_coverage": 1.0,
            "maximum_provider_calls": 12,
            "maximum_total_tokens": 8500,
        },
        "claim_ceiling": "SYNTHETIC_STRUCTURAL_SMOKE_ONLY_NO_SEMANTIC_VALIDITY",
        "fresh_v0_25_receipts_available_before_run": False,
        "full_holdout_authorized_on_pass_only": True,
        "external_panel_allowed": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def build_evidence_span_pack(item):
    text = evidence_text(item)
    pieces = [
        piece.strip()
        for piece in re.split(
            r"(?<=[.!?;])\s+|\s+(?=(?:but|while)\b)",
            text,
            flags=re.IGNORECASE,
        )
        if piece.strip()
    ]
    spans = []
    for index, piece in enumerate(pieces, 1):
        spans.append({
            "span_id": "S{:02d}-{}".format(
                index,
                hash_payload([
                    FUNNEL_VERSION,
                    item["conflict_id"],
                    index,
                    piece,
                ])[:10],
            ),
            "text": piece,
            "text_hash": hash_payload(piece),
        })
    commitment = {
        "span_pack_version": FUNNEL_VERSION,
        "conflict_id": item["conflict_id"],
        "source_text_hash": hash_payload(text),
        "spans": spans,
    }
    return {**commitment, "span_pack_hash": hash_payload(commitment)}


def validate_evidence_span_pack(pack, *, item):
    if pack != build_evidence_span_pack(item):
        raise ValueError("span_id_funnel_span_pack_invalid")


def source_status_schema(conflict_id, span_ids, evidence_refs):
    id_field = {
        "type": "array",
        "minItems": 1,
        "maxItems": len(span_ids),
        "uniqueItems": True,
        "items": {"type": "string", "enum": list(span_ids)},
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "requested_object_span_ids",
            "source_status_span_ids",
            "definition_source_status",
            "status_relation",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "requested_object_span_ids": id_field,
            "source_status_span_ids": id_field,
            "definition_source_status": {
                "type": "string", "enum": list(SOURCE_STATUSES),
            },
            "status_relation": {
                "type": "string", "enum": list(STATUS_RELATIONS),
            },
            "rationale": {"type": "string", "minLength": 1, "maxLength": 800},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def entailment_schema(conflict_id, span_ids, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "candidate_entailment",
            "entailment_relation",
            "evidence_span_ids",
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
                "type": "string", "enum": ["CANDIDATE_A", "CANDIDATE_B"],
            },
            "entailment_relation": {
                "type": "string", "enum": list(ENTAILMENT_RELATIONS),
            },
            "evidence_span_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": len(span_ids),
                "uniqueItems": True,
                "items": {"type": "string", "enum": list(span_ids)},
            },
            "contextual_default": {
                "type": "string", "enum": list(SELECTIONS),
            },
            "derivation_steps": {
                "type": "array",
                "maxItems": 4,
                "items": {"type": "string", "minLength": 1, "maxLength": 420},
            },
            "candidate_option_text_used_as_evidence": {
                "type": "boolean", "enum": [False],
            },
            "rationale": {"type": "string", "minLength": 1, "maxLength": 900},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "evidence_refs": {
                "type": "array",
                "minItems": len(evidence_refs),
                "maxItems": len(evidence_refs),
                "items": {"type": "string", "enum": list(evidence_refs)},
            },
        },
    }


def validate_source_status_receipt(receipt, *, item, span_pack, evidence_refs):
    span_ids = tuple(span["span_id"] for span in span_pack["spans"])
    required = set(source_status_schema(
        item["conflict_id"], span_ids, evidence_refs
    )["required"])
    requested = (
        receipt.get("requested_object_span_ids")
        if isinstance(receipt, dict) else None
    )
    source = (
        receipt.get("source_status_span_ids")
        if isinstance(receipt, dict) else None
    )
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != item["conflict_id"]
        or not _valid_ids(requested, span_ids)
        or not _valid_ids(source, span_ids)
        or receipt.get("definition_source_status") not in SOURCE_STATUSES
        or STATUS_RELATION_MAP.get(receipt.get("definition_source_status"))
        != receipt.get("status_relation")
        or (
            receipt.get("definition_source_status") == "CONFLICTED"
            and len(source) < 2
        )
        or not str(receipt.get("rationale", "")).strip()
        or not _confidence(receipt.get("confidence"))
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("span_id_funnel_source_receipt_invalid")


def validate_entailment_receipt(
    receipt,
    *,
    conflict_id,
    admitted_span_ids,
    evidence_refs,
):
    required = set(entailment_schema(
        conflict_id, admitted_span_ids, evidence_refs
    )["required"])
    evidence_ids = (
        receipt.get("evidence_span_ids") if isinstance(receipt, dict) else None
    )
    steps = receipt.get("derivation_steps") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != conflict_id
        or receipt.get("candidate_entailment")
        not in ("CANDIDATE_A", "CANDIDATE_B")
        or receipt.get("entailment_relation") not in ENTAILMENT_RELATIONS
        or not _valid_ids(evidence_ids, admitted_span_ids)
        or receipt.get("contextual_default") not in SELECTIONS
        or not isinstance(steps, list)
        or len(steps) > 4
        or any(not isinstance(step, str) or not step.strip() for step in steps)
        or receipt.get("candidate_option_text_used_as_evidence") is not False
        or not str(receipt.get("rationale", "")).strip()
        or not _confidence(receipt.get("confidence"))
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("span_id_funnel_entailment_receipt_invalid")


def run_span_id_funnel_smoke(*, corpus, preregistration, adapter):
    validate_span_id_funnel_holdout(corpus)
    if (
        preregistration.get("preregistration_version") != FUNNEL_VERSION
        or preregistration.get("artifact_hash") != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("span_id_funnel_preregistration_invalid")
    refs = tuple(corpus["evidence_refs"])
    calls, failures, source_receipts, entailment_receipts, outputs = (
        [], [], {}, {}, {}
    )
    span_packs = {}
    for item in corpus["public_surface"]["items"]:
        conflict_id = item["conflict_id"]
        pack = build_evidence_span_pack(item)
        validate_evidence_span_pack(pack, item=item)
        span_packs[conflict_id] = pack
        task = _source_status_task(item, pack, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        calls.append(_call("SOURCE_STATUS", conflict_id, task, envelope))
        if envelope.status != "COMPLETED":
            failures.append(_failure("SOURCE_STATUS", conflict_id, envelope))
            continue
        receipt = envelope.normalized_result
        try:
            validate_source_status_receipt(
                receipt,
                item=item,
                span_pack=pack,
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append(_validation_failure(
                "SOURCE_STATUS", conflict_id, receipt, exc
            ))
            continue
        source_receipts[conflict_id] = receipt
        if receipt["definition_source_status"] != "AVAILABLE":
            outputs[conflict_id] = _synthesize_nonavailable(
                receipt,
                span_pack=pack,
                conflict_id=conflict_id,
                evidence_refs=refs,
            )
            continue
        admitted_ids = _admitted_ids(receipt)
        entailment_task = _entailment_task(
            item, receipt, pack, admitted_ids, refs, adapter
        )
        entailment_envelope = ProviderTaskRouter([adapter]).route(
            entailment_task
        )
        calls.append(_call(
            "CANDIDATE_ENTAILMENT",
            conflict_id,
            entailment_task,
            entailment_envelope,
        ))
        if entailment_envelope.status != "COMPLETED":
            failures.append(_failure(
                "CANDIDATE_ENTAILMENT", conflict_id, entailment_envelope
            ))
            continue
        entailment = entailment_envelope.normalized_result
        try:
            validate_entailment_receipt(
                entailment,
                conflict_id=conflict_id,
                admitted_span_ids=admitted_ids,
                evidence_refs=refs,
            )
            entailment_receipts[conflict_id] = entailment
            outputs[conflict_id] = _synthesize_available(
                receipt,
                entailment,
                span_pack=pack,
                conflict_id=conflict_id,
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append(_validation_failure(
                "CANDIDATE_ENTAILMENT", conflict_id, entailment, exc
            ))
    output_records = [
        _output(conflict_id, payload)
        for conflict_id, payload in outputs.items()
    ]
    commitment = {
        "runtime_version": FUNNEL_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "evidence_span_packs": span_packs,
        "provider_calls": calls,
        "source_status_receipts": source_receipts,
        "entailment_receipts": entailment_receipts,
        "outputs": output_records,
        "failures": failures,
        "source_status_stage_candidate_blind": True,
        "runtime_owned_immutable_spans": True,
        "adaptive_entailment_routing": True,
        "external_reference_available": False,
        "synthetic_structural_smoke_only": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_span_id_funnel_smoke(*, corpus, run, preregistration):
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
    valid_entailments = run["entailment_receipts"]
    available = {
        conflict_id for conflict_id, receipt in valid_sources.items()
        if receipt["definition_source_status"] == "AVAILABLE"
    }
    source_match = sum(
        receipt["definition_source_status"]
        == bindings[conflict_id]["source_status"]
        for conflict_id, receipt in valid_sources.items()
    )
    false_available = sum(
        receipt["definition_source_status"] == "AVAILABLE"
        and bindings[conflict_id]["source_status"] != "AVAILABLE"
        for conflict_id, receipt in valid_sources.items()
    )
    candidate_blind = sum(
        call["candidate_fields_exposed"] is False
        and set(call["task_input_keys"])
        == {"stage", "evidence_span_pack", "conflict_id"}
        for call in source_calls
    )
    pack_valid = 0
    items = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    for conflict_id, pack in run["evidence_span_packs"].items():
        try:
            validate_evidence_span_pack(pack, item=items[conflict_id])
            pack_valid += 1
        except ValueError:
            pass
    source_rate = round(len(valid_sources) / corpus["case_count"], 6)
    match_rate = (
        round(source_match / len(valid_sources), 6)
        if valid_sources else None
    )
    entailment_rate = (
        round(len(valid_entailments) / len(entailment_calls), 6)
        if entailment_calls else None
    )
    no_new_rate = (
        round(sum(
            set(receipt["evidence_span_ids"]).issubset(
                set(_admitted_ids(valid_sources[conflict_id]))
            )
            for conflict_id, receipt in valid_entailments.items()
        ) / len(valid_entailments), 6)
        if valid_entailments else None
    )
    output_coverage = round(len(run["outputs"]) / corpus["case_count"], 6)
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
    total_tokens = sum(
        value["input_tokens"] + value["output_tokens"]
        for value in stage_costs.values()
    )
    gate = preregistration["success_gate"]
    conditions = {
        "required_span_pack_validation_rate": (
            round(pack_valid / corpus["case_count"], 6)
            >= gate["required_span_pack_validation_rate"]
        ),
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
        "maximum_false_available_promotions": (
            false_available <= gate["maximum_false_available_promotions"]
        ),
        "required_adaptive_route_match": (
            {call["conflict_id"] for call in entailment_calls} == available
            and gate["required_adaptive_route_match"] is True
        ),
        "required_entailment_receipt_validation_rate": (
            entailment_rate is not None
            and entailment_rate
            >= gate["required_entailment_receipt_validation_rate"]
        ),
        "required_no_new_span_id_rate": (
            no_new_rate is not None
            and no_new_rate >= gate["required_no_new_span_id_rate"]
        ),
        "required_output_coverage": (
            output_coverage >= gate["required_output_coverage"]
        ),
        "maximum_provider_calls": (
            len(run["provider_calls"]) <= gate["maximum_provider_calls"]
        ),
        "maximum_total_tokens": total_tokens <= gate["maximum_total_tokens"],
    }
    passed = all(conditions.values())
    commitment = {
        "analysis_version": FUNNEL_VERSION,
        "source_run_hash": run["run_hash"],
        "span_pack_validation_rate": round(
            pack_valid / corpus["case_count"], 6
        ),
        "source_candidate_blind_rate": round(
            candidate_blind / len(source_calls), 6
        ),
        "source_receipt_validation_rate": source_rate,
        "source_status_construction_match_rate": match_rate,
        "false_available_promotion_count": false_available,
        "source_status_distribution": dict(Counter(
            receipt["definition_source_status"]
            for receipt in valid_sources.values()
        )),
        "expected_source_status_distribution": corpus["source_status_counts"],
        "available_route_count": len(available),
        "entailment_call_count": len(entailment_calls),
        "entailment_receipt_validation_rate": entailment_rate,
        "no_new_span_id_rate": no_new_rate,
        "output_coverage": output_coverage,
        "provider_call_count": len(run["provider_calls"]),
        "failure_counts": dict(Counter(
            f"{failure['stage']}:{failure['status']}"
            for failure in run["failures"]
        )),
        "stage_accounting": {
            stage: dict(value) for stage, value in stage_costs.items()
        },
        "total_tokens": total_tokens,
        "preregistered_gate_conditions": conditions,
        "structural_smoke_gate": "PASS" if passed else "REJECT",
        "full_fresh_holdout_authorized": passed,
        "external_panel_allowed": False,
        "claim_scope": "SYNTHETIC_STRUCTURAL_SMOKE_ONLY_NO_SEMANTIC_VALIDITY",
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
        "candidate_state": (
            "SPAN_ID_FUNNEL_SMOKE_PASSED_READY_FULL_FRESH_HOLDOUT"
            if passed else "SPAN_ID_FUNNEL_SMOKE_REJECTED_STOP"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _source_status_task(item, span_pack, refs, adapter):
    span_ids = tuple(span["span_id"] for span in span_pack["spans"])
    return ProviderCognitiveTask(
        task_id=f"{FUNNEL_VERSION}-source-{item['conflict_id']}",
        task_kind=FUNNEL_TASK_KIND,
        objective=(
            "Without seeing candidate options, identify the requested object "
            "and classify its definition source as AVAILABLE, MISSING, "
            "UNSPECIFIED, or CONFLICTED. Select only immutable span_id values "
            "from evidence_span_pack. Never reproduce, paraphrase, or invent "
            "evidence text. CONFLICTED requires at least two status span IDs."
        ),
        inputs={
            "stage": "SOURCE_STATUS",
            "evidence_span_pack": span_pack,
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=source_status_schema(
            item["conflict_id"], span_ids, refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _entailment_task(item, source_receipt, span_pack, admitted_ids, refs, adapter):
    spans = {
        span["span_id"]: span for span in span_pack["spans"]
    }
    return ProviderCognitiveTask(
        task_id=f"{FUNNEL_VERSION}-entailment-{item['conflict_id']}",
        task_kind=FUNNEL_TASK_KIND,
        objective=(
            "Use only selected_evidence_spans admitted by the validated "
            "candidate-blind source receipt. Decide which candidate is "
            "entailed and whether the relation is DEFINES or JOINTLY_ENTAILS. "
            "Return only admitted span IDs; candidate text is never evidence."
        ),
        inputs={
            "stage": "CANDIDATE_ENTAILMENT",
            "validated_source_receipt": source_receipt,
            "selected_evidence_spans": [spans[value] for value in admitted_ids],
            "candidate_a": item["candidate_a"],
            "candidate_b": item["candidate_b"],
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=entailment_schema(
            item["conflict_id"], admitted_ids, refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _synthesize_nonavailable(
    receipt, *, span_pack, conflict_id, evidence_refs
):
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
        support_quote=_resolve_text(
            span_pack, receipt["source_status_span_ids"]
        ),
        rationale=receipt["rationale"],
        confidence=receipt["confidence"],
        evidence_refs=evidence_refs,
    )


def _synthesize_available(
    source_receipt,
    entailment_receipt,
    *,
    span_pack,
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
        support_quote=_resolve_text(
            span_pack, entailment_receipt["evidence_span_ids"]
        ),
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


def _resolve_text(span_pack, span_ids):
    by_id = {span["span_id"]: span["text"] for span in span_pack["spans"]}
    return " ".join(by_id[value] for value in span_ids)


def _admitted_ids(receipt):
    return tuple(dict.fromkeys([
        *receipt["requested_object_span_ids"],
        *receipt["source_status_span_ids"],
    ]))


def _valid_ids(values, allowed):
    return (
        isinstance(values, list)
        and bool(values)
        and len(values) == len(set(values))
        and set(values).issubset(set(allowed))
    )


def _call(stage, conflict_id, task, envelope):
    keys = sorted(task.inputs)
    commitment = {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": envelope.status,
        "normalized_result": (
            envelope.normalized_result
            if envelope.status == "COMPLETED" else None
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


def _validation_failure(stage, conflict_id, receipt, exc):
    return {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": f"{stage}_RECEIPT_VALIDATION_FAILED",
        "validation_errors": [str(exc)],
        "provider_receipt_preserved": receipt,
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
