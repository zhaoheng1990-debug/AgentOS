"""Mechanical fusion for naive replication and structured semantic defer."""

from __future__ import annotations

from collections import Counter

from .negative_evidence_structured_contracts import derive_structured_state
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


FUSION_VERSION = "negative_evidence_structured_fusion_v0_4"
BASELINE = "BASELINE"
MONOLITHIC_REPEAT_2 = "MONOLITHIC_REPEAT_2"
MONOLITHIC_REPEAT_3 = "MONOLITHIC_REPEAT_3"
LEGACY_LIVE = "LEGACY_LIVE_AMBIGUITY"
STRUCTURED_LIVE = "STRUCTURED_LIVE_AMBIGUITY"
FABRICATION = "FABRICATION"
MONOLITHIC_LANES = (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3)
LANES = (*MONOLITHIC_LANES, LEGACY_LIVE, STRUCTURED_LIVE, FABRICATION)
ARMS = ("SINGLE_MONOLITHIC", "BUDGET_MATCHED_MONOLITHIC", "NAIVE_REPLICATION", "STRUCTURED_DEFER")
ARM_LANES = {
    "SINGLE_MONOLITHIC": (BASELINE,),
    "BUDGET_MATCHED_MONOLITHIC": MONOLITHIC_LANES,
    "NAIVE_REPLICATION": (BASELINE, LEGACY_LIVE, FABRICATION),
    "STRUCTURED_DEFER": (BASELINE, STRUCTURED_LIVE, FABRICATION),
}


def build_structured_fusion(*, corpus_artifact, lanes):
    passes = [_monolithic(lanes[lane]["judgments"]) for lane in MONOLITHIC_LANES]
    legacy = _specialist(lanes[LEGACY_LIVE]["judgments"])
    structured = _structured(lanes[STRUCTURED_LIVE]["judgments"])
    fabrication = _specialist(lanes[FABRICATION]["judgments"])
    records = []
    for blind_id in sorted(corpus_artifact["blind_surface"]["bindings"]):
        baseline = _packet_state(passes[0].get(blind_id, {}))
        legacy_state = legacy.get(blind_id, "MISSING")
        structured_state = structured.get(blind_id, "MISSING")
        fabrication_state = fabrication.get(blind_id, "MISSING")
        majority = _majority(*(item.get(blind_id, {}) for item in passes))
        records.append({
            "blind_candidate_id": blind_id,
            "single_monolithic_state": baseline,
            "budget_matched_monolithic_state": _packet_state(majority),
            "budget_matched_majority_criteria": majority,
            "legacy_live_state": legacy_state,
            "structured_live_state": structured_state,
            "fabrication_state": fabrication_state,
            "naive_replication_state": _veto_fusion(baseline, legacy_state, fabrication_state),
            "structured_defer_state": _veto_fusion(baseline, structured_state, fabrication_state),
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
        "fusion_version": FUSION_VERSION, "records": records,
        "arm_accounting": accounting,
        "budget_matched_rule": "THREE_PASS_CRITERION_MAJORITY",
        "structured_state_rule": "RUNTIME_DERIVED_FROM_PROVIDER_SEMANTIC_SUBJUDGMENTS",
        "specialists_can_promote_baseline": False,
        "kernel_mechanical_fusion": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def _monolithic(judgments):
    return {a["blind_candidate_id"]: a["criteria"] for j in judgments for a in j["payload"]["assessments"]}


def _specialist(judgments):
    return {a["blind_candidate_id"]: a["state"] for j in judgments for a in j["payload"]["assessments"]}


def _structured(judgments):
    return {a["blind_candidate_id"]: derive_structured_state(a) for j in judgments for a in j["payload"]["assessments"]}


def _majority(*passes):
    if any(set(item) != set(JUDGE_CRITERIA) for item in passes):
        return {}
    result = {}
    for criterion in JUDGE_CRITERIA:
        state, count = Counter(item[criterion] for item in passes).most_common(1)[0]
        result[criterion] = state if count >= 2 else "UNCERTAIN"
    return result


def _packet_state(criteria):
    if set(criteria) != set(JUDGE_CRITERIA) or not set(criteria.values()).issubset(set(JUDGE_STATES)):
        return "MISSING"
    states = set(criteria.values())
    return "USABLE" if states == {"PRESENT"} else "UNUSABLE" if "ABSENT" in states else "UNRESOLVED"


def _veto_fusion(baseline, live, fabrication):
    if baseline == "UNUSABLE" or "VETO" in {live, fabrication}:
        return "UNUSABLE"
    if baseline == "USABLE" and {live, fabrication} == {"PASS"}:
        return "USABLE"
    return "UNRESOLVED"
