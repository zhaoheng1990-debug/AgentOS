"""Provider task for the staged context-only addon."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v7_schemas import context_addon_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def context_addon_task(
    *,
    item,
    atomic_receipt,
    atomic_partition,
    adapter,
):
    evidence = set(atomic_partition["evidence_span_ids"])
    candidates = [
        span for span in item["candidate_spans"]
        if span["span_id"] not in evidence
    ]
    candidate_ids = tuple(span["span_id"] for span in candidates)
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v7-82-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Assess context utility only for the supplied non-evidence spans. "
            "The upstream atomic effect partition is frozen and cannot be "
            "rejudged. Do not return effect facts, evidence status, object "
            "relation, disposition, partition, admission state, or a final "
            "effect label. Determine whether each span changes a downstream "
            "judgment about the exact intervention-comparator-outcome target. "
            "Allowed functions are target identity or mapping, effect "
            "interpretation, scope or applicability, and evidence validity. "
            "General topical similarity, a different outcome, or background "
            "that changes no target judgment is NO_TARGET_UTILITY. For a real "
            "context function set context_changes_downstream_decision true "
            "and copy a short exact quote from that span into "
            "utility_anchor_quote. Otherwise use NO_TARGET_UTILITY, false, "
            "and an empty quote. Runtime validates grounding and owns the "
            "context-versus-reject decision."
        ),
        inputs={
            "mechanism": "A16_STAGED_CONTEXT_UTILITY_ADDON",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": candidates,
            "source_item_hash": hash_payload(item),
            "source_atomic_receipt_hash": hash_payload(atomic_receipt),
            "source_atomic_partition_hash": (
                atomic_partition["partition_hash"]
            ),
            "upstream_evidence_partition_frozen": True,
            "effect_rejudgment_requested": False,
            "private_gold_available": False,
            "policy_labels_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=context_addon_schema(
            item=item,
            candidate_span_ids=candidate_ids,
            atomic_receipt=atomic_receipt,
            atomic_partition=atomic_partition,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
