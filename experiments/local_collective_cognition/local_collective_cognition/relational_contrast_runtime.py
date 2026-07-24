"""Provider-backed relational parsing with local label authority."""

from __future__ import annotations

from typing import Any, Callable

from agentos_kernel import ProviderCognitiveTask, ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import call_record, failed_call
from .relational_basis_compiler import compile_relational_basis
from .relational_contrast_contracts import (
    validate_relational_basis,
    validate_relational_frame,
)
from .relational_contrast_objects import arm_catalog
from .relational_contrast_tasks import (
    relational_basis_task,
    relational_frame_task,
)


def run_relational_contrast_panel(
    *,
    panel: dict[str, Any],
    preregistration: dict[str, Any],
    admission_receipts: dict[str, dict[str, Any]],
    adapter: Any,
) -> dict[str, Any]:
    _validate_hash(preregistration)
    items = panel["public_surface"]["items"]
    if set(admission_receipts) != {item["case_id"] for item in items}:
        raise ValueError("relational_admission_surface_invalid")
    calls, catalogs, frames, bases = [], {}, {}, {}
    failures: list[dict[str, Any]] = []
    for item in items:
        case_id = item["case_id"]
        admission = admission_receipts[case_id]
        catalog = arm_catalog(item)
        catalogs[case_id] = catalog
        task = relational_frame_task(
            item=item,
            admission=admission,
            catalog=catalog,
            adapter=adapter,
        )
        call, receipt, failure = _invoke(
            "A4_RELATIONAL_FRAME", item, task, adapter,
            lambda value, current=item, source=admission, arms=catalog: (
                validate_relational_frame(
                    receipt=value,
                    item=current,
                    admission=source,
                    catalog=arms,
                    refs=evidence_refs(current),
                )
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            frames[case_id] = receipt
    for item in items:
        case_id = item["case_id"]
        if case_id not in frames:
            continue
        admission = admission_receipts[case_id]
        task = relational_basis_task(
            item=item,
            admission=admission,
            catalog=catalogs[case_id],
            frame=frames[case_id],
            adapter=adapter,
        )
        call, receipt, failure = _invoke(
            "A4_RELATIONAL_BASIS", item, task, adapter,
            lambda value, current=item, source=admission,
            arms=catalogs[case_id], parsed=frames[case_id]: (
                validate_relational_basis(
                    receipt=value,
                    item=current,
                    admission=source,
                    catalog=arms,
                    frame=parsed,
                    refs=evidence_refs(current),
                )
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            bases[case_id] = receipt
    receipts, compiler_failures = {}, []
    for item in items:
        case_id = item["case_id"]
        if case_id not in frames or case_id not in bases:
            continue
        try:
            receipts[case_id] = compile_relational_basis(
                item=item,
                admission=admission_receipts[case_id],
                catalog=catalogs[case_id],
                frame=frames[case_id],
                basis=bases[case_id],
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": case_id,
                "contract_failures": [str(error)],
            })
    commitment = {
        "runtime_version": "relational_contrast_runtime_v0_68",
        "arm_id": "A4_EXPLICIT_RELATIONAL_CONTRAST",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "arm_catalogs": catalogs,
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
        raise ValueError("relational_preregistration_hash_invalid")
