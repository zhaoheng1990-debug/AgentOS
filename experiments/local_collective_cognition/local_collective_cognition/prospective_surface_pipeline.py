"""Reusable prospective frame-to-compiler experiment pipeline."""

from __future__ import annotations

from agentos_kernel import ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .coordinate_projection_replay import project_basis
from .provider_telemetry import hash_payload
from .relation_witness_tasks import witness_frame_task
from .relational_contrast_objects import arm_catalog
from .selection_retention_fresh_provider_helpers import (
    call_record,
    failed_call,
)
from .surface_binding_compiler import compile_surface_binding
from .surface_binding_contracts import validate_surface_binding
from .surface_binding_tasks import surface_binding_task
from .surface_candidate_catalog import build_surface_catalog


def run_surface_pipeline(
    *,
    panel,
    preregistration,
    admission_receipts,
    adapter,
    runtime_version,
    arm_id,
    frame_metadata_factory,
    frame_validator,
):
    _validate_hash(preregistration)
    items = panel["public_surface"]["items"]
    calls, arm_catalogs, frame_metadata, frames = [], {}, {}, {}
    catalogs, bases, projected_bases, projections, receipts = (
        {},
        {},
        {},
        {},
        {},
    )
    failures, compiler_failures = [], []
    for item in items:
        case_id = item["case_id"]
        admission = admission_receipts[case_id]
        arms = arm_catalog(item)
        metadata = frame_metadata_factory(arms)
        arm_catalogs[case_id] = arms
        frame_metadata[case_id] = metadata
        task = witness_frame_task(
            item=item,
            admission=admission,
            catalog=arms,
            adapter=adapter,
        )
        call, frame, failure = _invoke(
            role="A10_GROUPED_ALIAS_FRAME",
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value, current=item, source=admission,
            catalog=arms, context=metadata: frame_validator(
                receipt=value,
                item=current,
                admission=source,
                catalog=catalog,
                refs=evidence_refs(current),
                alias_catalog=context,
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
        else:
            frames[case_id] = frame
    for item in items:
        case_id = item["case_id"]
        if case_id not in frames:
            continue
        admission = admission_receipts[case_id]
        catalog = build_surface_catalog(item=item, admission=admission)
        catalogs[case_id] = catalog
        task = surface_binding_task(
            item=item,
            admission=admission,
            arm_catalog=arm_catalogs[case_id],
            frame=frames[case_id],
            catalog=catalog,
            adapter=adapter,
        )
        call, basis, failure = _invoke(
            role="A10_GROUPED_ALIAS_SURFACE_BINDING",
            item=item,
            task=task,
            adapter=adapter,
            validator=lambda value, current=item, source=admission,
            arms=arm_catalogs[case_id], frame=frames[case_id],
            surfaces=catalog: validate_surface_binding(
                receipt=value,
                item=current,
                admission=source,
                arm_catalog=arms,
                frame=frame,
                catalog=surfaces,
                refs=evidence_refs(current),
            ),
        )
        calls.append(call)
        if failure:
            failures.append(failure)
            continue
        bases[case_id] = basis
        projected, projection = project_basis(
            case_id=case_id,
            frame=frames[case_id],
            basis=basis,
        )
        projected_bases[case_id] = projected
        projections[case_id] = projection
        try:
            receipts[case_id] = compile_surface_binding(
                item=item,
                admission=admission,
                arm_catalog=arm_catalogs[case_id],
                frame=frames[case_id],
                catalog=catalog,
                basis=projected,
                refs=evidence_refs(item),
            )
        except ValueError as error:
            compiler_failures.append({
                "case_id": case_id,
                "contract_failures": [str(error)],
            })
    value = {
        "runtime_version": runtime_version,
        "arm_id": arm_id,
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": calls,
        "arm_catalogs": arm_catalogs,
        "frame_validation_metadata": frame_metadata,
        "frame_receipts": frames,
        "surface_catalogs": catalogs,
        "basis_receipts": bases,
        "projected_basis_receipts": projected_bases,
        "projection_receipts": projections,
        "receipts": receipts,
        "contract_failures": failures,
        "compiler_failures": compiler_failures,
        "private_gold_exposed": False,
        "provider_compiler_override_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}


def _invoke(*, role, item, task, adapter, validator):
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


def _validate_hash(value):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("surface_pipeline_preregistration_hash_invalid")
