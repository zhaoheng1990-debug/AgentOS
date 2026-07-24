"""Mechanical four-arm fusion for the negative-evidence generalization test."""

from __future__ import annotations

from collections import Counter

from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


FUSION_VERSION = "negative_evidence_four_arm_fusion_v0_2"
BASELINE = "BASELINE"
MONOLITHIC_REPEAT_2 = "MONOLITHIC_REPEAT_2"
MONOLITHIC_REPEAT_3 = "MONOLITHIC_REPEAT_3"
SAME_MODEL_LIVE = "SAME_MODEL_LIVE_AMBIGUITY"
SHARED_FABRICATION = "SHARED_FABRICATION"
HETEROGENEOUS_LIVE = "HETEROGENEOUS_LIVE_AMBIGUITY"
LANES = (
    BASELINE,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    SAME_MODEL_LIVE,
    SHARED_FABRICATION,
    HETEROGENEOUS_LIVE,
)
ARMS = (
    "SINGLE_MONOLITHIC",
    "BUDGET_MATCHED_MONOLITHIC",
    "SAME_MODEL_SPLIT",
    "HETEROGENEOUS_SPLIT",
)
ARM_LANES = {
    "SINGLE_MONOLITHIC": (BASELINE,),
    "BUDGET_MATCHED_MONOLITHIC": (
        BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3,
    ),
    "SAME_MODEL_SPLIT": (BASELINE, SAME_MODEL_LIVE, SHARED_FABRICATION),
    "HETEROGENEOUS_SPLIT": (
        BASELINE, HETEROGENEOUS_LIVE, SHARED_FABRICATION,
    ),
}


def build_four_arm_fusion(*, corpus_artifact, lanes):
    baseline_criteria = _monolithic_criteria(lanes[BASELINE]["judgments"])
    repeat_2 = _monolithic_criteria(
        lanes[MONOLITHIC_REPEAT_2]["judgments"]
    )
    repeat_3 = _monolithic_criteria(
        lanes[MONOLITHIC_REPEAT_3]["judgments"]
    )
    same_live = _specialist_states(lanes[SAME_MODEL_LIVE]["judgments"])
    fabrication = _specialist_states(
        lanes[SHARED_FABRICATION]["judgments"]
    )
    heterogeneous_live = _specialist_states(
        lanes[HETEROGENEOUS_LIVE]["judgments"]
    )
    records = []
    for blind_id in sorted(corpus_artifact["blind_surface"]["bindings"]):
        baseline = baseline_criteria.get(blind_id, {})
        majority = _majority_criteria(
            baseline,
            repeat_2.get(blind_id, {}),
            repeat_3.get(blind_id, {}),
        )
        baseline_state = _packet_state(baseline)
        same_live_state = same_live.get(blind_id, "MISSING")
        fabrication_state = fabrication.get(blind_id, "MISSING")
        heterogeneous_live_state = heterogeneous_live.get(blind_id, "MISSING")
        records.append({
            "blind_candidate_id": blind_id,
            "single_monolithic_state": baseline_state,
            "budget_matched_monolithic_state": _packet_state(majority),
            "budget_matched_majority_criteria": majority,
            "same_model_live_state": same_live_state,
            "heterogeneous_live_state": heterogeneous_live_state,
            "shared_fabrication_state": fabrication_state,
            "same_model_split_state": _veto_fusion(
                baseline_state, same_live_state, fabrication_state,
            ),
            "heterogeneous_split_state": _veto_fusion(
                baseline_state, heterogeneous_live_state, fabrication_state,
            ),
        })
    accounting = {
        arm: {
            "attributed_provider_calls": sum(
                lanes[lane]["provider_calls"] for lane in ARM_LANES[arm]
            ),
            "attributed_input_tokens": sum(
                lanes[lane]["input_tokens"] for lane in ARM_LANES[arm]
            ),
            "attributed_output_tokens": sum(
                lanes[lane]["output_tokens"] for lane in ARM_LANES[arm]
            ),
            "lanes": list(ARM_LANES[arm]),
        }
        for arm in ARMS
    }
    commitment = {
        "fusion_version": FUSION_VERSION,
        "records": records,
        "arm_accounting": accounting,
        "budget_matched_monolithic_rule": "CRITERION_WISE_MAJORITY",
        "split_rule": "BASELINE_CAN_ONLY_BE_DOWNGRADED_BY_SPECIALIST_VETO",
        "specialists_can_promote_baseline": False,
        "kernel_mechanical_fusion": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def _monolithic_criteria(judgments):
    indexed = {}
    for judgment in judgments:
        for assessment in judgment["payload"]["assessments"]:
            indexed[assessment["blind_candidate_id"]] = assessment["criteria"]
    return indexed


def _specialist_states(judgments):
    indexed = {}
    for judgment in judgments:
        for assessment in judgment["payload"]["assessments"]:
            indexed[assessment["blind_candidate_id"]] = assessment["state"]
    return indexed


def _majority_criteria(*passes):
    if any(set(item) != set(JUDGE_CRITERIA) for item in passes):
        return {}
    result = {}
    for criterion in JUDGE_CRITERIA:
        counts = Counter(item[criterion] for item in passes)
        state, count = counts.most_common(1)[0]
        result[criterion] = state if count >= 2 else "UNCERTAIN"
    return result


def _packet_state(criteria):
    if set(criteria) != set(JUDGE_CRITERIA):
        return "MISSING"
    states = set(criteria.values())
    if not states.issubset(set(JUDGE_STATES)):
        return "MISSING"
    if states == {"PRESENT"}:
        return "USABLE"
    if "ABSENT" in states:
        return "UNUSABLE"
    return "UNRESOLVED"


def _veto_fusion(baseline_state, live_state, fabrication_state):
    if baseline_state == "UNUSABLE":
        return "UNUSABLE"
    if "VETO" in {live_state, fabrication_state}:
        return "UNUSABLE"
    if baseline_state == "USABLE" and {live_state, fabrication_state} == {"PASS"}:
        return "USABLE"
    return "UNRESOLVED"
