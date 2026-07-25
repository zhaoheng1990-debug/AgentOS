"""Provider task for case-level study-relation review."""

from __future__ import annotations

from agentos_kernel import ProviderCognitiveTask

from .admission_v10_schemas import study_relation_schema
from .benchmark_bridge_tasks import evidence_refs
from .frontier_experiment import TASK_KIND
from .provider_telemetry import hash_payload


def study_relation_task(*, item, staged_partition, adapter):
    refs = evidence_refs(item)
    return ProviderCognitiveTask(
        task_id=f"admission-v10-85-{item['case_id']}",
        task_kind=TASK_KIND,
        objective=(
            "Build one case-level study relation graph before assessing each "
            "span. Identify exact surface aliases for target intervention, "
            "target comparator, their joint/coreferential contrast, target "
            "outcome, composite outcomes containing the target, related "
            "outcomes, and explicit non-target arms. Ground every binding in "
            "an exact quote from the supplied spans. Each span must reference "
            "the graph bindings it relies on. Distinguish a DIRECT_ARM_"
            "COMPARISON from a NONSEPARABLE_AGGREGATE: naming or comparing "
            "both target arms is not pooling. Distinguish EXACT_TARGET_OUTCOME "
            "from COMPOSITE_CONTAINS_TARGET and RELATED_OUTCOME. Use "
            "INDEPENDENT_COMPARATIVE_EFFECT only when the span can support the "
            "target effect by itself; otherwise use TARGET_RELATED_CONTEXT or "
            "NO_EFFECT_STATEMENT. Copy exact, contiguous source quotes; never "
            "use ellipses or normalized substitutions. Upstream dispositions "
            "are hidden. Do not return evidence, context, reject, disposition, "
            "partition, or an effect label. Kernel owns all mutations."
        ),
        inputs={
            "mechanism": "A19_STUDY_RELATION_REVIEW",
            "case_id": item["case_id"],
            "target_object": item["object"],
            "candidate_spans": item["candidate_spans"],
            "source_item_hash": hash_payload(item),
            "source_staged_partition_hash": (
                staged_partition["partition_hash"]
            ),
            "upstream_dispositions_exposed": False,
            "private_gold_available": False,
            "policy_labels_requested": False,
        },
        allowed_evidence=list(refs),
        expected_schema=study_relation_schema(
            item=item,
            staged_partition=staged_partition,
            refs=refs,
        ),
        timeout_seconds=min(600, adapter.profile.max_timeout_seconds),
        failure_semantics="preserve_failure",
    )
