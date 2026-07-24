"""Mechanical fusion for naive veto and execution-warranted veto."""

from __future__ import annotations

from collections import Counter

from .negative_evidence_warrant_contracts import derive_runtime_warrant_state
from .provider_telemetry import hash_payload
from .structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_STATES


FUSION_VERSION = "negative_evidence_warrant_fusion_v0_5"
BASELINE = "BASELINE"
MONOLITHIC_REPEAT_2 = "MONOLITHIC_REPEAT_2"
MONOLITHIC_REPEAT_3 = "MONOLITHIC_REPEAT_3"
LEGACY_LIVE = "LEGACY_LIVE_AMBIGUITY"
WARRANT_LIVE = "WARRANT_LIVE_AMBIGUITY"
FABRICATION = "FABRICATION"
MONOLITHIC_LANES = (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3)
LANES = (*MONOLITHIC_LANES, LEGACY_LIVE, WARRANT_LIVE, FABRICATION)
ARMS = ("SINGLE_MONOLITHIC", "BUDGET_MATCHED_MONOLITHIC", "NAIVE_REPLICATION", "WARRANTED_VETO")
ARM_LANES = {
    "SINGLE_MONOLITHIC": (BASELINE,),
    "BUDGET_MATCHED_MONOLITHIC": MONOLITHIC_LANES,
    "NAIVE_REPLICATION": (BASELINE, LEGACY_LIVE, FABRICATION),
    "WARRANTED_VETO": (BASELINE, WARRANT_LIVE, FABRICATION),
}


def build_warrant_fusion(*, corpus_artifact, lanes):
    passes = [_monolithic(lanes[lane]["judgments"]) for lane in MONOLITHIC_LANES]
    legacy = _specialist(lanes[LEGACY_LIVE]["judgments"])
    warrants = _warrants(lanes[WARRANT_LIVE]["judgments"])
    fabrication = _specialist(lanes[FABRICATION]["judgments"])
    prompts = {
        item["blind_candidate_id"]: item["public_prompt"]
        for batch in corpus_artifact["blind_surface"]["batches"]
        for item in batch["public_candidates"]
    }
    records = []
    for blind_id in sorted(corpus_artifact["blind_surface"]["bindings"]):
        baseline = _packet_state(passes[0].get(blind_id, {}))
        legacy_state = legacy.get(blind_id, "MISSING")
        fabrication_state = fabrication.get(blind_id, "MISSING")
        assessment = warrants.get(blind_id)
        runtime_warrant = (
            derive_runtime_warrant_state(assessment, public_prompt=prompts[blind_id])
            if assessment else "MISSING"
        )
        majority = _majority(*(item.get(blind_id, {}) for item in passes))
        records.append({
            "blind_candidate_id": blind_id,
            "single_monolithic_state": baseline,
            "budget_matched_monolithic_state": _packet_state(majority),
            "budget_matched_majority_criteria": majority,
            "legacy_live_state": legacy_state,
            "warrant_provider_state": assessment["provider_state"] if assessment else "MISSING",
            "warrant_kind": assessment["warrant_kind"] if assessment else "MISSING",
            "runtime_warrant_state": runtime_warrant,
            "fabrication_state": fabrication_state,
            "naive_replication_state": _naive_veto(baseline, legacy_state, fabrication_state),
            "warranted_veto_state": _warranted_veto(baseline, runtime_warrant, fabrication_state),
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
        "budget_matched_rule": "THREE_PASS_CRITERION_MAJORITY",
        "warrant_execution_rule": "EXACT_QUOTE_FIXATION_OR_PROVIDER_RIVAL_INVALIDITY_OR_EQUIVALENCE",
        "question_ineffective_only_has_veto_authority": False,
        "non_executable_veto_restores_usable_baseline": True,
        "specialists_can_promote_baseline": False,
        "kernel_mechanical_fusion": True,
    }
    return {**commitment, "fusion_hash": hash_payload(commitment)}


def _monolithic(judgments):
    return {item["blind_candidate_id"]: item["criteria"] for judgment in judgments for item in judgment["payload"]["assessments"]}


def _specialist(judgments):
    return {item["blind_candidate_id"]: item["state"] for judgment in judgments for item in judgment["payload"]["assessments"]}


def _warrants(judgments):
    return {item["blind_candidate_id"]: item for judgment in judgments for item in judgment["payload"]["assessments"]}


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


def _naive_veto(baseline, live, fabrication):
    if baseline == "UNUSABLE" or "VETO" in {live, fabrication}:
        return "UNUSABLE"
    if baseline == "USABLE" and {live, fabrication} == {"PASS"}:
        return "USABLE"
    return "UNRESOLVED"


def _warranted_veto(baseline, warrant, fabrication):
    if baseline == "UNUSABLE" or fabrication == "VETO" or warrant == "EXECUTABLE_VETO":
        return "UNUSABLE"
    if baseline == "USABLE" and fabrication == "PASS" and warrant in {"NO_EXECUTABLE_VETO", "NON_EXECUTABLE_VETO"}:
        return "USABLE"
    return "UNRESOLVED"
