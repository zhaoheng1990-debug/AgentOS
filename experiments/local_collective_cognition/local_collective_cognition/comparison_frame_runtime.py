"""Modular Provider orchestration and local compilation for v0.67."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import call_record, failed_call
from .comparison_frame_contracts import (
    validate_comparison_frame,
    validate_frame_basis,
)
from .comparison_frame_tasks import comparison_frame_task, frame_basis_task
from .deterministic_basis_compiler import compile_basis


def run_comparison_frame_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    admission_receipts: dict[str, dict[str, Any]],
    adapter: Any,
) -> dict[str, Any]:
    _validate_hash(preregistration)
    items = panel["public_surface"]["items"]
    if set(admission_receipts) != {item["case_id"] for item in items}:
        raise ValueError("comparison_frame_admission_surface_invalid")
    frame_calls, frames, failures = _run_frames(
        items, admission_receipts, adapter
    )
    basis_calls, bases, basis_failures = _run_bases(
        items, admission_receipts, frames, adapter
    )
    failures.extend(basis_failures)
    receipts: dict[str, dict[str, Any]] = {}
    compiler_failures: list[dict[str, Any]] = []
    for item in items:
        case_id = item["case_id"]
        if case_id not in frames or case_id not in bases:
            continue
        try:
            receipts[case_id] = compile_basis(
                item=item,
                admission=admission_receipts[case_id],
                frame=frames[case_id],
                basis=bases[case_id],
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": case_id,
                "contract_failures": [str(error)],
            })
    commitment = {
        "runtime_version": "comparison_frame_runtime_v0_67",
        "arm_id": "A3_FRAME_BOUND_DETERMINISTIC_COMPILER",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": [*frame_calls, *basis_calls],
        "frame_receipts": frames,
        "basis_receipts": bases,
        "receipts": receipts,
        "contract_failures": failures,
        "compiler_failures": compiler_failures,
        "private_gold_exposed": False,
        "provider_compiler_override_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _run_frames(items, admissions, adapter):
    calls, receipts, failures = [], {}, []
    for item in items:
        admission = admissions[item["case_id"]]
        task = comparison_frame_task(
            item=item, admission=admission, adapter=adapter
        )
        call, receipt, failure = _invoke(
            "A3_COMPARISON_FRAME",
            item,
            task,
            adapter,
            lambda value, current=item, source=admission: (
                validate_comparison_frame(
                    receipt=value,
                    item=current,
                    admission=source,
                    refs=evidence_refs(current),
                )
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            receipts[item["case_id"]] = receipt
    return calls, receipts, failures


def _run_bases(items, admissions, frames, adapter):
    calls, receipts, failures = [], {}, []
    for item in items:
        case_id = item["case_id"]
        frame = frames.get(case_id)
        if frame is None:
            continue
        admission = admissions[case_id]
        task = frame_basis_task(
            item=item, admission=admission, frame=frame, adapter=adapter
        )
        call, receipt, failure = _invoke(
            "A3_FRAME_BOUND_BASIS",
            item,
            task,
            adapter,
            lambda value, current=item, source=admission, parsed=frame: (
                validate_frame_basis(
                    receipt=value,
                    item=current,
                    admission=source,
                    frame=parsed,
                    refs=evidence_refs(current),
                )
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            receipts[case_id] = receipt
    return calls, receipts, failures


def _invoke(
    role: str,
    item: dict[str, Any],
    task: ProviderCognitiveTask,
    adapter: Any,
    validator: Callable[[dict[str, Any]], list[str]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any] | None]:
    envelope = ProviderTaskRouter([adapter]).route(task)
    call = call_record(role, item["case_id"], task, envelope)
    if envelope.status != "COMPLETED":
        return call, {}, failed_call(call, envelope)
    receipt = envelope.normalized_result
    failures = validator(receipt)
    if failures:
        return call, receipt, {
            **call,
            "contract_failures": failures,
            "invalid_receipt": receipt,
        }
    return call, receipt, None


def _validate_hash(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("comparison_frame_preregistration_hash_invalid")
