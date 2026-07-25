"""Independent Provider task for ternary evidence-boundary review."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v9_schemas import ternary_boundary_review_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def ternary_boundary_review_task(*, item, staged_partition, adapter):
    rejected = set(staged_partition["rejected_span_ids"])
    candidates = [
        span for span in item["candidate_spans"]
        if span["span_id"] not in rejected
    ]
    reviewed_ids = tuple(span["span_id"] for span in candidates)
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v9-84-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Assess the evidence-versus-context boundary for every supplied "
            "span without seeing upstream dispositions. For intervention, "
            "comparator, outcome, and timepoint, choose MATCHED only when the "
            "span states or unambiguously corefers to the target, "
            "EXPLICITLY_CONTRADICTED only when the span positively identifies "
            "a different target value, and NOT_STATED when the component is "
            "merely omitted. Omission is not contradiction. For comparator "
            "and outcome isolation, choose ISOLATED only when separately "
            "attributed, EXPLICITLY_POOLED only when the text explicitly "
            "combines target and non-target groups or outcomes, otherwise "
            "NOT_APPLICABLE_OR_NOT_STATED. Mark whether an independent effect "
            "statement exists and whether its subject unambiguously corefers "
            "to the target. Copy a short exact effect quote when such a "
            "statement exists. Copy a short exact contradiction quote only "
            "for EXPLICITLY_CONTRADICTED or EXPLICITLY_POOLED. Do not return "
            "evidence/context status, a disposition, partition, or effect "
            "label. Runtime validates grounding and owns all mutation."
        ),
        inputs={
            "mechanism": "A18_TERNARY_BOUNDARY_REVIEW",
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
        expected_schema=ternary_boundary_review_schema(
            item=item,
            reviewed_span_ids=reviewed_ids,
            staged_partition=staged_partition,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
