"""Runtime composition of frozen A14 evidence and A16 context utility."""

from __future__ import annotations

from agentos_kernel import ProviderTaskRouter

from .admission_v7_compiler import compile_context_addon
from .admission_v7_contracts import validate_context_addon
from .admission_v7_tasks import context_addon_task
from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)


def run_staged_context_addon_panel(
    *,
    panel,
    preregistration,
    atomic_run,
    adapter,
):
    _validate_hash(preregistration, "artifact_hash")
    _validate_hash(atomic_run, "run_hash")
    if atomic_run.get("source_panel_hash") != panel.get("artifact_hash"):
        raise ValueError("admission_v7_atomic_run_panel_mismatch")
    calls, receipts, partitions = [], {}, {}
    failures, compiler_failures = [], []
    for item in panel["public_surface"]["items"]:
        case_id = item["case_id"]
        atomic_receipt = atomic_run["receipts"][case_id]
        atomic_partition = atomic_run["partitions"][case_id]
        task = context_addon_task(
            item=item,
            atomic_receipt=atomic_receipt,
            atomic_partition=atomic_partition,
            adapter=adapter,
        )
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record(
            "A16_STAGED_CONTEXT_UTILITY_ADDON",
            case_id,
            task,
            envelope,
        )
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_context_addon(
            receipt=receipt,
            item=item,
            atomic_receipt=atomic_receipt,
            atomic_partition=atomic_partition,
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
            partitions[case_id] = compile_context_addon(
                item=item,
                atomic_receipt=atomic_receipt,
                atomic_partition=atomic_partition,
                receipt=receipt,
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": case_id,
                "contract_failures": [str(error)],
            })
    value = {
        "runtime_version": "staged_context_addon_runtime_v0_82",
        "arm_id": "A16_STAGED_CONTEXT_UTILITY_ADDON",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_atomic_run_hash": atomic_run["run_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "partitions": partitions,
        "contract_failures": failures,
        "compiler_failures": compiler_failures,
        "private_gold_exposed": False,
        "provider_effect_rejudgment_authority": False,
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
        raise ValueError(f"admission_v7_{field}_invalid")
