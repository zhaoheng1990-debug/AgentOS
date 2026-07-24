"""Provider cognitive tasks for the v0.65 benchmark bridge."""

from __future__ import annotations

from typing import Any

from agentos_kernel import ProviderCognitiveTask

from .benchmark_bridge_contracts import (
    admission_partition,
    admission_schema,
    one_pass_schema,
    staged_binding_schema,
)
from .evidence_inference_bridge import BRIDGE_VERSION
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def evidence_refs(item: dict[str, Any]) -> tuple[str, ...]:
    return (
        "benchmark://evidence-inference/"
        f"pmc/{item['source_pmcid']}/prompt/{item['source_prompt_id']}",
    )


def one_pass_task(item: dict[str, Any], adapter: Any) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"{BRIDGE_VERSION}-a0-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Infer the effect of the intervention versus comparator on the "
            "specified outcome. In one pass, partition every candidate span "
            "exactly once as primary, corroborating, counter, or irrelevant. "
            "Primary is the minimal direct rationale sufficient for the "
            "label. Corroborating adds support, counter genuinely pushes "
            "against the selected label, and irrelevant does not answer this "
            "PICO object. Do not use outside knowledge."
        ),
        inputs={
            "mechanism": "A0_ONE_PASS",
            "public_item": item,
            "private_gold_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=one_pass_schema(item, refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def admission_task(item: dict[str, Any], adapter: Any) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"{BRIDGE_VERSION}-a1-admit-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Before classifying any effect, assess every candidate passage "
            "against the exact intervention-comparator-outcome object. ADMIT "
            "a passage only when it directly answers the object or provides "
            "context needed to interpret such an answer. REJECT passages "
            "about a different outcome, comparison, or question, even when "
            "they contain statistical language. Do not predict the final "
            "effect label in this receipt."
        ),
        inputs={
            "mechanism": "A1_SPAN_ADMISSION",
            "public_item": item,
            "private_gold_available": False,
            "effect_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=admission_schema(item, refs),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )


def staged_binding_task(
    item: dict[str, Any],
    admission: dict[str, Any],
    adapter: Any,
) -> ProviderCognitiveTask:
    refs = evidence_refs(item)
    admitted_ids, rejected_ids = admission_partition(admission)
    admitted = [
        span
        for span in item["candidate_spans"]
        if span["span_id"] in set(admitted_ids)
    ]
    admission_hash = hash_payload(admission)
    return ProviderCognitiveTask(
        task_id=f"{BRIDGE_VERSION}-a1-bind-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Using only the previously admitted passages, infer the effect "
            "of the intervention versus comparator on the specified outcome. "
            "Partition every admitted span exactly once as primary, "
            "corroborating, or counter. Primary is the minimal sufficient "
            "rationale. Replay the rejected IDs exactly; never promote them."
        ),
        inputs={
            "mechanism": "A1_STAGED_BINDING",
            "case_id": item["case_id"],
            "object": item["object"],
            "admitted_candidate_spans": admitted,
            "admission_receipt": admission,
            "source_admission_hash": admission_hash,
            "private_gold_available": False,
        },
        allowed_evidence=list(refs),
        expected_schema=staged_binding_schema(
            item=item,
            admitted_ids=admitted_ids,
            rejected_ids=rejected_ids,
            admission_hash=admission_hash,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
