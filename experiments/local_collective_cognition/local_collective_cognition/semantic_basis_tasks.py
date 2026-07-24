"""Provider tasks for the v0.66 typed semantic-basis chain."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import admission_partition
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload
from .semantic_basis_schemas import (
    semantic_basis_schema,
    synthesis_schema,
)


RUNTIME_VERSION = "typed_semantic_basis_v0_66"


def basis_task(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    spans = [
        span
        for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-basis-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Issue exactly one typed semantic-basis record for every admitted "
            "span. Bind the exact outcome, requested timepoint, measurement "
            "method, and whether the sentence states intervention versus "
            "comparator or comparator versus intervention. Record the "
            "direction exactly as written before normalization. Treat "
            "p >= 0.05, a confidence interval including the null, and words "
            "such as trend or borderline as non-significant or borderline, "
            "not as a significant effect. Mark alternative measurements, "
            "timepoints, and mixed effects as ambiguity axes. Do not predict "
            "the final outcome label."
        ),
        inputs={
            "mechanism": "A2_SEMANTIC_BASIS",
            "case_id": item["case_id"],
            "object": item["object"],
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=semantic_basis_schema(
            item=item, admission=admission, refs=refs
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def synthesis_task(
    *,
    item: dict[str, Any],
    admission: dict[str, Any],
    basis: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    admitted, _ = admission_partition(admission)
    spans = [
        span
        for span in item["candidate_spans"]
        if span["span_id"] in set(admitted)
    ]
    return ProviderCognitiveTask(
        task_id=f"{RUNTIME_VERSION}-synthesis-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Synthesize the final outcome only from the complete typed basis. "
            "Normalize comparator-first statements before selecting direction. "
            "A trend, borderline result, p >= 0.05, or confidence interval "
            "including the null cannot by itself support INCREASED or "
            "DECREASED. Partition every admitted span exactly once. Use "
            "UNRESOLVED_MATERIAL_AMBIGUITY when incompatible timepoints, "
            "measurements, or effects prevent one answer to the exact object; "
            "do not force a benchmark label. Map DECISIVE basis records to "
            "primary, SUPPORTING to corroborating, COUNTER to counter, and "
            "REJECT_AFTER_BASIS to rejected-after-basis."
        ),
        inputs={
            "mechanism": "A2_SEMANTIC_SYNTHESIS",
            "case_id": item["case_id"],
            "object": item["object"],
            "admitted_candidate_spans": spans,
            "admission_receipt": admission,
            "semantic_basis_receipt": basis,
            "source_basis_hash": hash_payload(basis),
            "private_gold_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=synthesis_schema(
            item=item,
            admission=admission,
            basis=basis,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
