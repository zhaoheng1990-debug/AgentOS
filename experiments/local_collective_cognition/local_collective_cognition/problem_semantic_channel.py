"""Semantic channel identities that exclude non-cognitive lineage noise."""

from __future__ import annotations

from .provider_telemetry import hash_payload


def problem_semantic_channel_hash(task, context):
    if context.get("role") != "contrastive_problem_reviser":
        return hash_payload({"task": task.contract_hash(), "role": context["role"]})
    return hash_payload({
        "task_id": task.task_id, "task_kind": task.task_kind,
        "objective": task.objective,
        "benchmark_public_input": task.inputs["benchmark_public_input"],
        "benchmark_item_ids": task.inputs["benchmark_item_ids"],
        "role": context["role"],
        "problem_candidate_id": context["problem_candidate_id"],
        "contrastive_structure_packet": context["contrastive_structure_packet"],
    })


def quality_semantic_channel_hash(task, context):
    return hash_payload({
        "task_id": task.task_id, "task_kind": task.task_kind,
        "objective": task.objective,
        "benchmark_public_input": task.inputs["benchmark_public_input"],
        "benchmark_item_ids": task.inputs["benchmark_item_ids"],
        "role": context["role"],
        "contrastive_structure_packet": context["contrastive_structure_packet"],
    })
