"""Runtime orchestration for ternary boundary review v0.84."""

from __future__ import annotations

from agentos_kernel import ProviderTaskRouter

from .admission_v9_compiler import compile_ternary_boundary_review
from .admission_v9_contracts import validate_ternary_boundary_review
from .admission_v9_tasks import ternary_boundary_review_task
from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)


def run_ternary_boundary_review_panel(
    *,
    panel,
    preregistration,
    staged_run,
    adapter,
):
    _validate_hash(preregistration, "artifact_hash")
    _validate_hash(staged_run, "run_hash")
    if staged_run.get("source_panel_hash") != panel.get("artifact_hash"):
        raise ValueError("admission_v9_staged_run_panel_mismatch")
    calls, receipts, partitions = [], {}, {}
    failures, compiler_failures = [], []
    for item in panel["public_surface"]["items"]:
        case_id = item["case_id"]
        staged_partition = staged_run["partitions"][case_id]
        task = ternary_boundary_review_task(
            item=item,
            staged_partition=staged_partition,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record(
            "A18_TERNARY_BOUNDARY_REVIEW",
            case_id,
            task,
            envelope,
        )
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_ternary_boundary_review(
            receipt=receipt,
            item=item,
            staged_partition=staged_partition,
            refs=evidence_refs(item),
        )
        if contract_failures:
            failures.append({
                **call,
                "contract_failures": contract_failures,
                "invalid_receipt": receipt,
            })
            continue
        receipts[case_id] = receipt
        try:
            partitions[case_id] = compile_ternary_boundary_review(
                item=item,
                staged_partition=staged_partition,
                receipt=receipt,
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": case_id,
                "contract_failures": [str(error)],
            })
    value = {
        "runtime_version": "ternary_boundary_review_runtime_v0_84",
        "arm_id": "A18_TERNARY_BOUNDARY_REVIEW",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_staged_run_hash": staged_run["run_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "partitions": partitions,
        "contract_failures": failures,
        "compiler_failures": compiler_failures,
        "private_gold_exposed": False,
        "upstream_dispositions_exposed_to_provider": False,
        "provider_policy_authority": False,
        "predicted_label_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}


def _validate_hash(value, field):
    commitment = {
        key: item for key, item in value.items() if key != field
    }
    if value.get(field) != hash_payload(commitment):
        raise ValueError(f"admission_v9_{field}_invalid")
