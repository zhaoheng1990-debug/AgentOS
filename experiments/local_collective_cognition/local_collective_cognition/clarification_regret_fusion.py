"""Runtime-owned action derivation from direct and regret receipts."""

from __future__ import annotations

from collections import Counter

from .clarification_regret_holdout import CLARIFICATION_COST
from .provider_telemetry import hash_payload


FUSION_VERSION = "clarification_regret_fusion_v0_6"
DIRECT = "DIRECT_POLICY"
REGRET_1 = "REGRET_PASS_1"
REGRET_2 = "REGRET_PASS_2"
REGRET_3 = "REGRET_PASS_3"
REGRET_LANES = (REGRET_1, REGRET_2, REGRET_3)
LANES = (DIRECT, *REGRET_LANES)
ARMS = ("ALWAYS_ASK", "ALWAYS_ANSWER_A", "DIRECT_POLICY", "SINGLE_REGRET", "THREE_PASS_REGRET")
ARM_LANES = {
    "ALWAYS_ASK": (),
    "ALWAYS_ANSWER_A": (),
    "DIRECT_POLICY": (DIRECT,),
    "SINGLE_REGRET": (REGRET_1,),
    "THREE_PASS_REGRET": REGRET_LANES,
}


def build_clarification_regret_fusion(*, corpus_artifact, lanes):
    direct = _index(lanes[DIRECT]["judgments"])
    regret_passes = [_index(lanes[lane]["judgments"]) for lane in REGRET_LANES]
    records = []
    for blind_id in sorted(corpus_artifact["private_oracle"]["bindings"]):
        direct_item = direct.get(blind_id)
        regrets = [items.get(blind_id) for items in regret_passes]
        records.append({
            "blind_case_id": blind_id,
            "always_ask_action": "ASK",
            "always_answer_a_action": "ANSWER_A",
            "direct_policy_action": _direct_action(direct_item),
            "single_regret_action": _single_regret_action(regrets[0]),
            "three_pass_regret_action": _three_pass_regret_action(regrets),
            "single_probability_preferred_wrong": regrets[0]["probability_preferred_wrong"] if regrets[0] else None,
            "three_pass_mean_probability_wrong": _mean_probability(regrets),
            "three_pass_preferred_answer": _majority_answer(regrets),
        })
    accounting = {
        arm: {
            "attributed_provider_calls": sum(lanes[lane]["provider_calls"] for lane in arm_lanes),
            "attributed_input_tokens": sum(lanes[lane]["input_tokens"] for lane in arm_lanes),
            "attributed_output_tokens": sum(lanes[lane]["output_tokens"] for lane in arm_lanes),
            "lanes": list(arm_lanes),
        }
        for arm, arm_lanes in ARM_LANES.items()
    }
    commitment = {
        "fusion_version": FUSION_VERSION,
        "records": records,
        "arm_accounting": accounting,
        "clarification_threshold": CLARIFICATION_COST,
        "single_rule": "ASK_IF_ESTIMATED_WRONG_PROBABILITY_EXCEEDS_CLARIFICATION_COST",
        "three_pass_rule": "STRICT_PREFERRED_ANSWER_MAJORITY_PLUS_MEAN_WRONG_PROBABILITY",
        "missing_or_uncertain_receipt_action": "ASK",
        "provider_proposes_evidence_runtime_owns_action": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def _index(judgments):
    return {item["blind_case_id"]: item for judgment in judgments for item in judgment["payload"]["assessments"]}


def _direct_action(item):
    if not item or item["action"] == "UNCERTAIN":
        return "ASK"
    return item["action"]


def _single_regret_action(item):
    if not item or item["preferred_direct_answer"] == "UNCERTAIN":
        return "ASK"
    return "ASK" if item["probability_preferred_wrong"] > CLARIFICATION_COST else item["preferred_direct_answer"]


def _three_pass_regret_action(items):
    answer = _majority_answer(items)
    probability = _mean_probability(items)
    if answer == "UNCERTAIN" or probability is None or probability > CLARIFICATION_COST:
        return "ASK"
    return answer


def _majority_answer(items):
    answers = [item["preferred_direct_answer"] for item in items if item and item["preferred_direct_answer"] != "UNCERTAIN"]
    if not answers:
        return "UNCERTAIN"
    answer, count = Counter(answers).most_common(1)[0]
    return answer if count >= 2 else "UNCERTAIN"


def _mean_probability(items):
    values = [item["probability_preferred_wrong"] for item in items if item]
    return sum(values) / len(values) if values else None
