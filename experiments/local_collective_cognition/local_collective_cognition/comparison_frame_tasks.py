"""Provider tasks for the v0.67 frame-bound cognition chain."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .comparison_frame_schemas import (
    comparison_frame_schema,
    frame_basis_schema,
)


RUNTIME_VERSION = "comparison_frame_v0_67"


def comparison_frame_task(
    *, item: dict[str, Any], admission: dict[str, Any], adapter: Any
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-frame-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Construct the comparison frame before interpreting outcome "
            "evidence. Expand compound intervention strings into study arms; "
            "bind the focal intervention member or group against the stated "
            "comparator. Use WITHIN_GROUP_VS_BASELINE when post-treatment is "
            "compared with baseline within every named arm. A query that does "
            "not state a timepoint or measurement is UNCONSTRAINED, so an "
            "explicit passage value is allowed rather than different. Use "
            "EXACT only when the query itself names the coordinate. Mark the "
            "frame unresolved only for material arm or contrast ambiguity. "
            "Do not predict an outcome label."
        ),
        inputs={
            "mechanism": "A3_COMPARISON_FRAME",
            "case_id": item["case_id"],
            "object": item["object"],
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=comparison_frame_schema(
            item=item, admission=admission, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def frame_basis_task(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    frame: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    admitted_set = set(admitted)
    spans = [
        span for span in item["candidate_spans"]
        if span["span_id"] in admitted_set
    ]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-basis-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Apply the supplied comparison frame to every admitted span. "
            "Record the outcome, focal contrast, timepoint, measurement, "
            "sentence orientation, direction as written, and significance. "
            "For an UNCONSTRAINED frame coordinate, use "
            "ALLOWED_BY_UNCONSTRAINED when a passage names one. Comparator-"
            "first language remains COMPARATOR_VS_INTERVENTION; do not "
            "normalize its direction yourself. A p value >=0.05, a confidence "
            "interval including the null, or trend/borderline wording is not "
            "SIGNIFICANT. Reject spans with incompatible key coordinates. "
            "Do not predict or recommend a final label."
        ),
        inputs={
            "mechanism": "A3_FRAME_BOUND_BASIS",
            "case_id": item["case_id"],
            "object": item["object"],
            "comparison_frame_receipt": frame,
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "source_frame_hash": hash_payload(frame),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=frame_basis_schema(
            item=item,
            admission=admission,
            frame=frame,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
