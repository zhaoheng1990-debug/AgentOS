"""Private scoring for v0.69."""

from .benchmark_bridge_metrics import score_arm
from .provider_telemetry import hash_payload
from .relation_witness_protocol import validate_preregistration


def score_witness(*, panel, preregistration, baseline_run, candidate_run):
    validate_preregistration(preregistration)
    baseline = score_arm(
        panel=panel, preregistration=preregistration, run=baseline_run
    )
    candidate = score_arm(
        panel=panel, preregistration=preregistration, run=candidate_run
    )
    old = {case["case_id"]: case for case in baseline["cases"]}
    new = {case["case_id"]: case for case in candidate["cases"]}
    corrections = sorted(
        key for key in new
        if not old[key]["label_correct"] and new[key]["label_correct"]
    )
    harms = sorted(
        key for key in new
        if old[key]["label_correct"] and not new[key]["label_correct"]
    )
    value = {
        "score_version": "relation_witness_score_v0_69",
        "source_panel_hash": panel["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "baseline": baseline,
        "candidate": candidate,
        "candidate_total_failure_count": (
            len(candidate_run["contract_failures"])
            + len(candidate_run["compiler_failures"])
        ),
        "corrected_case_ids": corrections,
        "harmed_case_ids": harms,
        "unresolved_case_ids": sorted(
            key for key, receipt in candidate_run["receipts"].items()
            if receipt["predicted_label"]
            == "UNRESOLVED_MATERIAL_AMBIGUITY"
        ),
    }
    return {**value, "artifact_hash": hash_payload(value)}


def calibration_decision(*, preregistration, score):
    validate_preregistration(preregistration)
    gate = preregistration["calibration_gate"]
    candidate, baseline = score["candidate"], score["baseline"]
    labels = {
        case["case_id"]: case["predicted_label"]
        for case in candidate["cases"]
    }
    conditions = {
        "valid_receipts": candidate["valid_receipt_count"]
        >= gate["valid_receipts_min"],
        "failures": score["candidate_total_failure_count"]
        <= gate["failure_count_max"],
        "label_accuracy": candidate["label_accuracy"]
        >= gate["label_accuracy_min"],
        "evidence_f1": candidate["evidence_f1"] >= baseline["evidence_f1"],
        "effective_cbit": candidate["effective_cbit"]
        > baseline["effective_cbit"],
        "no_harms": len(score["harmed_case_ids"])
        <= gate["harmed_cases_max"],
        "required_labels": all(
            labels.get(key) == value
            for key, value in gate["required_labels"].items()
        ),
        "task_budget": candidate["provider_task_count"]
        <= preregistration["maximum_provider_tasks"],
        "attempt_budget": candidate["physical_attempt_count"]
        <= preregistration["maximum_physical_attempts"],
        "token_budget": candidate["physical_total_tokens"]
        <= preregistration["hard_token_ceiling"],
    }
    passed = all(conditions.values())
    value = {
        "decision_version": "relation_witness_decision_v0_69",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_score_hash": score["artifact_hash"],
        "conditions": conditions,
        "decision": (
            "PASS_RELATION_WITNESS_CALIBRATION"
            if passed else "REJECT_RELATION_WITNESS_CALIBRATION"
        ),
        "fresh_holdout_authorized": passed,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}
