"""Kernel compiler for staged context utility v0.82."""

from __future__ import annotations

from .admission_v7_facts import context_fact_conflicts
from .provider_telemetry import hash_payload


def compile_context_addon(
    *,
    item,
    atomic_receipt,
    atomic_partition,
    receipt,
):
    spans = {
        span["span_id"]: span["text"]
        for span in item["candidate_spans"]
    }
    atomic_facts = {
        fact["span_id"]: fact for fact in atomic_receipt["records"]
    }
    evidence = set(atomic_partition["evidence_span_ids"])
    expected_non_evidence = set(spans) - evidence
    context_facts = {
        fact["span_id"]: fact for fact in receipt["records"]
    }
    if set(context_facts) != expected_non_evidence:
        raise ValueError("admission_v7_context_coverage_invalid")
    derived, conflicts = [], []
    for span_id in sorted(expected_non_evidence):
        atomic_fact = atomic_facts[span_id]
        context_fact = context_facts[span_id]
        codes = context_fact_conflicts(
            context_fact,
            span_text=spans[span_id],
        )
        intrinsic = (
            atomic_fact["exact_target_object_mentioned"]
            or atomic_fact["target_effect_separately_extractable"]
        )
        witnessed = (
            context_fact["context_utility_code"] != "NO_TARGET_UTILITY"
            and context_fact["context_changes_downstream_decision"]
            and not codes
        )
        retained = intrinsic or witnessed
        record = {
            "span_id": span_id,
            "disposition": (
                "RETAIN_CONTEXT" if retained else "REJECT"
            ),
            "context_utility_code": (
                "INTRINSIC_TARGET_CONTEXT"
                if intrinsic
                else context_fact["context_utility_code"]
                if witnessed
                else "NO_VALIDATED_TARGET_UTILITY"
            ),
            "utility_anchor_quote": (
                context_fact["utility_anchor_quote"]
            ),
            "context_semantic_conflicts": codes,
            "policy_derivation_basis": (
                "FROZEN_ATOMIC_TARGET_CONTEXT"
                if intrinsic
                else "GROUNDED_CONTEXT_UTILITY_WITNESS"
                if witnessed
                else "NO_VALIDATED_TARGET_UTILITY"
            ),
            "conflict_resolution": (
                "FAIL_CLOSED_TO_REJECT" if codes and not intrinsic
                else "FROZEN_TARGET_CONTEXT_PRIORITY"
                if codes and intrinsic
                else "NONE"
            ),
        }
        derived.append(record)
        if codes:
            conflicts.append({
                "span_id": span_id,
                "context_codes": codes,
                "resolution": record["conflict_resolution"],
            })
    context = {
        record["span_id"] for record in derived
        if record["disposition"] == "RETAIN_CONTEXT"
    }
    rejected = expected_non_evidence - context
    observed = evidence | context | rejected
    if observed != set(spans) or evidence & (context | rejected):
        raise ValueError("admission_v7_compiled_partition_invalid")
    value = {
        "compiler_version": "staged_context_addon_compiler_v0_82",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_atomic_receipt_hash": hash_payload(atomic_receipt),
        "source_atomic_partition_hash": atomic_partition["partition_hash"],
        "source_context_addon_receipt_hash": hash_payload(receipt),
        "derived_context_records": derived,
        "semantic_conflict_ledger": conflicts,
        "semantic_conflict_count": len(conflicts),
        "conflicted_span_ids": sorted(
            record["span_id"] for record in conflicts
        ),
        "evidence_span_ids": sorted(evidence),
        "context_span_ids": sorted(context),
        "rejected_span_ids": sorted(rejected),
        "admission_state": atomic_partition["admission_state"],
        "downstream_effect_label_authorized": (
            atomic_partition["downstream_effect_label_authorized"]
        ),
        "abstention_required": atomic_partition["abstention_required"],
        "provider_policy_override_allowed": False,
        "atomic_evidence_partition_mutation_allowed": False,
        "ungrounded_context_promotion_allowed": False,
    }
    return {**value, "partition_hash": hash_payload(value)}
