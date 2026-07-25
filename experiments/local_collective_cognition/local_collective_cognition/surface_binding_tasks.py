"""Provider task for v0.71 source-surface candidate binding."""

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .surface_binding_schemas import surface_binding_schema


def surface_binding_task(
    *, item, admission, arm_catalog, frame, catalog, adapter
):
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    spans = [
        span for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ]
    return ProviderCognitiveTask(
        task_id=f"surface_binding_v0_71-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Bind semantic roles only to immutable source-surface candidate "
            "IDs. Select a subject candidate that names the group whose value "
            "is described and a relation candidate that states the effect or "
            "absence. Candidates may come from any admitted span in the same "
            "discourse unit. Never paraphrase or create a surface. Use "
            "IMPLICIT_SUBJECT only for an explicit non-comparative absence "
            "statement and then use NO_COMPARATIVE_EFFECT_REPORTED. "
            "Non-significant exact evidence remains usable. Do not predict a "
            "final label."
        ),
        inputs={
            "mechanism": "A7_SURFACE_ID_BINDING",
            "case_id": item["case_id"],
            "object": item["object"],
            "arm_catalog": arm_catalog,
            "relational_frame_receipt": frame,
            "admitted_candidate_spans": spans,
            "surface_candidate_catalog": catalog,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=surface_binding_schema(
            item=item,
            admission=admission,
            arm_catalog=arm_catalog,
            frame=frame,
            catalog=catalog,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
