"""Provider-backed relational witness runtime v0.23."""

from __future__ import annotations

from collections import Counter

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .cognitive_action_evidence_calibrator import source_schema
from .cognitive_action_evidence_gate_policies import (
    REPAIRED_GATE,
    apply_gate_policy,
)
from .cognitive_action_relational_witness_holdout import (
    evidence_text,
    validate_relational_witness_holdout,
)
from .provider_telemetry import hash_payload


RELATIONAL_WITNESS_VERSION = (
    "cognitive_action_relational_witness_selective_v0_23"
)
RELATIONAL_WITNESS_TASK_KIND = (
    "COGNITIVE_ACTION_RELATIONAL_WITNESS_SELECTIVE"
)
SOURCE_EVALUATION_HASH = (
    "042402600ea29465e3a03eda94ebfebc3814fec02c7a6ccd65ee230e2de6e13d"
)
SOURCE_REFERENCE_HASH = (
    "b373ddeb7c1c00f5c2cae6454ed332ac6ba0b5161b139bc3c1bca7323593ca5a"
)
BASELINE_CELL = "BASELINE_LEGACY_SOURCE_REPAIRED_GATE"
RELATIONAL_CELL = "RELATIONAL_WITNESS_RUNTIME_SYNTHESIS"
CELLS = (BASELINE_CELL, RELATIONAL_CELL)
DECISIVE_CAP = 4
OPEN_CAP = 2
SOURCE_STATUSES = ("AVAILABLE", "MISSING", "UNSPECIFIED", "CONFLICTED")
SUPPORT_RELATIONS = (
    "DEFINES",
    "JOINTLY_ENTAILS",
    "INDICATES_ABSENCE",
    "NO_SUPPORT",
    "CONFLICTS",
)
SELECTIONS = ("CANDIDATE_A", "CANDIDATE_B", "NONE", "UNCERTAIN")


