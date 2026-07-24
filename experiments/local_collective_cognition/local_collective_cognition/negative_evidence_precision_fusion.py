"""Mechanical fusion for precision-confirmed negative-evidence vetoes."""

from __future__ import annotations

from collections import Counter

from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


FUSION_VERSION = "negative_evidence_precision_fusion_v0_3"
BASELINE = "BASELINE"
MONOLITHIC_REPEAT_2 = "MONOLITHIC_REPEAT_2"
MONOLITHIC_REPEAT_3 = "MONOLITHIC_REPEAT_3"
MONOLITHIC_REPEAT_4 = "MONOLITHIC_REPEAT_4"
LIVE_AMBIGUITY = "LIVE_AMBIGUITY"
FABRICATION = "FABRICATION"
VETO_CONFIRMATION = "VETO_CONFIRMATION"
MONOLITHIC_LANES = (
    BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3, MONOLITHIC_REPEAT_4,
)
PRIMARY_LANES = (*MONOLITHIC_LANES, LIVE_AMBIGUITY, FABRICATION)
LANES = (*PRIMARY_LANES, VETO_CONFIRMATION)
ARMS = (
    "SINGLE_MONOLITHIC",
    "BUDGET_CEILING_MONOLITHIC",
    "NAIVE_VETO",
    "CONFIRMED_VETO",
)
ARM_LANES = {
    "SINGLE_MONOLITHIC": (BASELINE,),
    "BUDGET_CEILING_MONOLITHIC": MONOLITHIC_LANES,
    "NAIVE_VETO": (BASELINE, LIVE_AMBIGUITY, FABRICATION),
    "CONFIRMED_VETO": (
        BASELINE, LIVE_AMBIGUITY, FABRICATION, VETO_CONFIRMATION,
    ),
}


def build_precision_fusion(*, corpus_artifact, lanes):
    monolithic = [
        _monolithic_criteria(lanes[lane]["judgments"])
        for lane in MONOLITHIC_LANES
    ]
    live = _specialist_states(lanes[LIVE_AMBIGUITY]["judgments"])
    fabrication = _specialist_states(lanes[FABRICATION]["judgments"])
    confirmation = _confirmation_states(lanes[VETO_CONFIRMATION]["judgments"])
    targets = confirmation_target_ids(lanes)
    records = []
    for blind_id in sorted(corpus_artifact["blind_surface"]["bindings"]):
        baseline = monolithic[0].get(blind_id, {})
        baseline_state = _packet_state(baseline)
        live_state = live.get(blind_id, "MISSING")
        fabrication_state = fabrication.get(blind_id, "MISSING")
        confirmation_state = confirmation.get(
            blind_id, "MISSING" if blind_id in targets else "NOT_REQUESTED",
        )
        records.append({
            "blind_candidate_id": blind_id,
            "single_monolithic_state": baseline_state,
            "budget_ceiling_monolithic_state": _packet_state(
                _supermajority_criteria(*(item.get(blind_id, {}) for item in monolithic))
            ),
            "budget_ceiling_majority_criteria": _supermajority_criteria(
                *(item.get(blind_id, {}) for item in monolithic)
            ),
            "live_ambiguity_state": live_state,
            "fabrication_state": fabrication_state,
            "confirmation_requested": blind_id in targets,
            "confirmation_state": confirmation_state,
            "naive_veto_state": _naive_veto(
                baseline_state, live_state, fabrication_state,
            ),
            "confirmed_veto_state": _confirmed_veto(
                baseline_state, live_state, fabrication_state, confirmation_state,
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
        "confirmation_target_ids": sorted(targets),
        "arm_accounting": accounting,
        "budget_ceiling_monolithic_rule": "FOUR_PASS_THREE_VOTE_CRITERION_SUPERMAJORITY",
        "naive_rule": "BASELINE_DOWNGRADED_BY_ANY_SPECIALIST_VETO",
        "confirmation_rule": "LIVE_VETO_REQUIRES_INDEPENDENT_CONFIRMATION",
        "confirmation_can_only_restore_baseline": True,
        "specialists_can_promote_baseline": False,
        "kernel_mechanical_fusion": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def confirmation_target_ids(lanes):
    baseline = _monolithic_criteria(lanes[BASELINE]["judgments"])
    live = _specialist_states(lanes[LIVE_AMBIGUITY]["judgments"])
    fabrication = _specialist_states(lanes[FABRICATION]["judgments"])
    return {
        blind_id for blind_id, criteria in baseline.items()
        if _packet_state(criteria) == "USABLE"
        and live.get(blind_id) == "VETO"
        and fabrication.get(blind_id) == "PASS"
    }


def _monolithic_criteria(judgments):
    return {
        item["blind_candidate_id"]: item["criteria"]
        for judgment in judgments
        for item in judgment["payload"]["assessments"]
    }


def _specialist_states(judgments):
    return {
        item["blind_candidate_id"]: item["state"]
        for judgment in judgments
        for item in judgment["payload"]["assessments"]
    }


def _confirmation_states(judgments):
    return {
        item["blind_candidate_id"]: item["state"]
        for judgment in judgments
        for item in judgment["payload"]["assessments"]
    }


def _supermajority_criteria(*passes):
    if any(set(item) != set(JUDGE_CRITERIA) for item in passes):
        return {}
    result = {}
    for criterion in JUDGE_CRITERIA:
        counts = Counter(item[criterion] for item in passes)
        state, count = counts.most_common(1)[0]
        result[criterion] = state if count >= 3 else "UNCERTAIN"
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


def _naive_veto(baseline, live, fabrication):
    if baseline == "UNUSABLE":
        return "UNUSABLE"
    if "VETO" in {live, fabrication}:
        return "UNUSABLE"
    if baseline == "USABLE" and {live, fabrication} == {"PASS"}:
        return "USABLE"
    return "UNRESOLVED"


def _confirmed_veto(baseline, live, fabrication, confirmation):
    if baseline == "UNUSABLE" or fabrication == "VETO":
        return "UNUSABLE"
    if baseline != "USABLE" or fabrication != "PASS":
        return "UNRESOLVED"
    if live == "PASS":
        return "USABLE"
    if live != "VETO":
        return "UNRESOLVED"
    if confirmation == "CONFIRM_VETO":
        return "UNUSABLE"
    if confirmation == "REJECT_VETO":
        return "USABLE"
    return "UNRESOLVED"
