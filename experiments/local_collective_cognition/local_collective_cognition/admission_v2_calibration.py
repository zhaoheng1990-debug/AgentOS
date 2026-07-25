"""Revealed development projection and scoring for Admission V2."""

from __future__ import annotations

from statistics import mean

from .evidence_inference_bridge import validate_panel
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


SELECTED_CASE_IDS = (
    "EI-CAL-8984",
    "EI-CAL-9554",
    "EI-CAL-9333",
    "EI-CAL-8986",
    "EI-CAL-11995",
    "EI-CAL-5362",
    "EI-CAL-10177",
    "EI-CAL-9748",
    "EI-CAL-6857",
    "EI-CAL-8615",
    "EI-CAL-6165",
    "EI-CAL-11806",
)
EXCLUDED_SURFACE_CALIBRATION_CASE_IDS = (
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


def build_calibration_projection(
    *, panels, runs, excluded_case_ids
):
    for panel in panels:
        validate_panel(panel)
    for run in runs:
        _validate_run_hash(run)
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
    selected = set(SELECTED_CASE_IDS)
    if selected & set(excluded_case_ids):
        raise ValueError("admission_v2_reused_surface_calibration_case")
    if not selected.issubset(items) or not selected.issubset(admissions):
        raise ValueError("admission_v2_selected_case_missing")
    public_items = [items[case_id] for case_id in SELECTED_CASE_IDS]
    private_gold = {
        case_id: gold[case_id] for case_id in SELECTED_CASE_IDS
    }
    source_admissions = {
        case_id: admissions[case_id] for case_id in SELECTED_CASE_IDS
    }
    baseline_partitions = {
        case_id: _old_partition(items[case_id], admissions[case_id])
        for case_id in SELECTED_CASE_IDS
    }
    selection_metadata = {
        case_id: {
            "old_contextual_record_count": sum(
                record["relation"] == "CONTEXTUAL"
                for record in admissions[case_id]["decisions"]
            ),
            "selection_status": "REVEALED_DEVELOPMENT_DATA",
        }
        for case_id in SELECTED_CASE_IDS
    }
    value = {
        "projection_version": "admission_v2_calibration_v0_76",
        "benchmark_id": "evidence-inference-admission-v2-calibration",
        "split": "revealed_v0_65_development_projection",
        "case_count": len(public_items),
        "label_balance": {
            label: sum(
                value["label"] == label
                for value in private_gold.values()
            )
            for label in ("INCREASED", "DECREASED", "NO_DIFFERENCE")
        },
        "public_surface": {"items": public_items},
        "private_gold": private_gold,
        "source_admission_receipts": source_admissions,
        "baseline_partitions": baseline_partitions,
        "selection_metadata": selection_metadata,
        "excluded_surface_calibration_case_ids": sorted(
            excluded_case_ids
        ),
        "source_panel_hashes": [
            panel["artifact_hash"] for panel in panels
        ],
        "source_run_hashes": [run["run_hash"] for run in runs],
        "development_calibration": True,
        "fresh_generalization_claim": False,
        "v0_75_holdout_reused": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def public_projection(value):
    return {
        "projection_version": value["projection_version"],
        "benchmark_id": value["benchmark_id"],
        "split": value["split"],
        "case_count": value["case_count"],
        "public_surface": value["public_surface"],
        "source_artifact_hash": value["artifact_hash"],
    }


def validate_calibration_projection(value):
    _validate_artifact_hash(value)
    if value.get("case_count") != 12:
        raise ValueError("admission_v2_calibration_count_invalid")
    if value.get("label_balance") != {
        "INCREASED": 4,
        "DECREASED": 4,
        "NO_DIFFERENCE": 4,
    }:
        raise ValueError("admission_v2_calibration_balance_invalid")
    observed = {
        item["case_id"] for item in value["public_surface"]["items"]
    }
    if observed != set(SELECTED_CASE_IDS):
        raise ValueError("admission_v2_calibration_cases_invalid")
    if value.get("v0_75_holdout_reused") is not False:
        raise ValueError("admission_v2_v075_reuse_boundary_invalid")


def score_calibration(*, panel, run):
    validate_calibration_projection(panel)
    _validate_run_hash(run)
    baseline = _score_partitions(
        panel=panel,
        partitions=panel["baseline_partitions"],
        valid_receipt_count=panel["case_count"],
        failure_count=0,
        task_calls=[],
        arm_id="A1_BINARY_ADMISSION_BASELINE",
    )
    candidate = _score_partitions(
        panel=panel,
        partitions=run["partitions"],
        valid_receipt_count=len(run["receipts"]),
        failure_count=(
            len(run["contract_failures"])
            + len(run["compiler_failures"])
        ),
        task_calls=run["task_calls"],
        arm_id=run["arm_id"],
    )
    old = {
        value["case_id"]: value for value in baseline["cases"]
    }
    new = {
        value["case_id"]: value for value in candidate["cases"]
    }
    improved = sorted(
        case_id for case_id in new
        if new[case_id]["evidence_f1"] > old[case_id]["evidence_f1"]
    )
    harmed = sorted(
        case_id for case_id in new
        if new[case_id]["evidence_f1"] < old[case_id]["evidence_f1"]
    )
    value = {
        "score_version": "admission_v2_score_v0_76",
        "source_panel_hash": panel["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "improved_case_ids": improved,
        "harmed_case_ids": harmed,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _old_partition(item, receipt):
    evidence = sorted(
        value["span_id"] for value in receipt["decisions"]
        if value["decision"] == "ADMIT"
    )
    rejected = sorted(
        value["span_id"] for value in receipt["decisions"]
        if value["decision"] == "REJECT"
    )
    value = {
        "compiler_version": "binary_admission_projection_v0_76",
        "case_id": item["case_id"],
        "evidence_span_ids": evidence,
        "context_span_ids": [],
        "rejected_span_ids": rejected,
        "admission_state": (
            "EVIDENCE_AVAILABLE"
            if evidence
            else "NO_APPLICABLE_EVIDENCE"
        ),
    }
    return {**value, "partition_hash": hash_payload(value)}


def _score_partitions(
    *,
    panel,
    partitions,
    valid_receipt_count,
    failure_count,
    task_calls,
    arm_id,
):
    items = {
        item["case_id"]: item
        for item in panel["public_surface"]["items"]
    }
    cases = []
    for case_id, gold in panel["private_gold"].items():
        partition = partitions.get(case_id)
        if partition is None:
            cases.append({
                "case_id": case_id,
                "evidence_precision": 0.0,
                "evidence_recall": 0.0,
                "evidence_f1": 0.0,
                "context_span_count": 0,
                "partition_complete": 0,
                "false_no_applicable_evidence": 1,
            })
            continue
        predicted = set(partition["evidence_span_ids"])
        expected = set(gold["gold_rationale_span_ids"])
        matched = len(predicted & expected)
        precision = matched / len(predicted) if predicted else 0.0
        recall = matched / len(expected) if expected else 0.0
        evidence_f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        observed = set(
            partition["evidence_span_ids"]
            + partition["context_span_ids"]
            + partition["rejected_span_ids"]
        )
        expected_ids = {
            span["span_id"] for span in items[case_id]["candidate_spans"]
        }
        cases.append({
            "case_id": case_id,
            "evidence_precision": precision,
            "evidence_recall": recall,
            "evidence_f1": evidence_f1,
            "context_span_count": len(partition["context_span_ids"]),
            "partition_complete": int(observed == expected_ids),
            "false_no_applicable_evidence": int(
                partition["admission_state"]
                == "NO_APPLICABLE_EVIDENCE"
            ),
        })
    value = {
        "arm_id": arm_id,
        "case_count": len(cases),
        "valid_receipt_count": valid_receipt_count,
        "failure_count": failure_count,
        "evidence_precision": mean(
            value["evidence_precision"] for value in cases
        ),
        "evidence_recall": mean(
            value["evidence_recall"] for value in cases
        ),
        "evidence_f1": mean(
            value["evidence_f1"] for value in cases
        ),
        "context_span_count": sum(
            value["context_span_count"] for value in cases
        ),
        "complete_partition_count": sum(
            value["partition_complete"] for value in cases
        ),
        "false_no_applicable_count": sum(
            value["false_no_applicable_evidence"] for value in cases
        ),
        "provider_task_count": len(task_calls),
        "physical_attempt_count": physical_attempts(task_calls),
        "physical_total_tokens": token_count(task_calls),
        "cases": cases,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _validate_run_hash(value):
    commitment = {
        key: item for key, item in value.items() if key != "run_hash"
    }
    if value.get("run_hash") != hash_payload(commitment):
        raise ValueError("admission_v2_source_run_hash_invalid")


def _validate_artifact_hash(value):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    if value.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("admission_v2_artifact_hash_invalid")
