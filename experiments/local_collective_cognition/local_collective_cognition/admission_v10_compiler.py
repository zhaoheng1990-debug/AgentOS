"""Kernel compiler for bounded study-relation mutations."""

from __future__ import annotations

from .admission_v10_facts import (
    context_witness,
    evidence_witness,
    semantic_graph_conflicts,
)
from .provider_telemetry import hash_payload


def compile_study_relation_review(*, item, staged_partition, receipt):
    spans = {
        span["span_id"]: span["text"]
        for span in item["candidate_spans"]
    }
    upstream = {
        "ADMIT_EVIDENCE": set(staged_partition["evidence_span_ids"]),
        "RETAIN_CONTEXT": set(staged_partition["context_span_ids"]),
        "REJECT": set(staged_partition["rejected_span_ids"]),
    }
    facts = {
        fact["span_id"]: fact for fact in receipt["span_records"]
    }
    if set(facts) != set(spans):
        raise ValueError("admission_v10_review_coverage_invalid")
    conflicts = semantic_graph_conflicts(
        bindings=receipt["bindings"],
        facts=receipt["span_records"],
        spans=spans,
    )
    conflict_spans = {
        code.split(":", 1)[0]
        for code in conflicts
        if ":" in code and code.split(":", 1)[0] in spans
    }
    evidence = set(upstream["ADMIT_EVIDENCE"])
    context = set(upstream["RETAIN_CONTEXT"])
    rejected = set(upstream["REJECT"])
    mutations = []
    for span_id in sorted(spans):
        fact = facts[span_id]
        before = _disposition(span_id, upstream)
        after = before
        basis = "PRESERVE_UPSTREAM_NO_RELATIONAL_WITNESS"
        if span_id not in conflict_spans and not conflicts:
            evidence_ok = evidence_witness(
                fact=fact,
                bindings=receipt["bindings"],
                spans=spans,
                all_facts=receipt["span_records"],
            )
            context_ok = context_witness(
                fact=fact,
                bindings=receipt["bindings"],
                spans=spans,
                all_facts=receipt["span_records"],
            )
            if before == "ADMIT_EVIDENCE" and context_ok:
                evidence.remove(span_id)
                context.add(span_id)
                after = "RETAIN_CONTEXT"
                basis = "GROUNDED_RELATIONAL_CONTEXT_WITNESS"
            elif before == "RETAIN_CONTEXT" and evidence_ok:
                context.remove(span_id)
                evidence.add(span_id)
                after = "ADMIT_EVIDENCE"
                basis = "GROUNDED_RELATIONAL_EVIDENCE_WITNESS"
            elif before == "REJECT" and context_ok:
                rejected.remove(span_id)
                context.add(span_id)
                after = "RETAIN_CONTEXT"
                basis = "GROUNDED_RELATIONAL_CONTEXT_RECOVERY"
        if after != before:
            mutations.append({
                "span_id": span_id,
                "before": before,
                "after": after,
                "basis": basis,
            })
    observed = evidence | context | rejected
    if (
        observed != set(spans)
        or evidence & context
        or evidence & rejected
        or context & rejected
    ):
        raise ValueError("admission_v10_compiled_partition_invalid")
    value = {
        "compiler_version": "study_relation_compiler_v0_85",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_staged_partition_hash": staged_partition["partition_hash"],
        "source_study_relation_receipt_hash": hash_payload(receipt),
        "mutation_ledger": mutations,
        "mutation_count": len(mutations),
        "semantic_conflict_codes": conflicts,
        "semantic_conflict_count": len(conflicts),
        "evidence_span_ids": sorted(evidence),
        "context_span_ids": sorted(context),
        "rejected_span_ids": sorted(rejected),
        "admission_state": (
            "EVIDENCE_AVAILABLE" if evidence
            else "NO_APPLICABLE_EVIDENCE"
        ),
        "downstream_effect_label_authorized": bool(evidence),
        "abstention_required": not evidence,
        "provider_policy_authority": False,
        "evidence_to_context_allowed": True,
        "context_to_evidence_allowed": True,
        "reject_to_context_allowed": True,
        "evidence_to_reject_allowed": False,
        "context_to_reject_allowed": False,
        "reject_to_evidence_allowed": False,
        "conflicted_mutation_allowed": False,
    }
    return {**value, "partition_hash": hash_payload(value)}


def _disposition(span_id, partitions):
    for disposition, values in partitions.items():
        if span_id in values:
            return disposition
    raise ValueError("admission_v10_upstream_span_missing")
