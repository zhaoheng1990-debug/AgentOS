"""Compiler and split conflict ledger for context utility v0.81."""

from __future__ import annotations

from .admission_v6_derivation import derive_policy_record
from .provider_telemetry import hash_payload


def compile_context_utility_witness(*, item, receipt):
    span_text = {
        span["span_id"]: span["text"]
        for span in item["candidate_spans"]
    }
    derived = [
        derive_policy_record(
            fact,
            span_text=span_text[fact["span_id"]],
        )
        for fact in receipt["records"]
    ]
    keys = {
        "ADMIT_EVIDENCE": "evidence_span_ids",
        "RETAIN_CONTEXT": "context_span_ids",
        "REJECT": "rejected_span_ids",
    }
    partition = {
        key: sorted(
            record["span_id"]
            for record in derived
            if record["disposition"] == disposition
        )
        for disposition, key in keys.items()
    }
    observed = [
        span_id
        for values in partition.values()
        for span_id in values
    ]
    expected = sorted(span_text)
    if sorted(observed) != expected or len(observed) != len(set(observed)):
        raise ValueError("admission_v6_compiled_partition_invalid")
    conflicts = [
        {
            "span_id": record["span_id"],
            "effect_codes": record["effect_semantic_conflicts"],
            "context_codes": record["context_semantic_conflicts"],
            "resolution": record["conflict_resolution"],
        }
        for record in derived
        if record["semantic_conflicts"]
    ]
    evidence_available = bool(partition["evidence_span_ids"])
    value = {
        "compiler_version": "context_utility_witness_compiler_v0_81",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_context_utility_receipt_hash": hash_payload(receipt),
        "derived_records": sorted(
            derived,
            key=lambda record: record["span_id"],
        ),
        "semantic_conflict_ledger": sorted(
            conflicts,
            key=lambda record: record["span_id"],
        ),
        "semantic_conflict_count": len(conflicts),
        "conflicted_span_ids": sorted(
            record["span_id"] for record in conflicts
        ),
        **partition,
        "admission_state": (
            "EVIDENCE_AVAILABLE"
            if evidence_available
            else "NO_APPLICABLE_EVIDENCE"
        ),
        "downstream_effect_label_authorized": evidence_available,
        "abstention_required": not evidence_available,
        "provider_policy_override_allowed": False,
        "ungrounded_context_promotion_allowed": False,
        "context_conflict_effect_demotion_allowed": False,
    }
    return {**value, "partition_hash": hash_payload(value)}
