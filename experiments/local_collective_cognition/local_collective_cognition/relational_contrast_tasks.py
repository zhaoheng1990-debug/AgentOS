"""Provider tasks for the v0.68 relational contrast chain."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .relational_contrast_schemas import (
    relational_basis_schema,
    relational_frame_schema,
)


RUNTIME_VERSION = "relational_contrast_v0_68"


def relational_frame_task(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-frame-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Resolve the focal relation using the immutable local arm IDs. "
            "FOCAL_INTERVENTION always denotes the full intervention object, "
            "including a compound or grouped intervention. FOCAL_COMPARATOR "
            "always denotes the comparator object, including baseline. Supply "
            "passage aliases for both IDs; aliases need not equal canonical "
            "display strings. Use WITHIN_GROUP_VS_BASELINE when the outcome is "
            "post-treatment versus baseline within the focal group. A query "
            "that does not name a timepoint or measurement is UNCONSTRAINED. "
            "Do not predict an outcome label."
        ),
        inputs={
            "mechanism": "A4_RELATIONAL_FRAME",
            "case_id": item["case_id"],
            "object": item["object"],
            "arm_catalog": catalog,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=relational_frame_schema(
            item=item,
            admission=admission,
            catalog=catalog,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def relational_basis_task(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    catalog: dict[str, Any],
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
            "Issue one relational basis record per admitted span. "
            "subject_group_id is the group whose outcome value is described; "
            "reference_group_id is the group or baseline it is compared with. "
            "Ignore grammatical mention order. Example: 'intervention lower "
            "than control' means subject FOCAL_INTERVENTION, reference "
            "FOCAL_COMPARATOR, SUBJECT_LOWER. 'control higher than "
            "intervention' means subject FOCAL_COMPARATOR, reference "
            "FOCAL_INTERVENTION, SUBJECT_HIGHER. For within-group change, use "
            "subject FOCAL_INTERVENTION and reference WITHIN_GROUP_BASELINE. "
            "Non-significant or borderline exact evidence remains DECISIVE or "
            "SUPPORTING because it can establish NO_DIFFERENCE; never exclude "
            "a span merely because its effect is non-significant. Exclude only "
            "object-, relation-, timepoint-, or measurement-incompatible "
            "evidence. Do not predict a final label."
        ),
        inputs={
            "mechanism": "A4_RELATIONAL_BASIS",
            "case_id": item["case_id"],
            "object": item["object"],
            "arm_catalog": catalog,
            "relational_frame_receipt": frame,
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "source_frame_hash": hash_payload(frame),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=relational_basis_schema(
            item=item,
            admission=admission,
            catalog=catalog,
            frame=frame,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
