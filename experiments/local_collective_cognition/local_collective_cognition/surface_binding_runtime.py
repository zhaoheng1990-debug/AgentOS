"""v0.71 one-stage Provider binding with local compilation."""

from agentos_kernel import ProviderTaskRouter

from .benchmark_bridge_tasks import evidence_refs
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import call_record, failed_call
from .surface_binding_compiler import compile_surface_binding
from .surface_binding_contracts import validate_surface_binding
from .surface_binding_tasks import surface_binding_task
from .surface_candidate_catalog import build_surface_catalog


def run_surface_binding_panel(
    *, panel, preregistration, admission_receipts, source_frame_run, adapter
):
    items = panel["public_surface"]["items"]
    frames = source_frame_run["frame_receipts"]
    arm_catalogs = source_frame_run["arm_catalogs"]
    calls, catalogs, bases, receipts, failures = [], {}, {}, {}, []
    for item in items:
        case_id = item["case_id"]
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
        envelope = ProviderTaskRouter([adapter]).route(task)
        call = call_record("A7_SURFACE_ID_BINDING", case_id, task, envelope)
        calls.append(call)
        if envelope.status != "COMPLETED":
            failures.append(failed_call(call, envelope))
            continue
        basis = envelope.normalized_result
        contract = validate_surface_binding(
            receipt=basis,
            item=item,
            admission=admission,
            arm_catalog=arm_catalogs[case_id],
            frame=frames[case_id],
            catalog=catalog,
            refs=evidence_refs(item),
        )
        if contract:
            failures.append({
                **call,
                "contract_failures": contract,
                "invalid_receipt": basis,
            })
            continue
        bases[case_id] = basis
        receipts[case_id] = compile_surface_binding(
            item=item,
            admission=admission,
            arm_catalog=arm_catalogs[case_id],
            frame=frames[case_id],
            catalog=catalog,
            basis=basis,
            refs=evidence_refs(item),
        )
    frame_calls = [
        call for call in source_frame_run["task_calls"]
        if call["role"] == "A5_WITNESS_FRAME"
    ]
    value = {
        "runtime_version": "surface_binding_runtime_v0_71",
        "arm_id": "A7_SOURCE_SURFACE_ID_BINDING",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_frame_run_hash": source_frame_run["run_hash"],
        "provider_id": adapter.profile.provider_id,
        "model_id": adapter.profile.model_id,
        "task_calls": [*frame_calls, *calls],
        "arm_catalogs": arm_catalogs,
        "frame_receipts": frames,
        "surface_catalogs": catalogs,
        "basis_receipts": bases,
        "receipts": receipts,
        "contract_failures": failures,
        "compiler_failures": [],
        "private_gold_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}
