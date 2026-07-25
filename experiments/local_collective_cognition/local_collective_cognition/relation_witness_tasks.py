"""Provider tasks for v0.69 grounded relation witnesses."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .relation_witness_schemas import (
    witness_basis_schema,
    witness_frame_schema,
)


def witness_frame_task(*, item, admission, catalog, adapter):
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    spans = [
        span for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ]
    return ProviderCognitiveTask(
        task_id=f"relation_witness_v0_69-frame-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Resolve the stable arm IDs exactly as in v0.68, and include every "
            "useful group-name surface appearing verbatim in admitted spans as "
            "an alias for its arm. Canonical object text may also be an alias. "
            "Do not infer an outcome label."
        ),
        inputs={
            "mechanism": "A4_RELATIONAL_FRAME",
            "case_id": item["case_id"],
            "object": item["object"],
            "arm_catalog": catalog,
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=witness_frame_schema(
            item=item,
            admission=admission,
            catalog=catalog,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def witness_basis_task(*, item, admission, catalog, frame, adapter):
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    spans = [
        span for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ]
    return ProviderCognitiveTask(
        task_id=f"relation_witness_v0_69-basis-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Issue one basis record per admitted span. For an explicitly named "
            "group, copy subject_surface and relation_surface verbatim from the "
            "span; subject_surface must be an alias assigned to that arm. Bind "
            "direction to the explicitly quoted subject, not to an inferred "
            "opposite group. Use FRAME_IMPLICIT only when no group is named "
            "and the span reports absence such as 'no adverse effects were "
            "observed'; then use NO_COMPARATIVE_EFFECT_REPORTED, empty "
            "subject_surface, and quote the absence relation. Non-significant "
            "exact evidence remains usable. Do not predict a label."
        ),
        inputs={
            "mechanism": "A5_RELATION_WITNESS_BASIS",
            "case_id": item["case_id"],
            "object": item["object"],
            "arm_catalog": catalog,
            "relational_frame_receipt": frame,
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=witness_basis_schema(
            item=item,
            admission=admission,
            catalog=catalog,
            frame=frame,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
