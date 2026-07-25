"""Mechanical fail-closed finalization for an incomplete holdout admission."""

from __future__ import annotations

from .fresh_holdout_protocol import validate_preregistration
from .provider_telemetry import hash_payload
from .selection_retention_fresh_provider_helpers import (
    physical_attempts,
    token_count,
)


def finalize_admission_block(*, preregistration, baseline_run):
    validate_preregistration(preregistration)
    expected = preregistration["case_count"]
    admission_count = len(baseline_run["admission_receipts"])
    if admission_count >= expected:
        raise ValueError("fresh_holdout_admission_block_not_present")
    failures = [
        {
            "case_id": failure["case_id"],
            "role": failure["role"],
            "task_id": failure["task_id"],
            "contract_failures": failure["contract_failures"],
            "invalid_receipt_hash": hash_payload(
                failure.get("invalid_receipt", {})
            ),
        }
        for failure in baseline_run["contract_failures"]
    ]
    value = {
        "decision_version": "fresh_holdout_block_v0_75",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "decision": "BLOCKED_BY_ADMISSION_CONTRACT",
        "expected_admission_receipts": expected,
        "valid_admission_receipts": admission_count,
        "valid_baseline_receipts": len(baseline_run["receipts"]),
        "failure_count": len(failures),
        "failure_records": failures,
        "provider_task_count": len(baseline_run["task_calls"]),
        "physical_attempt_count": physical_attempts(
            baseline_run["task_calls"]
        ),
        "physical_total_tokens": token_count(
            baseline_run["task_calls"]
        ),
        "candidate_execution_started": False,
        "private_gold_scored": False,
        "fresh_generalization_assessable": False,
        "holdout_consumed_at_admission_stage": True,
        "holdout_reexecution_allowed": False,
        "holdout_driven_mechanism_change_allowed": False,
        "next_research_object": (
            "NULL_AND_CONTEXTUAL_EVIDENCE_ADMISSION_CONTRACT"
        ),
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}
