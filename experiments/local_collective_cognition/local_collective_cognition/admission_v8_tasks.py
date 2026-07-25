"""Independent Provider task for selective evidence-boundary review."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v8_schemas import boundary_review_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def boundary_review_task(*, item, staged_partition, adapter):
    rejected = set(staged_partition["rejected_span_ids"])
    candidates = [
        span for span in item["candidate_spans"]
        if span["span_id"] not in rejected
    ]
    reviewed_ids = tuple(span["span_id"] for span in candidates)
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v8-83-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Independently assess the evidence-versus-context boundary for "
            "each supplied span. Upstream dispositions are hidden. Do not "
            "return evidence status, context status, disposition, partition, "
            "or a final effect label. Report whether the exact intervention, "
            "comparator, outcome, and target timepoint match; whether comparator "
            "and outcome are separately isolated rather than pooled; and "
            "whether the span contains an independent target-effect statement. "
            "For a fully positive witness use boundary_issue_codes=[NONE], "
            "copy a short exact effect quote into support_anchor_quote, and "
            "leave boundary_anchor_quote empty. For any mismatch, pooling, "
            "timepoint error, or absent independent statement, provide every "
            "applicable issue code, copy a short exact source quote showing "
            "the boundary problem into boundary_anchor_quote, and leave "
            "support_anchor_quote empty unless a separate effect statement is "
            "also present. Runtime validates grounding and owns mutation."
        ),
        inputs={
            "mechanism": "A17_SELECTIVE_EVIDENCE_BOUNDARY_REVIEW",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": candidates,
            "source_item_hash": hash_payload(item),
            "source_staged_partition_hash": (
                staged_partition["partition_hash"]
            ),
            "upstream_dispositions_exposed": False,
            "private_gold_available": False,
            "policy_labels_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=boundary_review_schema(
            item=item,
            reviewed_span_ids=reviewed_ids,
            staged_partition=staged_partition,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
