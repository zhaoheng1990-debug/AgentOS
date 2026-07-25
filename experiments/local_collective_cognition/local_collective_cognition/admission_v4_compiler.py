"""Local compiler for minimal semantic witness v0.79."""

from __future__ import annotations

from .admission_v4_derivation import derive_policy_record
from .provider_telemetry import hash_payload


def compile_minimal_witness(*, item, receipt):
    derived = [
        derive_policy_record(fact)
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
    expected = sorted(
        span["span_id"] for span in item["candidate_spans"]
    )
    if sorted(observed) != expected or len(observed) != len(set(observed)):
        raise ValueError("admission_v4_compiled_partition_invalid")
    evidence_available = bool(partition["evidence_span_ids"])
    value = {
        "compiler_version": "minimal_witness_compiler_v0_79",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_semantic_fact_receipt_hash": hash_payload(receipt),
        "derived_records": sorted(
            derived,
            key=lambda record: record["span_id"],
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
    }
    return {**value, "partition_hash": hash_payload(value)}
