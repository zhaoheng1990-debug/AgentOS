"""Evidence-first selective challenge runtime v0.22."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_calibrator import source_schema
from .cognitive_action_evidence_gate_policies import (
    REPAIRED_GATE,
    apply_gate_policy,
)
from .cognitive_action_evidence_first_holdout import (
    evidence_text,
    validate_evidence_first_holdout,
)
from .provider_telemetry import hash_payload


EVIDENCE_FIRST_VERSION = "cognitive_action_evidence_first_selective_v0_22"
EVIDENCE_FIRST_TASK_KIND = "COGNITIVE_ACTION_EVIDENCE_FIRST_SELECTIVE"
SOURCE_EVALUATION_HASH = (
    "2564473a3da75bfa15e4490b04be75f5502b187829796d18940ba0d76cc67505"
)
SOURCE_REFERENCE_HASH = (
    "9be0c97920cd292852b74c907406f45f523151de86857d04aaa790128f39357a"
)
BASELINE_CELL = "BASELINE_LEGACY_SOURCE_REPAIRED_GATE"
SELECTIVE_CELL = "EVIDENCE_FIRST_SELECTIVE_CHALLENGE"
CELLS = (BASELINE_CELL, SELECTIVE_CELL)
DECISIVE_CAP = 4
OPEN_CAP = 2
WITNESS_MODES = (
    "POSITIVE_DEFINITION",
    "COMPOSITIONAL_DERIVATION",
    "EVIDENCE_ABSENCE",
    "CONFLICT",
    "UNRESOLVED",
)


def build_evidence_first_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state")
        != "SOURCE_ONTOLOGY_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("evidence_first_source_evaluation_invalid")
    commitment = {
        "preregistration_version": EVIDENCE_FIRST_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": (
            "a mechanically verified evidence witness followed by a separate "
            "judge can correct selected high-risk receipts without repeating "
            "unconditional source-axis rationalization"
        ),
        "cells": list(CELLS),
        "challenge_plan": {
            "decisive_source_cap": DECISIVE_CAP,
            "open_source_cap": OPEN_CAP,
            "ranking": "ascending_confidence_then_hash",
            "maximum_challenged_objects": DECISIVE_CAP + OPEN_CAP,
            "reference_available": False,
        },
        "witness_invariants": {
            "witness_precedes_judgment": True,
            "support_spans_must_be_exact_evidence_text_substrings": True,
            "candidate_option_text_cannot_be_support_span": True,
            "witness_has_no_evidence_state_or_selection_fields": True,
            "judge_may_use_only_verified_witness": True,
            "failed_challenge_preserves_baseline": True,
        },
        "success_gate": {
            "minimum_net_correct_cell_gain": 3,
            "minimum_evidence_state_correct_gain": 2,
            "minimum_challenged_full_tuple_gain": 2,
            "maximum_selected_object_correct_loss": 0,
            "corrections_must_exceed_harms": True,
            "required_output_coverage": 1.0,
            "maximum_selective_to_baseline_token_ratio": 2.0,
            "required_witness_validation_rate": 1.0,
        },
        "v0_21_labels_used_as_failure_mechanism_only": True,
        "fresh_v0_22_labels_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def witness_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "witness_mode",
            "support_spans",
            "derivation_steps",
            "candidate_option_text_used_as_evidence",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "witness_mode": {
                "type": "string",
                "enum": list(WITNESS_MODES),
            },
            "support_spans": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 300,
                },
            },
            "derivation_steps": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 400,
                },
            },
            "candidate_option_text_used_as_evidence": {
                "type": "boolean",
                "enum": [False],
            },
            "rationale": {
                "type": "string",
                "minLength": 1,
                "maxLength": 800,
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


def validate_witness(receipt, *, item, evidence_refs):
    required = set(
        witness_schema(item["conflict_id"], evidence_refs)["required"]
    )
    text = evidence_text(item)
    spans = receipt.get("support_spans") if isinstance(receipt, dict) else None
    steps = receipt.get("derivation_steps") if isinstance(receipt, dict) else None
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != item["conflict_id"]
        or receipt.get("witness_mode") not in WITNESS_MODES
        or not isinstance(spans, list)
        or not 1 <= len(spans) <= 3
        or any(
            not isinstance(span, str)
            or not span.strip()
            or span not in text
            or span in (item["candidate_a"], item["candidate_b"])
            for span in spans
        )
        or not isinstance(steps, list)
        or len(steps) > 4
        or any(
            not isinstance(step, str) or not step.strip() for step in steps
        )
        or receipt.get("candidate_option_text_used_as_evidence") is not False
        or not isinstance(receipt.get("rationale"), str)
        or not receipt["rationale"].strip()
        or not isinstance(receipt.get("confidence"), (int, float))
        or isinstance(receipt.get("confidence"), bool)
        or not 0 <= receipt["confidence"] <= 1
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("evidence_first_witness_invalid")


def run_evidence_first_selective(*, corpus, preregistration, adapter):
    validate_evidence_first_holdout(corpus)
    if (
        preregistration.get("preregistration_version")
        != EVIDENCE_FIRST_VERSION
        or preregistration.get("artifact_hash")
        != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("evidence_first_preregistration_invalid")
    refs = tuple(corpus["evidence_refs"])
    public = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    calls, failures, baseline_outputs, source_receipts = [], [], {}, {}
    for item in corpus["public_surface"]["items"]:
        task = _baseline_task(item, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = _call("BASELINE_SOURCE", item["conflict_id"], task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(_failure("BASELINE_SOURCE", item, envelope))
            continue
        try:
            gated = apply_gate_policy(
                REPAIRED_GATE,
                envelope.normalized_result,
                conflict_id=item["conflict_id"],
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "BASELINE_GATE",
                "conflict_id": item["conflict_id"],
                "status": "SEMANTIC_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
            })
            continue
        source_receipts[item["conflict_id"]] = envelope.normalized_result
        baseline_outputs[item["conflict_id"]] = gated["payload"]

    plan = _challenge_plan(source_receipts)
    selective_outputs = dict(baseline_outputs)
    challenge_records = []
    for conflict_id in plan["admitted_conflict_ids"]:
        item = public[conflict_id]
        witness_task = _witness_task(item, refs, adapter)
        witness_envelope = ProviderTaskRouter([adapter]).route(witness_task)
        calls.append(_call(
            "EVIDENCE_WITNESS",
            conflict_id,
            witness_task,
            witness_envelope,
        ))
        if witness_envelope.status != "COMPLETED":
            failures.append(_failure(
                "EVIDENCE_WITNESS",
                item,
                witness_envelope,
            ))
            challenge_records.append(_challenge_record(
                conflict_id, "WITNESS_FAILED", None, False
            ))
            continue
        witness = witness_envelope.normalized_result
        try:
            validate_witness(witness, item=item, evidence_refs=refs)
        except ValueError as exc:
            failures.append({
                "stage": "EVIDENCE_WITNESS",
                "conflict_id": conflict_id,
                "status": "MECHANICAL_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "provider_receipt_preserved": witness,
            })
            challenge_records.append(_challenge_record(
                conflict_id, "WITNESS_INVALID", witness, False
            ))
            continue
        judge_task = _judge_task(item, witness, refs, adapter)
        judge_envelope = ProviderTaskRouter([adapter]).route(judge_task)
        calls.append(_call(
            "WITNESS_BOUND_JUDGE",
            conflict_id,
            judge_task,
            judge_envelope,
        ))
        if judge_envelope.status != "COMPLETED":
            failures.append(_failure(
                "WITNESS_BOUND_JUDGE",
                item,
                judge_envelope,
            ))
            challenge_records.append(_challenge_record(
                conflict_id, "JUDGE_FAILED", witness, True
            ))
            continue
        try:
            gated = apply_gate_policy(
                REPAIRED_GATE,
                judge_envelope.normalized_result,
                conflict_id=conflict_id,
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "WITNESS_BOUND_JUDGE",
                "conflict_id": conflict_id,
                "status": "SEMANTIC_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "provider_receipt_preserved": (
                    judge_envelope.normalized_result
                ),
            })
            challenge_records.append(_challenge_record(
                conflict_id, "JUDGE_INVALID", witness, True
            ))
            continue
        changed = [
            key
            for key in (
                "selected_object",
                "selection_basis",
                "pragmatic_preference",
                "evidence_state",
                "assessment_process_state",
            )
            if baseline_outputs[conflict_id][key] != gated["payload"][key]
        ]
        selective_outputs[conflict_id] = gated["payload"]
        challenge_records.append({
            **_challenge_record(
                conflict_id, "COMPLETED", witness, True
            ),
            "judge_source_receipt": judge_envelope.normalized_result,
            "changed_axes": changed,
        })
    outputs = [
        _output(BASELINE_CELL, conflict_id, payload, "BASELINE")
        for conflict_id, payload in baseline_outputs.items()
    ] + [
        _output(
            SELECTIVE_CELL,
            conflict_id,
            payload,
            (
                "CHALLENGE"
                if conflict_id in plan["admitted_conflict_ids"]
                and any(
                    record["conflict_id"] == conflict_id
                    and record["status"] == "COMPLETED"
                    for record in challenge_records
                )
                else "BASELINE_PRESERVED"
            ),
        )
        for conflict_id, payload in selective_outputs.items()
    ]
    commitment = {
        "runtime_version": EVIDENCE_FIRST_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "challenge_plan": plan,
        "provider_calls": calls,
        "challenge_records": challenge_records,
        "outputs": outputs,
        "failures": failures,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "failed_challenge_preserves_baseline": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_evidence_first_run(*, corpus, run):
    by_cell = {cell: {} for cell in CELLS}
    for output in run["outputs"]:
        by_cell[output["cell"]][output["conflict_id"]] = output
    costs = {stage: Counter() for stage in (
        "BASELINE_SOURCE",
        "EVIDENCE_WITNESS",
        "WITNESS_BOUND_JUDGE",
    )}
    for call in run["provider_calls"]:
        usage = call["invocation_receipt"].get("token_usage") or {}
        costs[call["stage"]].update({
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
    baseline_tokens = (
        costs["BASELINE_SOURCE"]["input_tokens"]
        + costs["BASELINE_SOURCE"]["output_tokens"]
    )
    total_tokens = sum(
        value["input_tokens"] + value["output_tokens"]
        for value in costs.values()
    )
    completed = [
        record for record in run["challenge_records"]
        if record["status"] == "COMPLETED"
    ]
    commitment = {
        "analysis_version": EVIDENCE_FIRST_VERSION,
        "source_run_hash": run["run_hash"],
        "cell_coverage": {
            cell: round(len(values) / corpus["case_count"], 6)
            for cell, values in by_cell.items()
        },
        "challenged_count": len(run["challenge_plan"]["admitted_conflict_ids"]),
        "completed_challenge_count": len(completed),
        "witness_validation_rate": round(
            sum(record["witness_validated"] for record in run["challenge_records"])
            / len(run["challenge_records"]),
            6,
        ) if run["challenge_records"] else None,
        "changed_axis_counts": dict(Counter(
            axis for record in completed for axis in record["changed_axes"]
        )),
        "changed_object_count": sum(bool(record["changed_axes"]) for record in completed),
        "failure_counts": dict(Counter(
            failure["stage"] for failure in run["failures"]
        )),
        "stage_accounting": {
            stage: dict(value) for stage, value in costs.items()
        },
        "baseline_total_tokens": baseline_tokens,
        "selective_total_tokens": total_tokens,
        "selective_to_baseline_token_ratio": (
            round(total_tokens / baseline_tokens, 6)
            if baseline_tokens else None
        ),
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": (
            "EVIDENCE_FIRST_SELECTIVE_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
        ),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def _challenge_plan(receipts):
    decisive_sources = {
        "EXPLICIT_REQUEST_DEFINITION",
        "ESTABLISHED_UNAMBIGUOUS_TERM",
        "COMPOSED_CONSTRAINTS",
    }
    decisive = [
        conflict_id for conflict_id, receipt in receipts.items()
        if receipt["definition_source"] in decisive_sources
    ]
    open_items = [
        conflict_id for conflict_id, receipt in receipts.items()
        if receipt["definition_source"] not in decisive_sources
    ]
    rank = lambda conflict_id: (
        receipts[conflict_id]["confidence"],
        hash_payload([EVIDENCE_FIRST_VERSION, "challenge", conflict_id]),
    )
    decisive = sorted(decisive, key=rank)[:DECISIVE_CAP]
    open_items = sorted(open_items, key=rank)[:OPEN_CAP]
    commitment = {
        "plan_version": EVIDENCE_FIRST_VERSION,
        "decisive_conflict_ids": decisive,
        "open_conflict_ids": open_items,
        "admitted_conflict_ids": decisive + open_items,
        "decisive_cap": DECISIVE_CAP,
        "open_cap": OPEN_CAP,
        "reference_available": False,
    }
    return {**commitment, "plan_hash": hash_payload(commitment)}


def _baseline_task(item, refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{EVIDENCE_FIRST_VERSION}-baseline-{item['conflict_id']}",
        task_kind=EVIDENCE_FIRST_TASK_KIND,
        objective=(
            "Identify the operative definition source. Distinguish positive "
            "definition, composed constraints, ordinary underspecification, "
            "and a missing named external specification. Candidate option "
            "text is not evidence. Keep semantic selection separate from "
            "pragmatic preference."
        ),
        inputs={"stage": "BASELINE_SOURCE", "public_object": item},
        allowed_evidence=list(refs),
        expected_schema=source_schema(item["conflict_id"], refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def _witness_task(item, refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{EVIDENCE_FIRST_VERSION}-witness-{item['conflict_id']}",
        task_kind=EVIDENCE_FIRST_TASK_KIND,
        objective=(
            "Produce evidence only, before any semantic label. Quote one to "
            "three exact spans from evidence_text. Do not copy candidate option "
            "text as evidence. Identify whether the spans support a positive "
            "definition, a multi-step derivation, explicit evidence absence, "
            "conflict, or unresolved status. Derivation steps may explain how "
            "quoted premises combine, but do not output selected_object, "
            "definition_source, evidence_state, or selection_basis."
        ),
        inputs={
            "stage": "EVIDENCE_WITNESS",
            "evidence_text": evidence_text(item),
            "candidate_a": item["candidate_a"],
            "candidate_b": item["candidate_b"],
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=witness_schema(item["conflict_id"], refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_baseline_on_failure",
    )


def _judge_task(item, witness, refs, adapter):
    return ProviderCognitiveTask(
        task_id=f"{EVIDENCE_FIRST_VERSION}-judge-{item['conflict_id']}",
        task_kind=EVIDENCE_FIRST_TASK_KIND,
        objective=(
            "Judge the semantic object using only the mechanically verified "
            "witness and the candidate identities. Do not introduce a new "
            "support span or treat candidate option text as evidence. Map a "
            "positive defining witness to direct evidence only when it fixes a "
            "candidate; map a derivation witness to composed constraints only "
            "when its steps entail a candidate; map explicit absence to an "
            "ordinary open surface or missing external specification as "
            "appropriate. A justified open conclusion can be COMPLETE."
        ),
        inputs={
            "stage": "WITNESS_BOUND_JUDGE",
            "verified_witness": witness,
            "candidate_a": item["candidate_a"],
            "candidate_b": item["candidate_b"],
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=source_schema(item["conflict_id"], refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_baseline_on_failure",
    )


def _call(stage, conflict_id, task, envelope):
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
        "reference_available": False,
    }
    return {**commitment, "call_hash": hash_payload(commitment)}


def _failure(stage, item, envelope):
    return {
        "stage": stage,
        "conflict_id": item["conflict_id"],
        "status": envelope.status,
        "validation_errors": list(envelope.validation_errors),
    }


def _challenge_record(conflict_id, status, witness, validated):
    return {
        "conflict_id": conflict_id,
        "status": status,
        "verified_witness": witness,
        "witness_validated": validated,
        "baseline_preserved_on_failure": status != "COMPLETED",
    }


def _output(cell, conflict_id, payload, origin):
    commitment = {
        "cell": cell,
        "conflict_id": conflict_id,
        "payload": payload,
        "origin": origin,
        "reference_available": False,
    }
    return {**commitment, "output_hash": hash_payload(commitment)}
