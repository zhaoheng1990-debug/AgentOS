"""Frozen v0.65 challenge projection for v0.66 calibration."""

from __future__ import annotations

from typing import Any

from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload
from .semantic_basis_selection import challenge_tags


CALIBRATION_CASE_IDS = (
    "EI-CAL-1113",
    "EI-CAL-8846",
    "EI-CAL-6743",
    "EI-CAL-13790",
    "EI-CAL-5842",
    "EI-CAL-9330",
    "EI-CAL-3189",
    "EI-CAL-5791",
    "EI-CAL-13793",
    "EI-CAL-11179",
    "EI-CAL-8861",
    "EI-CAL-8555",
)
KNOWN_FAILURES = {
    "EI-CAL-11179": "SIGNIFICANCE_BOUNDARY",
    "EI-CAL-5842": "COMPARISON_ORIENTATION",
    "EI-CAL-13793": "MATERIAL_AMBIGUITY_AND_COMPLETENESS",
}


def build_calibration_projection(
    *,
    calibration_panel: dict[str, Any],
    calibration_run: dict[str, Any],
    holdout_panel: dict[str, Any],
    holdout_run: dict[str, Any],
    source_closure: dict[str, Any],
) -> dict[str, Any]:
    validate_panel(calibration_panel)
    validate_panel(holdout_panel)
    for run in (calibration_run, holdout_run):
        _validate_run_hash(run)
    _validate_artifact_hash(source_closure)
    if source_closure.get("decision") != (
        "REJECT_BENCHMARK_BRIDGE_TEST_SPLIT_TRANSFER"
    ):
        raise ValueError("semantic_basis_source_closure_invalid")
    panels = (calibration_panel, holdout_panel)
    runs = (calibration_run, holdout_run)
    items = {
        item["case_id"]: item
        for panel in panels
        for item in panel["public_surface"]["items"]
    }
    gold = {
        case_id: value
        for panel in panels
        for case_id, value in panel["private_gold"].items()
    }
    admissions = {
        case_id: value
        for run in runs
        for case_id, value in run["admission_receipts"].items()
    }
    baseline_receipts = {
        case_id: value
        for run in runs
        for case_id, value in run["receipts"].items()
        if case_id in CALIBRATION_CASE_IDS
    }
    public_items = [items[case_id] for case_id in CALIBRATION_CASE_IDS]
    private_gold = {
        case_id: gold[case_id] for case_id in CALIBRATION_CASE_IDS
    }
    source_admissions = {
        case_id: admissions[case_id] for case_id in CALIBRATION_CASE_IDS
    }
    baseline_failures = [
        failure
        for run in runs
        for failure in run["contract_failures"]
        if failure["case_id"] in CALIBRATION_CASE_IDS
    ]
    baseline_calls = [
        call
        for run in runs
        for call in run["task_calls"]
        if call["case_id"] in CALIBRATION_CASE_IDS
    ]
    baseline_commitment = {
        "arm_id": "A1_DIRECT_BINDING",
        "receipts": baseline_receipts,
        "contract_failures": baseline_failures,
        "task_calls": baseline_calls,
        "source_run_hashes": [
            calibration_run["run_hash"],
            holdout_run["run_hash"],
        ],
    }
    baseline_projection = {
        **baseline_commitment,
        "run_hash": hash_payload(baseline_commitment),
    }
    commitment = {
        "projection_version": "semantic_basis_calibration_v0_66",
        "benchmark_id": "evidence-inference-semantic-basis-calibration",
        "split": "revealed_v0_65_development_challenges",
        "case_count": len(public_items),
        "label_balance": {
            label: sum(
                value["label"] == label
                for value in private_gold.values()
            )
            for label in ("INCREASED", "DECREASED", "NO_DIFFERENCE")
        },
        "challenge_tags": {
            item["case_id"]: challenge_tags(
                " ".join(
                    span["text"] for span in item["candidate_spans"]
                )
            )
            for item in public_items
        },
        "known_failures": KNOWN_FAILURES,
        "public_surface": {"items": public_items},
        "source_admission_receipts": source_admissions,
        "baseline_projection": baseline_projection,
        "private_gold": private_gold,
        "source_artifacts": {
            "calibration_panel_hash": calibration_panel["artifact_hash"],
            "calibration_run_hash": calibration_run["run_hash"],
            "holdout_panel_hash": holdout_panel["artifact_hash"],
            "holdout_run_hash": holdout_run["run_hash"],
            "source_closure_hash": source_closure["artifact_hash"],
        },
        "development_calibration": True,
        "fresh_generalization_claim": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def public_projection(value: dict[str, Any]) -> dict[str, Any]:
    return {
        "projection_version": value["projection_version"],
        "benchmark_id": value["benchmark_id"],
        "split": value["split"],
        "case_count": value["case_count"],
        "challenge_tags": value["challenge_tags"],
        "public_surface": value["public_surface"],
        "source_admission_receipts": value[
            "source_admission_receipts"
        ],
        "source_artifact_hash": value["artifact_hash"],
    }


def validate_calibration_projection(value: dict[str, Any]) -> None:
    _validate_artifact_hash(value)
    if value.get("case_count") != 12:
        raise ValueError("semantic_basis_calibration_count_invalid")
    if value.get("label_balance") != {
        "INCREASED": 4,
        "DECREASED": 4,
        "NO_DIFFERENCE": 4,
    }:
        raise ValueError("semantic_basis_calibration_balance_invalid")
    case_ids = {
        item["case_id"] for item in value["public_surface"]["items"]
    }
    if case_ids != set(CALIBRATION_CASE_IDS):
        raise ValueError("semantic_basis_calibration_cases_invalid")
    if set(value["source_admission_receipts"]) != case_ids:
        raise ValueError("semantic_basis_admission_coverage_invalid")
    if set(value["private_gold"]) != case_ids:
        raise ValueError("semantic_basis_private_gold_coverage_invalid")


def _validate_run_hash(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "run_hash"
    }
    if value.get("run_hash") != hash_payload(commitment):
        raise ValueError("semantic_basis_source_run_hash_invalid")


def _validate_artifact_hash(value: dict[str, Any]) -> None:
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("semantic_basis_artifact_hash_invalid")
