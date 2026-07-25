"""Paired outcome and inclusive-cost accounting for v0.75."""

from __future__ import annotations

import math
import random
from statistics import mean

from .provider_telemetry import hash_payload


BOOTSTRAP_SEED = 75075
BOOTSTRAP_SAMPLES = 10000


def build_candidate_cost_view(*, baseline_run, candidate_run):
    admission_calls = [
        call for call in baseline_run["task_calls"]
        if call["role"] == "A1_SPAN_ADMISSION"
    ]
    admission_failures = [
        failure for failure in baseline_run["contract_failures"]
        if failure["role"] == "A1_SPAN_ADMISSION"
    ]
    value = {
        key: item
        for key, item in candidate_run.items()
        if key not in {"run_hash", "task_calls", "contract_failures"}
    }
    value.update({
        "runtime_version": "fresh_holdout_cost_view_v0_75",
        "arm_id": "A10_GROUPED_ALIAS_WITH_SHARED_ADMISSION_COST",
        "task_calls": [*admission_calls, *candidate_run["task_calls"]],
        "contract_failures": [
            *admission_failures,
            *candidate_run["contract_failures"],
        ],
        "source_candidate_run_hash": candidate_run["run_hash"],
        "source_baseline_run_hash": baseline_run["run_hash"],
        "shared_admission_task_count": len(admission_calls),
        "incremental_candidate_task_count": len(
            candidate_run["task_calls"]
        ),
    })
    return {**value, "run_hash": hash_payload(value)}


def paired_outcome_summary(*, baseline_score, candidate_score):
    baseline = {
        value["case_id"]: value for value in baseline_score["cases"]
    }
    candidate = {
        value["case_id"]: value for value in candidate_score["cases"]
    }
    if set(baseline) != set(candidate):
        raise ValueError("fresh_holdout_case_set_mismatch")
    case_ids = sorted(baseline)
    corrected = [
        case_id for case_id in case_ids
        if not baseline[case_id]["label_correct"]
        and candidate[case_id]["label_correct"]
    ]
    harmed = [
        case_id for case_id in case_ids
        if baseline[case_id]["label_correct"]
        and not candidate[case_id]["label_correct"]
    ]
    deltas = [
        candidate[case_id]["effective_cbit"]
        - baseline[case_id]["effective_cbit"]
        for case_id in case_ids
    ]
    interval = _bootstrap_interval(deltas)
    value = {
        "comparison_version": "fresh_holdout_paired_outcome_v0_75",
        "source_baseline_score_hash": baseline_score["artifact_hash"],
        "source_candidate_score_hash": candidate_score["artifact_hash"],
        "case_count": len(case_ids),
        "corrected_case_ids": corrected,
        "harmed_case_ids": harmed,
        "net_label_corrections": len(corrected) - len(harmed),
        "label_accuracy_delta": (
            candidate_score["label_accuracy"]
            - baseline_score["label_accuracy"]
        ),
        "evidence_f1_delta": (
            candidate_score["evidence_f1"]
            - baseline_score["evidence_f1"]
        ),
        "rationale_token_f1_delta": (
            candidate_score["rationale_token_f1"]
            - baseline_score["rationale_token_f1"]
        ),
        "effective_cbit_delta": mean(deltas),
        "effective_cbit_delta_bootstrap_95": interval,
        "label_discordance_exact_p": _two_sided_binomial(
            len(corrected),
            len(harmed),
        ),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_samples": BOOTSTRAP_SAMPLES,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def _bootstrap_interval(values):
    generator = random.Random(BOOTSTRAP_SEED)
    count = len(values)
    estimates = sorted(
        mean(values[generator.randrange(count)] for _ in range(count))
        for _ in range(BOOTSTRAP_SAMPLES)
    )
    return {
        "lower": estimates[math.floor(0.025 * (BOOTSTRAP_SAMPLES - 1))],
        "upper": estimates[math.ceil(0.975 * (BOOTSTRAP_SAMPLES - 1))],
    }


def _two_sided_binomial(corrected, harmed):
    discordant = corrected + harmed
    if discordant == 0:
        return 1.0
    tail = min(corrected, harmed)
    probability = sum(
        math.comb(discordant, value)
        for value in range(tail + 1)
    ) / (2 ** discordant)
    return min(1.0, 2 * probability)
