"""Provider task for atomic semantic witness v0.80."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v5_schemas import atomic_witness_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def atomic_witness_task(*, item, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v5-80-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Return atomic semantic facts for every candidate span. Do not "
            "assign object relation, utility, disposition, partition, "
            "admission state, or a final effect label. "
            "exact_target_object_mentioned is true only when the span "
            "addresses the specified intervention, comparator, and outcome. "
            "target_effect_separately_extractable is true when that target "
            "has its own interpretable value, direction, statistical result, "
            "or statement. A target reported beside other outcomes remains "
            "separately extractable; set false only when it appears solely "
            "inside a pooled or composite endpoint whose target component "
            "cannot be isolated. independent_effect_support is true only when "
            "the span can independently support the exact target effect. "
            "Null/no-difference, uncertainty, significance, direction, "
            "magnitude, and quantitative corroboration can qualify. A more "
            "concise sibling does not demote support. When support is false, "
            "use NOT_EFFECT_BEARING as the sole basis and state whether the "
            "span still provides useful non-effect context. Preserve your "
            "facts even when uncertain; Runtime handles conflicts."
        ),
        inputs={
            "mechanism": "A14_ATOMIC_SEMANTIC_WITNESS",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "policy_labels_requested": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=atomic_witness_schema(item=item, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
