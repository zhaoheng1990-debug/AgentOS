"""Experiment-only posterior credit for ASK versus a Provider-preferred direct answer."""

from __future__ import annotations

from dataclasses import dataclass

from .clarification_action_credit_contracts import FINGERPRINTS
from .clarification_regret_holdout import CLARIFICATION_COST, CORRECT_UTILITY
from .provider_telemetry import hash_payload


LEDGER_VERSION = "clarification_action_credit_ledger_v0_7"
MINIMUM_OBSERVATIONS = 2
ASK_UTILITY = CORRECT_UTILITY - CLARIFICATION_COST


@dataclass(frozen=True)
class ActionCredit:
    fingerprint: str
    observations: int
    direct_successes: int
    direct_success_posterior: float
    ask_utility: float

    def as_dict(self):
        return dict(self.__dict__)


def build_action_credit_ledger(*, calibration_corpus, calibration_run):
    from .clarification_action_credit_runtime import validate_action_credit_run
    from .clarification_regret_holdout import validate_clarification_regret_artifact

    validate_clarification_regret_artifact(calibration_corpus)
    validate_action_credit_run(calibration_run, corpus_artifact=calibration_corpus, expected_mode="CALIBRATION")
    oracle = calibration_corpus["private_oracle"]["bindings"]
    proposals = {item["blind_case_id"]: item for item in calibration_run["proposals"]}
    records = []
    for fingerprint in FINGERPRINTS:
        selected = [item for item in proposals.values() if item["fingerprint"] == fingerprint]
        successes = sum(item["preferred_direct_answer"] in oracle[item["blind_case_id"]]["valid_direct_actions"] for item in selected)
        posterior = (successes + 1.0) / (len(selected) + 2.0)
        records.append(ActionCredit(fingerprint, len(selected), successes, round(posterior, 12), ASK_UTILITY).as_dict())
    commitment = {
        "ledger_version": LEDGER_VERSION,
        "source_corpus_hash": calibration_corpus["artifact_hash"],
        "source_run_hash": calibration_run["candidate_run_hash"],
        "records": records,
        "minimum_observations": MINIMUM_OBSERVATIONS,
        "ask_utility": ASK_UTILITY,
        "validation_outcomes_used": False,
        "experiment_only": True,
        "core_baseline_authority": False,
    }
    return {**commitment, "ledger_hash": hash_payload(commitment)}


def validate_action_credit_ledger(ledger, *, calibration_corpus, calibration_run):
    commitment = {key: value for key, value in ledger.items() if key != "ledger_hash"}
    if ledger.get("ledger_hash") != hash_payload(commitment) or ledger != build_action_credit_ledger(calibration_corpus=calibration_corpus, calibration_run=calibration_run):
        raise ValueError("clarification_action_credit_ledger_invalid")


def select_ledger_action(*, ledger, fingerprint, preferred_direct_answer):
    if preferred_direct_answer == "UNCERTAIN":
        return "ASK"
    record = next((item for item in ledger["records"] if item["fingerprint"] == fingerprint), None)
    if not record or record["observations"] < ledger["minimum_observations"]:
        return "ASK"
    return preferred_direct_answer if record["direct_success_posterior"] > ledger["ask_utility"] else "ASK"
