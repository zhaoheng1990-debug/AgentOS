"""Provider task for minimal semantic witness v0.79."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v4_schemas import minimal_witness_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def minimal_witness_task(*, item, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v4-79-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "For every candidate span, return only independent semantic "
            "facts; do not assign object relation, utility, disposition, "
            "partition, admission state, or final effect label. Determine "
            "whether the target outcome is separately reported, appears only "
            "as a component of a non-separable composite, is a related "
            "outcome only, or is absent. A list of outcomes is not a "
            "composite when the target has its own separately interpretable "
            "value or statement. Mark independent_effect_support true only "
            "when the span can independently support the exact target effect. "
            "Increased, decreased, null/no-difference, uncertainty, "
            "significance, magnitude, and quantitative corroboration can all "
            "qualify. A more concise sibling does not demote valid support. "
            "When support is false, use NOT_EFFECT_BEARING as the sole effect "
            "basis and state whether the span still provides useful context "
            "for interpreting the target."
        ),
        inputs={
            "mechanism": "A13_MINIMAL_SEMANTIC_WITNESS",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "policy_labels_requested": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=minimal_witness_schema(item=item, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
