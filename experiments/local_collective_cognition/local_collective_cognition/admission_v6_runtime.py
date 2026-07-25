"""Provider-backed runtime for context-utility witness admission."""

from __future__ import annotations

from agentos_kernel import ProviderTaskRouter

from .admission_v6_compiler import compile_context_utility_witness
from .admission_v6_contracts import validate_context_utility_witness
from .admission_v6_tasks import context_utility_witness_task
from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)


def run_context_utility_witness_panel(
    *,
    panel,
    preregistration,
    preflight_amendment,
    adapter,
):
    _validate_hash(preregistration)
    _validate_hash(preflight_amendment)
    calls, receipts, partitions = [], {}, {}
    failures, compiler_failures = [], []
    for item in panel["public_surface"]["items"]:
        task = context_utility_witness_task(item=item, adapter=adapter)
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record(
            "A15_CONTEXT_UTILITY_WITNESS",
            item["case_id"],
            task,
            envelope,
        )
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        receipt = envelope.normalized_result
        contract_failures = validate_context_utility_witness(
            receipt=receipt,
            item=item,
            refs=evidence_refs(item),
        )
        if contract_failures:
            failures.append({
                **call,
                "contract_failures": contract_failures,
                "invalid_receipt": receipt,
            })
            continue
        receipts[item["case_id"]] = receipt
        try:
            partitions[item["case_id"]] = (
                compile_context_utility_witness(
                    item=item,
                    receipt=receipt,
                )
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": item["case_id"],
                "contract_failures": [str(error)],
            })
    value = {
        "runtime_version": "context_utility_witness_runtime_v0_81",
        "arm_id": "A15_CONTEXT_UTILITY_WITNESS",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_preflight_amendment_hash": (
            preflight_amendment["artifact_hash"]
        ),
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "receipts": receipts,
        "partitions": partitions,
        "contract_failures": failures,
        "compiler_failures": compiler_failures,
        "private_gold_exposed": False,
        "provider_policy_authority": False,
        "predicted_label_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}


def _validate_hash(value):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("admission_v6_preregistration_hash_invalid")
