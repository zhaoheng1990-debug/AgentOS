"""Kernel mutation gate for ternary evidence/context boundary review."""

from __future__ import annotations

from .admission_v9_facts import (
    negative_boundary_witness,
    positive_boundary_witness,
    semantic_fact_conflicts,
)
from .provider_telemetry import hash_payload


def compile_ternary_boundary_review(*, item, staged_partition, receipt):
    spans = {
        span["span_id"]: span["text"]
        for span in item["candidate_spans"]
    }
    upstream_evidence = set(staged_partition["evidence_span_ids"])
    upstream_context = set(staged_partition["context_span_ids"])
    upstream_reject = set(staged_partition["rejected_span_ids"])
    facts = {fact["span_id"]: fact for fact in receipt["records"]}
    if set(facts) != upstream_evidence | upstream_context:
        raise ValueError("admission_v9_review_coverage_invalid")
    evidence = set(upstream_evidence)
    context = set(upstream_context)
    mutations, conflicts = [], []
    for span_id in sorted(facts):
        fact = facts[span_id]
        text = spans[span_id]
        codes = semantic_fact_conflicts(fact, span_text=text)
        positive = positive_boundary_witness(fact, span_text=text)
        negative = negative_boundary_witness(fact, span_text=text)
        before = (
            "ADMIT_EVIDENCE"
            if span_id in upstream_evidence
            else "RETAIN_CONTEXT"
        )
        after = before
        basis = "PRESERVE_UPSTREAM_NO_STRONG_WITNESS"
        if before == "ADMIT_EVIDENCE" and negative:
            evidence.remove(span_id)
            context.add(span_id)
            after = "RETAIN_CONTEXT"
            basis = "GROUNDED_EXPLICIT_NEGATIVE_WITNESS"
        elif before == "RETAIN_CONTEXT" and positive:
            context.remove(span_id)
            evidence.add(span_id)
            after = "ADMIT_EVIDENCE"
            basis = "GROUNDED_POSITIVE_EFFECT_WITNESS"
        if after != before:
            mutations.append({
                "span_id": span_id,
                "before": before,
                "after": after,
                "basis": basis,
            })
        if codes:
            conflicts.append({
                "span_id": span_id,
                "codes": codes,
                "resolution": "PRESERVE_UPSTREAM",
            })
    observed = evidence | context | upstream_reject
    if (
        observed != set(spans)
        or evidence & context
        or evidence & upstream_reject
        or context & upstream_reject
    ):
        raise ValueError("admission_v9_compiled_partition_invalid")
    value = {
        "compiler_version": "ternary_boundary_review_compiler_v0_84",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged_partition["partition_hash"],
        "source_boundary_review_receipt_hash": hash_payload(receipt),
        "mutation_ledger": mutations,
        "mutation_count": len(mutations),
        "semantic_conflict_ledger": conflicts,
        "semantic_conflict_count": len(conflicts),
        "evidence_span_ids": sorted(evidence),
        "context_span_ids": sorted(context),
        "rejected_span_ids": sorted(upstream_reject),
        "admission_state": (
            "EVIDENCE_AVAILABLE" if evidence
            else "NO_APPLICABLE_EVIDENCE"
        ),
        "downstream_effect_label_authorized": bool(evidence),
        "abstention_required": not evidence,
        "provider_policy_override_allowed": False,
        "reject_partition_mutation_allowed": False,
        "not_stated_demotion_allowed": False,
        "unwitnessed_boundary_mutation_allowed": False,
        "conflicted_boundary_mutation_allowed": False,
    }
    return {**value, "partition_hash": hash_payload(value)}
