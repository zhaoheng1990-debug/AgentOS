"""Provider task for grounded context-utility witnesses."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v6_schemas import context_utility_witness_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def context_utility_witness_task(*, item, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v6-81-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Return atomic semantic facts for every candidate span. Do not "
            "assign object relation, disposition, partition, admission state, "
            "or a final effect label. Apply the v0.80 target and independent "
            "effect rules unchanged. For each span also determine whether "
            "non-effect information changes a downstream judgment about the "
            "exact target. Allowed context functions are target identity or "
            "mapping, effect interpretation, scope or applicability, and "
            "evidence validity. General topical similarity, a different "
            "outcome, or background that changes no target judgment is "
            "NO_TARGET_UTILITY. For a real context function set "
            "context_changes_downstream_decision true and copy a short exact "
            "quote from that span into utility_anchor_quote. Otherwise use "
            "NO_TARGET_UTILITY, false, and an empty quote. For independently "
            "effect-bearing spans use NO_TARGET_UTILITY for the context fields "
            "because Runtime gives effect evidence priority. Preserve atomic "
            "facts under uncertainty; Runtime validates grounding and resolves "
            "conflicts."
        ),
        inputs={
            "mechanism": "A15_CONTEXT_UTILITY_WITNESS",
            "case_id": item["case_id"],
            "object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "private_gold_available": False,
            "policy_labels_requested": False,
            "final_label_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=context_utility_witness_schema(
            item=item,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
