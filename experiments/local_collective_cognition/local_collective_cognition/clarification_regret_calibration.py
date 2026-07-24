"""Formal oracle scoring and frozen v0.6 admission gates."""

from __future__ import annotations

from .clarification_regret_fusion import ARMS
from .clarification_regret_holdout import CLARIFICATION_COST, CORRECT_UTILITY, WRONG_UTILITY, validate_clarification_regret_artifact
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_regret_calibration_v0_6"
ACTION_KEYS = {
    "ALWAYS_ASK": "always_ask_action",
    "ALWAYS_ANSWER_A": "always_answer_a_action",
    "DIRECT_POLICY": "direct_policy_action",
    "SINGLE_REGRET": "single_regret_action",
    "THREE_PASS_REGRET": "three_pass_regret_action",
}
FROZEN_GATES = {
    "single_regret": {
        "minimum_mean_utility": 0.82,
        "minimum_open_utility": 0.70,
        "minimum_control_utility": 0.85,
        "maximum_wrong_answer_rate": 0.10,
        "maximum_unnecessary_question_rate": 0.30,
        "maximum_missed_clarification_rate": 0.25,
        "minimum_utility_gain_vs_direct": 0.03,
        "maximum_call_multiplier": 1.10,
    },
    "three_pass_regret": {
        "minimum_mean_utility": 0.85,
        "minimum_open_utility": 0.70,
        "minimum_control_utility": 0.90,
        "maximum_wrong_answer_rate": 0.10,
        "maximum_unnecessary_question_rate": 0.25,
        "maximum_missed_clarification_rate": 0.25,
        "minimum_utility_gain_vs_single": 0.03,
        "maximum_control_utility_harm_vs_single": 0.05,
        "maximum_call_multiplier": 3.20,
    },
}


def build_clarification_regret_calibration(*, corpus_artifact, candidate_run):
    from .clarification_regret_runtime import validate_clarification_regret_run

    validate_clarification_regret_artifact(corpus_artifact)
    validate_clarification_regret_run(candidate_run, corpus_artifact=corpus_artifact)
    oracle = corpus_artifact["private_oracle"]["bindings"]
    records = {item["blind_case_id"]: item for item in candidate_run["fusion"]["records"]}
    rows = []
    for blind_id in sorted(oracle):
        binding = oracle[blind_id]
        row = {"blind_case_id": blind_id, "category": binding["category"], "operational_oracle_action": binding["operational_oracle_action"]}
        for arm, key in ACTION_KEYS.items():
            action = records[blind_id][key]
            row[arm] = action
            row[f"{arm}_utility"] = _utility(action, binding)
        rows.append(row)
    metrics = {arm: _metrics(arm, rows, candidate_run["fusion"]["arm_accounting"][arm]) for arm in ARMS}
    direct, single, three = (metrics[arm] for arm in ("DIRECT_POLICY", "SINGLE_REGRET", "THREE_PASS_REGRET"))
    sg = FROZEN_GATES["single_regret"]
    single_gates = {
        **_absolute_gates(single, sg),
        "utility_gain_vs_direct": single["mean_utility"] - direct["mean_utility"] >= sg["minimum_utility_gain_vs_direct"],
    }
    tg = FROZEN_GATES["three_pass_regret"]
    three_gates = {
        **_absolute_gates(three, tg),
        "utility_gain_vs_single": three["mean_utility"] - single["mean_utility"] >= tg["minimum_utility_gain_vs_single"],
        "control_utility_harm_vs_single": max(0.0, single["control_utility"] - three["control_utility"]) <= tg["maximum_control_utility_harm_vs_single"],
    }
    single_pass, three_pass = all(single_gates.values()), all(three_gates.values())
    state = (
        "SINGLE_AND_THREE_PASS_REGRET_CANDIDATES" if single_pass and three_pass
        else "THREE_PASS_REGRET_CANDIDATE" if three_pass
        else "SINGLE_REGRET_CANDIDATE" if single_pass
        else "CLARIFICATION_REGRET_GATE_FAILED"
    )
    commitment = {
        "calibration_version": CALIBRATION_VERSION,
        "frozen_gates": FROZEN_GATES,
        "corpus_artifact_hash": corpus_artifact["artifact_hash"],
        "candidate_run_hash": candidate_run["candidate_run_hash"],
        "rows": rows,
        "arm_metrics": metrics,
        "single_regret_gate_results": single_gates,
        "three_pass_regret_gate_results": three_gates,
        "candidate_state": state,
        "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT",
        "real_world_ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_clarification_regret_calibration(artifact, *, corpus_artifact, candidate_run):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_clarification_regret_calibration(corpus_artifact=corpus_artifact, candidate_run=candidate_run):
        raise ValueError("clarification_regret_calibration_invalid")


def _utility(action, binding):
    if action == "ASK":
        return CORRECT_UTILITY - CLARIFICATION_COST
    return CORRECT_UTILITY if action in binding["valid_direct_actions"] else WRONG_UTILITY


def _metrics(arm, rows, accounting):
    open_rows = [row for row in rows if row["category"] == "OPEN"]
    controls = [row for row in rows if row["category"] != "OPEN"]
    utilities = [row[f"{arm}_utility"] for row in rows]
    calls = accounting["attributed_provider_calls"]
    tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    oracle_utility = sum(CORRECT_UTILITY - CLARIFICATION_COST if row["category"] == "OPEN" else CORRECT_UTILITY for row in rows) / len(rows)
    return {
        "mean_utility": sum(utilities) / len(utilities),
        "open_utility": sum(row[f"{arm}_utility"] for row in open_rows) / len(open_rows),
        "control_utility": sum(row[f"{arm}_utility"] for row in controls) / len(controls),
        "wrong_answer_rate": sum(row[arm] != "ASK" and row[f"{arm}_utility"] == WRONG_UTILITY for row in rows) / len(rows),
        "unnecessary_question_rate": sum(row[arm] == "ASK" for row in controls) / len(controls),
        "missed_clarification_rate": sum(row[arm] != "ASK" for row in open_rows) / len(open_rows),
        "ask_rate": sum(row[arm] == "ASK" for row in rows) / len(rows),
        "operational_oracle_utility": oracle_utility,
        "utility_regret_vs_operational_oracle": oracle_utility - sum(utilities) / len(utilities),
        "attributed_provider_calls": calls,
        "attributed_tokens": tokens,
        "call_multiplier": calls / (len(rows) / 2) if calls else 0.0,
        "tokens_per_item": tokens / len(rows) if tokens else 0.0,
    }


def _absolute_gates(metrics, gates):
    return {
        "mean_utility": metrics["mean_utility"] >= gates["minimum_mean_utility"],
        "open_utility": metrics["open_utility"] >= gates["minimum_open_utility"],
        "control_utility": metrics["control_utility"] >= gates["minimum_control_utility"],
        "wrong_answer_rate": metrics["wrong_answer_rate"] <= gates["maximum_wrong_answer_rate"],
        "unnecessary_question_rate": metrics["unnecessary_question_rate"] <= gates["maximum_unnecessary_question_rate"],
        "missed_clarification_rate": metrics["missed_clarification_rate"] <= gates["maximum_missed_clarification_rate"],
        "call_multiplier": metrics["call_multiplier"] <= gates["maximum_call_multiplier"],
    }
