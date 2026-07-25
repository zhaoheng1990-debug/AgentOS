"""Deterministic partition compiler for typed evidence admission."""

from __future__ import annotations

from .provider_telemetry import hash_payload


def compile_typed_partition(*, item, receipt):
    records = receipt["records"]
    partitions = {
        "evidence_span_ids": sorted(
            record["span_id"] for record in records
            if record["disposition"] == "ADMIT_EVIDENCE"
        ),
        "context_span_ids": sorted(
            record["span_id"] for record in records
            if record["disposition"] == "RETAIN_CONTEXT"
        ),
        "rejected_span_ids": sorted(
            record["span_id"] for record in records
            if record["disposition"] == "REJECT"
        ),
    }
    observed = [
        span_id
        for values in partitions.values()
        for span_id in values
    ]
    expected = sorted(
        span["span_id"] for span in item["candidate_spans"]
    )
    if sorted(observed) != expected or len(observed) != len(set(observed)):
        raise ValueError("admission_v2_compiled_partition_invalid")
    evidence_available = bool(partitions["evidence_span_ids"])
    state = (
        "EVIDENCE_AVAILABLE"
        if evidence_available
        else "NO_APPLICABLE_EVIDENCE"
    )
    if receipt["admission_state"] != state:
        raise ValueError("admission_v2_compiled_state_mismatch")
    value = {
        "compiler_version": "typed_admission_compiler_v0_76",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_admission_receipt_hash": hash_payload(receipt),
        **partitions,
        "admission_state": state,
        "downstream_effect_label_authorized": evidence_available,
        "abstention_required": not evidence_available,
        "provider_partition_override_allowed": False,
    }
    return {**value, "partition_hash": hash_payload(value)}
