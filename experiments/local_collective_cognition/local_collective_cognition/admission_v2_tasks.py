"""Provider task for typed evidence admission v0.76."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v2_schemas import typed_admission_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def typed_admission_task(*, item, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission_v2_76-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Assess every candidate span on three separate axes. "
            "object_relation asks whether the span addresses the exact "
            "intervention-comparator-outcome object, only its context, or a "
            "different object. evidence_utility asks whether it can support "
            "the target effect judgment, supplies context only, or supplies "
            "neither. disposition must be ADMIT_EVIDENCE for effect-bearing "
            "exact-object spans, RETAIN_CONTEXT for useful non-effect context, "
            "and REJECT for no utility. If no span is effect-bearing, return "
            "NO_APPLICABLE_EVIDENCE rather than forcing an admission. Do not "
            "predict an outcome label."
        ),
        inputs={
            "mechanism": "A11_TYPED_EVIDENCE_ADMISSION",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=typed_admission_schema(item=item, refs=refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
