"""v0.69 grounded-witness orchestration."""

from __future__ import annotations

from agentos_kernel import ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import call_record, failed_call
from .relation_witness_compiler import compile_witness_basis
from .relation_witness_contracts import (
    validate_witness_basis,
    validate_witness_frame,
)
from .relation_witness_tasks import witness_basis_task, witness_frame_task
from .relational_contrast_objects import arm_catalog


def run_relation_witness_panel(
    *, panel, preregistration, admission_receipts, adapter
):
    commitment = {
        key: value for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if preregistration.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("witness_preregistration_hash_invalid")
    items = panel["public_surface"]["items"]
    calls, catalogs, frames, bases, failures = [], {}, {}, {}, []
    for item in items:
        case_id = item["case_id"]
        admission = admission_receipts[case_id]
        catalog = arm_catalog(item)
        catalogs[case_id] = catalog
        task = witness_frame_task(
            item=item,
            admission=admission,
            catalog=catalog,
            adapter=adapter,
        )
        call, receipt, failure = _invoke(
            "A5_WITNESS_FRAME",
            item,
            task,
            adapter,
            lambda value, current=item, source=admission, arms=catalog: (
                validate_witness_frame(
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
        task = witness_basis_task(
            item=item,
            admission=admission,
            catalog=catalogs[case_id],
            frame=frames[case_id],
            adapter=adapter,
        )
        call, receipt, failure = _invoke(
            "A5_WITNESS_BASIS",
            item,
            task,
            adapter,
            lambda value, current=item, source=admission,
            arms=catalogs[case_id], parsed=frames[case_id]: (
                validate_witness_basis(
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
            receipts[case_id] = compile_witness_basis(
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
    value = {
        "runtime_version": "relation_witness_runtime_v0_69",
        "arm_id": "A5_SPAN_ANCHORED_RELATION_WITNESS",
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
    return {**value, "run_hash": hash_payload(value)}


def _invoke(role, item, task, adapter, validator):
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
