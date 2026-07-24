"""Two-stage Provider orchestration for v0.66."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)
from .semantic_basis_consistency import semantic_consistency_failures
from .semantic_basis_contracts import (
    validate_semantic_basis,
    validate_synthesis,
)
from .semantic_basis_tasks import basis_task, synthesis_task


def run_semantic_basis_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    admission_receipts: dict[str, dict[str, Any]],
    adapter: Any,
) -> dict[str, Any]:
    _validate_hash(preregistration)
    items = panel["public_surface"]["items"]
    case_ids = {item["case_id"] for item in items}
    if set(admission_receipts) != case_ids:
        raise ValueError("semantic_basis_admission_surface_invalid")
    basis_calls: list[dict[str, Any]] = []
    basis_receipts: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, Any]] = []
    for item in items:
        admission = admission_receipts[item["case_id"]]
        task = basis_task(
            item=item, admission=admission, adapter=adapter
        )
        call, receipt, failure = _invoke(
            role="A2_SEMANTIC_BASIS",
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value, current=item, source=admission: (
                validate_semantic_basis(
                    receipt=value,
                    item=current,
                    admission=source,
                    refs=evidence_refs(current),
                )
            ),
        )
        basis_calls.append(call)
        if failure:
            failures.append(failure)
        else:
            basis_receipts[item["case_id"]] = receipt

    synthesis_calls: list[dict[str, Any]] = []
    receipts: dict[str, dict[str, Any]] = {}
    consistency_failures: list[dict[str, Any]] = []
    for item in items:
        case_id = item["case_id"]
        admission = admission_receipts[case_id]
        basis = basis_receipts.get(case_id)
        if basis is None:
            continue
        task = synthesis_task(
            item=item,
            admission=admission,
            basis=basis,
            adapter=adapter,
        )
        call, receipt, failure = _invoke(
            role="A2_SEMANTIC_SYNTHESIS",
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value, current=item, source=admission, typed=basis: (
                validate_synthesis(
                    receipt=value,
                    item=current,
                    admission=source,
                    basis=typed,
                    refs=evidence_refs(current),
                )
            ),
        )
        synthesis_calls.append(call)
        if failure:
            failures.append(failure)
            continue
        semantic_failures = semantic_consistency_failures(
            basis=basis, synthesis=receipt
        )
        if semantic_failures:
            consistency_failures.append({
                **call,
                "contract_failures": semantic_failures,
                "invalid_receipt": receipt,
            })
            continue
        receipts[case_id] = receipt
    commitment = {
        "runtime_version": "semantic_basis_runtime_v0_66",
        "arm_id": "A2_TYPED_SEMANTIC_BASIS",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": [*basis_calls, *synthesis_calls],
        "basis_receipts": basis_receipts,
        "receipts": receipts,
        "contract_failures": failures,
        "semantic_consistency_failures": consistency_failures,
        "private_gold_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _invoke(
    *,
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
        raise ValueError("semantic_basis_preregistration_hash_invalid")
