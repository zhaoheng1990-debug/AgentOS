"""Deterministic frame-to-basis coordinate projection for v0.72."""

from __future__ import annotations

from copy import deepcopy

from .provider_telemetry import hash_payload
from .surface_binding_compiler import compile_surface_binding


PROJECTION_VERSION = "coordinate_projection_v0_72"


def project_basis(*, case_id, frame, basis):
    projected = deepcopy(basis)
    changes = []
    rules = (
        (
            "timepoint_binding",
            frame["timepoint_requirement"],
            "FRAME_TIMEPOINT_UNCONSTRAINED",
        ),
        (
            "measurement_binding",
            frame["measurement_requirement"],
            "FRAME_MEASUREMENT_UNCONSTRAINED",
        ),
    )
    for record in projected["basis_records"]:
        for field, requirement, rule in rules:
            if requirement["mode"] != "UNCONSTRAINED":
                continue
            before = record[field]
            after = "ALLOWED_BY_UNCONSTRAINED"
            if before == after:
                continue
            record[field] = after
            changes.append({
                "span_id": record["span_id"],
                "field": field,
                "before": before,
                "after": after,
                "rule": rule,
            })
    receipt = {
        "projection_version": PROJECTION_VERSION,
        "case_id": case_id,
        "source_frame_hash": hash_payload(frame),
        "source_basis_hash": hash_payload(basis),
        "projected_basis_hash": hash_payload(projected),
        "changes": changes,
        "semantic_text_interpretation_performed": False,
        "provider_override_allowed": False,
    }
    return projected, {**receipt, "projection_hash": hash_payload(receipt)}


def build_projection_replay(*, panel, preregistration, source_run):
    frames = source_run["frame_receipts"]
    projected_bases, projection_receipts, receipts = {}, {}, {}
    for item in panel["public_surface"]["items"]:
        case_id = item["case_id"]
        projected, projection = project_basis(
            case_id=case_id,
            frame=frames[case_id],
            basis=source_run["basis_receipts"][case_id],
        )
        projected_bases[case_id] = projected
        projection_receipts[case_id] = projection
        receipts[case_id] = compile_surface_binding(
            item=item,
            admission=panel["source_admission_receipts"][case_id],
            arm_catalog=source_run["arm_catalogs"][case_id],
            frame=frames[case_id],
            catalog=source_run["surface_catalogs"][case_id],
            basis=projected,
            refs=tuple(source_run["receipts"][case_id]["evidence_refs"]),
        )
    value = {
        "runtime_version": "coordinate_projection_replay_v0_72",
        "arm_id": "A8_FRAME_COORDINATE_PROJECTION",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": source_run["run_hash"],
        "task_calls": source_run["task_calls"],
        "frame_receipts": frames,
        "surface_catalogs": source_run["surface_catalogs"],
        "basis_receipts": projected_bases,
        "projection_receipts": projection_receipts,
        "receipts": receipts,
        "contract_failures": [],
        "compiler_failures": [],
        "provider_calls_added": 0,
        "private_gold_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "run_hash": hash_payload(value)}