def build_relational_witness_preregistration(*, source_evaluation):
    if (
        source_evaluation.get("artifact_hash") != SOURCE_EVALUATION_HASH
        or source_evaluation.get("reference_hash") != SOURCE_REFERENCE_HASH
        or source_evaluation.get("anti_additive_gate") != "REJECT"
        or source_evaluation.get("candidate_state")
        != "EVIDENCE_FIRST_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
    ):
        raise ValueError("relational_witness_source_evaluation_invalid")
    commitment = {
        "preregistration_version": RELATIONAL_WITNESS_VERSION,
        "source_evaluation_hash": SOURCE_EVALUATION_HASH,
        "source_reference_hash": SOURCE_REFERENCE_HASH,
        "frozen_hypothesis": (
            "binding requested object, source availability, support relation, "
            "and candidate entailment in one Provider receipt lets Runtime "
            "block false positive definitions at lower cost"
        ),
        "cells": list(CELLS),
        "challenge_plan": {
            "decisive_source_cap": DECISIVE_CAP,
            "open_source_cap": OPEN_CAP,
            "ranking": "ascending_confidence_then_hash",
            "maximum_challenged_objects": DECISIVE_CAP + OPEN_CAP,
            "reference_available": False,
        },
        "relational_invariants": {
            "requested_object_quote_must_be_exact": True,
            "source_status_quote_must_be_exact": True,
            "support_spans_must_be_exact_pre_candidate_text": True,
            "candidate_option_text_cannot_be_evidence": True,
            "missing_source_forces_anti_entailment": True,
            "positive_entailment_requires_available_source": True,
            "runtime_synthesizes_tuple_without_second_provider_judge": True,
            "failed_witness_preserves_baseline": True,
        },
        "success_gate": {
            "minimum_net_correct_cell_gain": 2,
            "minimum_evidence_state_correct_gain": 2,
            "minimum_challenged_full_tuple_gain": 1,
            "maximum_selected_object_correct_loss": 0,
            "corrections_must_exceed_harms": True,
            "required_output_coverage": 1.0,
            "maximum_relational_to_baseline_token_ratio": 1.55,
            "required_relational_witness_validation_rate": 1.0,
        },
        "v0_22_labels_used_as_failure_mechanism_only": True,
        "fresh_v0_23_labels_available_during_inference": False,
        "reference_revision_allowed_after_candidate_run": False,
        "baseline_promotion_allowed_before_external_panel": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def relational_witness_schema(conflict_id, evidence_refs):
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "conflict_id",
            "requested_object_quote",
            "source_status_quote",
            "definition_source_status",
            "support_relation",
            "support_spans",
            "derivation_steps",
            "candidate_entailment",
            "contextual_default",
            "anti_entailment_reason",
            "candidate_option_text_used_as_evidence",
            "rationale",
            "confidence",
            "evidence_refs",
        ],
        "properties": {
            "conflict_id": {"type": "string", "enum": [conflict_id]},
            "requested_object_quote": {
                "type": "string", "minLength": 1, "maxLength": 240,
            },
            "source_status_quote": {
                "type": "string", "minLength": 1, "maxLength": 320,
            },
            "definition_source_status": {
                "type": "string", "enum": list(SOURCE_STATUSES),
            },
            "support_relation": {
                "type": "string", "enum": list(SUPPORT_RELATIONS),
            },
            "support_spans": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "string", "minLength": 1, "maxLength": 320,
                },
            },
            "derivation_steps": {
                "type": "array",
                "maxItems": 4,
                "items": {
                    "type": "string", "minLength": 1, "maxLength": 400,
                },
            },
            "candidate_entailment": {
                "type": "string", "enum": list(SELECTIONS),
            },
            "contextual_default": {
                "type": "string", "enum": list(SELECTIONS),
            },
            "anti_entailment_reason": {
                "type": "string", "minLength": 1, "maxLength": 500,
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


def validate_relational_witness(receipt, *, item, evidence_refs):
    required = set(
        relational_witness_schema(
            item["conflict_id"],
            evidence_refs,
        )["required"]
    )
    text = evidence_text(item)
    if (
        not isinstance(receipt, dict)
        or set(receipt) != required
        or receipt.get("conflict_id") != item["conflict_id"]
        or receipt.get("definition_source_status") not in SOURCE_STATUSES
        or receipt.get("support_relation") not in SUPPORT_RELATIONS
        or receipt.get("candidate_entailment") not in SELECTIONS
        or receipt.get("contextual_default") not in SELECTIONS
        or receipt.get("requested_object_quote") not in text
        or receipt.get("source_status_quote") not in text
        or not _valid_spans(receipt.get("support_spans"), item, text)
        or receipt["source_status_quote"] not in receipt["support_spans"]
        or not _valid_steps(receipt.get("derivation_steps"))
        or not str(receipt.get("anti_entailment_reason", "")).strip()
        or receipt.get("candidate_option_text_used_as_evidence") is not False
        or not str(receipt.get("rationale", "")).strip()
        or not _confidence(receipt.get("confidence"))
        or receipt.get("evidence_refs") != list(evidence_refs)
    ):
        raise ValueError("relational_witness_invalid")
    _validate_relations(receipt)


def synthesize_relational_tuple(receipt, *, conflict_id, evidence_refs):
    status = receipt["definition_source_status"]
    relation = receipt["support_relation"]
    selected = receipt["candidate_entailment"]
    preference = receipt["contextual_default"]
    if status == "AVAILABLE":
        source = (
            "EXPLICIT_REQUEST_DEFINITION"
            if relation == "DEFINES"
            else "COMPOSED_CONSTRAINTS"
        )
    elif status == "MISSING":
        source, selected, preference = (
            "MISSING_EXTERNAL_SPECIFICATION", "NONE", "NONE"
        )
    elif status == "UNSPECIFIED":
        source, selected = "UNDERSPECIFIED_SURFACE", "NONE"
        if preference == "UNCERTAIN":
            preference = "NONE"
    else:
        source, selected, preference = (
            "CONFLICTING_SURFACE", "UNCERTAIN", "UNCERTAIN"
        )
    source_receipt = {
        "conflict_id": conflict_id,
        "selected_object": selected,
        "definition_source": source,
        "pragmatic_preference": preference,
        "assessment_process_state": "COMPLETE",
        "support_quote": receipt["source_status_quote"],
        "rationale": receipt["rationale"],
        "confidence": receipt["confidence"],
        "evidence_refs": list(evidence_refs),
    }
    gated = apply_gate_policy(
        REPAIRED_GATE,
        source_receipt,
        conflict_id=conflict_id,
        evidence_refs=evidence_refs,
    )
    return {
        **gated,
        "relational_source_receipt": source_receipt,
    }


def run_relational_witness_selective(*, corpus, preregistration, adapter):
    validate_relational_witness_holdout(corpus)
    if (
        preregistration.get("preregistration_version")
        != RELATIONAL_WITNESS_VERSION
        or preregistration.get("artifact_hash")
        != hash_payload({
            key: value for key, value in preregistration.items()
            if key != "artifact_hash"
        })
    ):
        raise ValueError("relational_witness_preregistration_invalid")
    refs = tuple(corpus["evidence_refs"])
    public = {
        item["conflict_id"]: item
        for item in corpus["public_surface"]["items"]
    }
    calls, failures, baseline, source_receipts = [], [], {}, {}
    for item in corpus["public_surface"]["items"]:
        task = _baseline_task(item, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        calls.append(_call(
            "BASELINE_SOURCE",
            item["conflict_id"],
            task,
            envelope,
        ))
        if envelope.status != "COMPLETED":
            failures.append(_failure(
                "BASELINE_SOURCE",
                item["conflict_id"],
                envelope,
            ))
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
        baseline[item["conflict_id"]] = gated["payload"]

    plan = _challenge_plan(source_receipts)
    relational = dict(baseline)
    records = []
    for conflict_id in plan["admitted_conflict_ids"]:
        item = public[conflict_id]
        task = _relational_task(item, refs, adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        calls.append(_call(
            "RELATIONAL_WITNESS",
            conflict_id,
            task,
            envelope,
        ))
        if envelope.status != "COMPLETED":
            failures.append(_failure(
                "RELATIONAL_WITNESS",
                conflict_id,
                envelope,
            ))
            records.append(_record(
                conflict_id, "WITNESS_FAILED", None, False
            ))
            continue
        witness = envelope.normalized_result
        try:
            validate_relational_witness(
                witness,
                item=item,
                evidence_refs=refs,
            )
            synthesized = synthesize_relational_tuple(
                witness,
                conflict_id=conflict_id,
                evidence_refs=refs,
            )
        except ValueError as exc:
            failures.append({
                "stage": "RELATIONAL_WITNESS",
                "conflict_id": conflict_id,
                "status": "RELATIONAL_VALIDATION_FAILED",
                "validation_errors": [str(exc)],
                "provider_receipt_preserved": witness,
            })
            records.append(_record(
                conflict_id, "WITNESS_INVALID", witness, False
            ))
            continue
        changed = [
            key for key in (
                "selected_object",
                "selection_basis",
                "pragmatic_preference",
                "evidence_state",
                "assessment_process_state",
            )
            if baseline[conflict_id][key]
            != synthesized["payload"][key]
        ]
        relational[conflict_id] = synthesized["payload"]
        records.append({
            **_record(conflict_id, "COMPLETED", witness, True),
            "relational_source_receipt": (
                synthesized["relational_source_receipt"]
            ),
            "runtime_gate_transforms": synthesized["gate_transforms"],
            "changed_axes": changed,
        })
    outputs = [
        _output(BASELINE_CELL, conflict_id, payload, "BASELINE")
        for conflict_id, payload in baseline.items()
    ] + [
        _output(
            RELATIONAL_CELL,
            conflict_id,
            payload,
            (
                "RELATIONAL_SYNTHESIS"
                if any(
                    record["conflict_id"] == conflict_id
                    and record["status"] == "COMPLETED"
                    for record in records
                )
                else "BASELINE_PRESERVED"
            ),
        )
        for conflict_id, payload in relational.items()
    ]
    commitment = {
        "runtime_version": RELATIONAL_WITNESS_VERSION,
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "challenge_plan": plan,
        "provider_calls": calls,
        "challenge_records": records,
        "outputs": outputs,
        "failures": failures,
        "external_reference_available": False,
        "candidate_outputs_frozen_before_external_reference": True,
        "runtime_synthesizes_without_second_provider_judge": True,
        "failed_witness_preserves_baseline": True,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def analyze_relational_witness_run(*, corpus, run):
    by_cell = {cell: {} for cell in CELLS}
    for output in run["outputs"]:
        by_cell[output["cell"]][output["conflict_id"]] = output
    costs = {
        stage: Counter()
        for stage in ("BASELINE_SOURCE", "RELATIONAL_WITNESS")
    }
    for call in run["provider_calls"]:
        usage = call["invocation_receipt"].get("token_usage") or {}
        costs[call["stage"]].update({
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
        "analysis_version": RELATIONAL_WITNESS_VERSION,
        "source_run_hash": run["run_hash"],
        "cell_coverage": {
            cell: round(len(values) / corpus["case_count"], 6)
            for cell, values in by_cell.items()
        },
        "challenged_count": len(run["challenge_plan"]["admitted_conflict_ids"]),
        "completed_challenge_count": len(completed),
        "relational_witness_validation_rate": round(
            sum(
                record["relational_witness_validated"]
                for record in run["challenge_records"]
            ) / len(run["challenge_records"]),
            6,
        ) if run["challenge_records"] else None,
        "source_status_distribution": dict(Counter(
            record["relational_witness"]["definition_source_status"]
            for record in completed
        )),
        "support_relation_distribution": dict(Counter(
            record["relational_witness"]["support_relation"]
            for record in completed
        )),
        "changed_axis_counts": dict(Counter(
            axis for record in completed for axis in record["changed_axes"]
        )),
        "changed_object_count": sum(
            bool(record["changed_axes"]) for record in completed
        ),
        "failure_counts": dict(Counter(
            failure["stage"] for failure in run["failures"]
        )),
        "stage_accounting": {
            stage: dict(value) for stage, value in costs.items()
        },
        "baseline_total_tokens": baseline_tokens,
        "relational_total_tokens": total_tokens,
        "relational_to_baseline_token_ratio": (
            round(total_tokens / baseline_tokens, 6)
            if baseline_tokens else None
        ),
        "semantic_accuracy_available": False,
        "external_panel_required": True,
        "candidate_state": (
            "RELATIONAL_WITNESS_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL"
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
        hash_payload([RELATIONAL_WITNESS_VERSION, "challenge", conflict_id]),
    )
    decisive = sorted(decisive, key=rank)[:DECISIVE_CAP]
    open_items = sorted(open_items, key=rank)[:OPEN_CAP]
    commitment = {
        "plan_version": RELATIONAL_WITNESS_VERSION,
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
        task_id=(
            f"{RELATIONAL_WITNESS_VERSION}-baseline-"
            f"{item['conflict_id']}"
        ),
        task_kind=RELATIONAL_WITNESS_TASK_KIND,
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


def _relational_task(item, refs, adapter):
    return ProviderCognitiveTask(
        task_id=(
            f"{RELATIONAL_WITNESS_VERSION}-witness-"
            f"{item['conflict_id']}"
        ),
        task_kind=RELATIONAL_WITNESS_TASK_KIND,
        objective=(
            "Produce one relational evidence receipt. First bind the exact "
            "requested object. Then determine whether its definition source "
            "is AVAILABLE, MISSING, UNSPECIFIED, or CONFLICTED. Quote exact "
            "pre-candidate text for the object and source status. Classify "
            "whether evidence DEFINES a candidate, JOINTLY_ENTAILS it, only "
            "INDICATES_ABSENCE, provides NO_SUPPORT, or CONFLICTS. A named "
            "specification whose catalog or formula is unavailable is "
            "MISSING and cannot entail either candidate. Candidate option "
            "text is never evidence. Keep semantic entailment separate from "
            "a merely contextual default. Include source_status_quote among "
            "support_spans. For AVAILABLE sources use exactly NOT_APPLICABLE "
            "as anti_entailment_reason; for every other source status provide "
            "a concrete anti-entailment reason."
        ),
        inputs={
            "stage": "RELATIONAL_WITNESS",
            "evidence_text": evidence_text(item),
            "candidate_a": item["candidate_a"],
            "candidate_b": item["candidate_b"],
            "conflict_id": item["conflict_id"],
        },
        allowed_evidence=list(refs),
        expected_schema=relational_witness_schema(
            item["conflict_id"],
            refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_baseline_on_failure",
    )


def _validate_relations(receipt):
    status = receipt["definition_source_status"]
    relation = receipt["support_relation"]
    entailment = receipt["candidate_entailment"]
    default = receipt["contextual_default"]
    steps = receipt["derivation_steps"]
    anti = receipt["anti_entailment_reason"].strip()
    if status == "AVAILABLE":
        if (
            relation not in ("DEFINES", "JOINTLY_ENTAILS")
            or entailment not in ("CANDIDATE_A", "CANDIDATE_B")
            or anti != "NOT_APPLICABLE"
            or (relation == "DEFINES" and steps)
            or (relation == "JOINTLY_ENTAILS" and not steps)
        ):
            raise ValueError("relational_witness_available_mismatch")
    elif status == "MISSING":
        if (
            relation != "INDICATES_ABSENCE"
            or entailment != "NONE"
            or default != "NONE"
            or anti == "NOT_APPLICABLE"
            or steps
        ):
            raise ValueError("relational_witness_missing_mismatch")
    elif status == "UNSPECIFIED":
        if (
            relation != "NO_SUPPORT"
            or entailment != "NONE"
            or default == "UNCERTAIN"
            or anti == "NOT_APPLICABLE"
            or steps
        ):
            raise ValueError("relational_witness_unspecified_mismatch")
    elif (
        relation != "CONFLICTS"
        or entailment != "UNCERTAIN"
        or default != "UNCERTAIN"
        or anti == "NOT_APPLICABLE"
    ):
        raise ValueError("relational_witness_conflicted_mismatch")


def _valid_spans(spans, item, text):
    return (
        isinstance(spans, list)
        and 1 <= len(spans) <= 3
        and all(
            isinstance(span, str)
            and span.strip()
            and span in text
            and span not in (item["candidate_a"], item["candidate_b"])
            for span in spans
        )
    )


def _valid_steps(steps):
    return (
        isinstance(steps, list)
        and len(steps) <= 4
        and all(isinstance(step, str) and step.strip() for step in steps)
    )


def _confidence(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
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


def _failure(stage, conflict_id, envelope):
    return {
        "stage": stage,
        "conflict_id": conflict_id,
        "status": envelope.status,
        "validation_errors": list(envelope.validation_errors),
    }


def _record(conflict_id, status, witness, validated):
    return {
        "conflict_id": conflict_id,
        "status": status,
        "relational_witness": witness,
        "relational_witness_validated": validated,
        "baseline_preserved_on_failure": status != "COMPLETED",
    }


def _output(cell, conflict_id, payload, origin):
    commitment = {
        "cell": cell,
        "conflict_id": conflict_id,
        "origin": origin,
        "payload": payload,
        "reference_available": False,
    }
    return {**commitment, "output_hash": hash_payload(commitment)}
