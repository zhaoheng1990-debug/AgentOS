"""Provider task for witness-backed admission v0.78."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v3_schemas import witness_admission_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def witness_admission_task(*, item, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v3-78-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Assess every candidate span independently before any outcome "
            "classification. First identify whether the exact target outcome "
            "is separately reported, appears only inside a non-separable "
            "composite, is merely related, or is absent. Containment in a "
            "composite is not separable evidence for the target component. "
            "Then decide whether the span independently supports the exact "
            "target effect. Increased, decreased, null/no-difference, "
            "uncertainty, significance, magnitude, and quantitative "
            "corroboration may all be effect-bearing; a more concise sibling "
            "does not demote valid support. Use NOT_EFFECT_BEARING as the sole "
            "basis when independent support is false. Keep useful related "
            "material as context and reject material with no target utility. "
            "Do not predict a final outcome label."
        ),
        inputs={
            "mechanism": "A12_WITNESS_BACKED_ADMISSION",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=witness_admission_schema(
            item=item,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
