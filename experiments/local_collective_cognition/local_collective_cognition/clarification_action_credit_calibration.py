"""Fresh validation scoring for a frozen clarification action credit ledger."""

from __future__ import annotations

from .clarification_action_credit_holdout import validate_action_credit_validation_artifact
from .clarification_action_credit_ledger import validate_action_credit_ledger
from .clarification_action_credit_runtime import validate_action_credit_run
from .clarification_regret_holdout import CLARIFICATION_COST, CORRECT_UTILITY, WRONG_UTILITY
from .provider_telemetry import hash_payload


CALIBRATION_VERSION = "clarification_action_credit_calibration_v0_7"
ARMS = ("ALWAYS_ASK", "ALWAYS_ANSWER_A", "DIRECT_POLICY", "LEDGER_POLICY")
ACTION_KEYS = {"ALWAYS_ASK": "always_ask_action", "ALWAYS_ANSWER_A": "always_answer_a_action", "DIRECT_POLICY": "direct_policy_action", "LEDGER_POLICY": "ledger_policy_action"}
FROZEN_GATES = {"minimum_mean_utility": 0.85, "minimum_open_utility": 0.70, "minimum_control_utility": 0.90, "maximum_wrong_answer_rate": 0.10, "maximum_unnecessary_question_rate": 0.25, "maximum_missed_clarification_rate": 0.25, "minimum_utility_gain_vs_direct": 0.05, "maximum_call_multiplier": 1.10}


def build_action_credit_calibration(*, calibration_corpus, calibration_run, ledger, validation_corpus, validation_run):
    validate_action_credit_validation_artifact(validation_corpus)
    validate_action_credit_run(validation_run, corpus_artifact=validation_corpus, expected_mode="VALIDATION", ledger=ledger)
    validate_action_credit_ledger(ledger, calibration_corpus=calibration_corpus, calibration_run=calibration_run)
    if validation_run.get("ledger_hash") != ledger["ledger_hash"] or calibration_corpus["artifact_hash"] == validation_corpus["artifact_hash"]:
        raise ValueError("clarification_action_credit_split_invalid")
    oracle = validation_corpus["private_oracle"]["bindings"]
    records = {item["blind_case_id"]: item for item in validation_run["records"]}
    rows = []
    for blind_id in sorted(oracle):
        binding = oracle[blind_id]
        row = {"blind_case_id": blind_id, "category": binding["category"], "fingerprint": records[blind_id]["fingerprint"]}
        for arm, key in ACTION_KEYS.items():
            action = records[blind_id][key]
            row[arm] = action
            row[f"{arm}_utility"] = _utility(action, binding)
        rows.append(row)
    metrics = {arm: _metrics(arm, rows, validation_run["arm_accounting"][arm]) for arm in ARMS}
    direct, policy = metrics["DIRECT_POLICY"], metrics["LEDGER_POLICY"]
    gates = {
        "mean_utility": policy["mean_utility"] >= FROZEN_GATES["minimum_mean_utility"],
        "open_utility": policy["open_utility"] >= FROZEN_GATES["minimum_open_utility"],
        "control_utility": policy["control_utility"] >= FROZEN_GATES["minimum_control_utility"],
        "wrong_answer_rate": policy["wrong_answer_rate"] <= FROZEN_GATES["maximum_wrong_answer_rate"],
        "unnecessary_question_rate": policy["unnecessary_question_rate"] <= FROZEN_GATES["maximum_unnecessary_question_rate"],
        "missed_clarification_rate": policy["missed_clarification_rate"] <= FROZEN_GATES["maximum_missed_clarification_rate"],
        "utility_gain_vs_direct": policy["mean_utility"] - direct["mean_utility"] >= FROZEN_GATES["minimum_utility_gain_vs_direct"],
        "call_multiplier": policy["call_multiplier"] <= FROZEN_GATES["maximum_call_multiplier"],
    }
    state = "ACTION_CREDIT_TRANSFER_CANDIDATE" if all(gates.values()) else "ACTION_CREDIT_TRANSFER_GATE_FAILED"
    commitment = {"calibration_version": CALIBRATION_VERSION, "frozen_gates": FROZEN_GATES, "calibration_corpus_hash": calibration_corpus["artifact_hash"], "calibration_run_hash": calibration_run["candidate_run_hash"], "ledger_hash": ledger["ledger_hash"], "validation_corpus_hash": validation_corpus["artifact_hash"], "validation_run_hash": validation_run["candidate_run_hash"], "rows": rows, "arm_metrics": metrics, "gate_results": gates, "candidate_state": state, "evidence_coordinate": "SYNTHETIC_FORMAL_AUDIT", "validation_outcomes_written_to_current_ledger": False, "real_world_ground_truth_claim": False, "selection_authority": False, "retention_authority": False, "production_authority": False}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_action_credit_calibration(artifact, **sources):
    commitment = {key: value for key, value in artifact.items() if key != "artifact_hash"}
    if artifact.get("artifact_hash") != hash_payload(commitment) or artifact != build_action_credit_calibration(**sources):
        raise ValueError("clarification_action_credit_calibration_invalid")


def _utility(action, binding):
    if action == "ASK": return CORRECT_UTILITY - CLARIFICATION_COST
    return CORRECT_UTILITY if action in binding["valid_direct_actions"] else WRONG_UTILITY


def _metrics(arm, rows, accounting):
    open_rows = [row for row in rows if row["category"] == "OPEN"]
    controls = [row for row in rows if row["category"] != "OPEN"]
    utilities = [row[f"{arm}_utility"] for row in rows]
    calls = accounting["attributed_provider_calls"]; tokens = accounting["attributed_input_tokens"] + accounting["attributed_output_tokens"]
    return {"mean_utility": sum(utilities)/len(rows), "open_utility": sum(row[f"{arm}_utility"] for row in open_rows)/len(open_rows), "control_utility": sum(row[f"{arm}_utility"] for row in controls)/len(controls), "wrong_answer_rate": sum(row[arm] != "ASK" and row[f"{arm}_utility"] == WRONG_UTILITY for row in rows)/len(rows), "unnecessary_question_rate": sum(row[arm] == "ASK" for row in controls)/len(controls), "missed_clarification_rate": sum(row[arm] != "ASK" for row in open_rows)/len(open_rows), "ask_rate": sum(row[arm] == "ASK" for row in rows)/len(rows), "attributed_provider_calls": calls, "attributed_tokens": tokens, "call_multiplier": calls/(len(rows)/2) if calls else 0.0, "tokens_per_item": tokens/len(rows) if tokens else 0.0}
