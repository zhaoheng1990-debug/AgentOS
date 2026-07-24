"""Compete stop, one-peer verification, and majority by structural utility."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan, CostAwareReviewPolicy
from .hierarchical_fingerprint_credit import HierarchicalFingerprintProfile
from .routing_calibration import ReviewerValueLedger
from .structural_operator_credit import StructuralOperatorCreditSnapshot


@dataclass(frozen=True)
class StructuralOperatorDecision:
    item_id: str
    primary_model_id: str
    reviewer_model_id: str
    peer_model_ids: tuple[str, ...]
    action: str
    primary_utility: float
    expected_correction: float
    expected_harm: float
    expected_net_cbit: float
    future_information_cbit: float
    expected_extra_calls: int
    work_penalty: float
    operator_utility: float
    primary_answer: str
    reason: str
    resolution_policy: str = ""
    resolution_expected_correction: float = 0.0
    resolution_expected_harm: float = 0.0
    resolution_expected_net_cbit: float = 0.0
    resolution_evidence_level: str = ""
    resolution_exploration: bool = False
    context_model_id: str = ""
    context_support_topology: str = ""
    context_expected_net_cbit: float = 0.0
    context_pair_correction_surplus: int = 0
    context_pair_evidence_count: int = 0
    context_witness_used: bool = False
    case_adjudication_used: bool = False
    case_judge_model_id: str = ""
    case_selected_candidate: str = ""
    case_adjudicability: str = ""
    case_confidence: float = 0.0
    case_decisive_reason: str = ""
    case_argument_hashes: tuple[str, ...] = ()
    case_judgment_hash: str = ""
    final_answer: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__, "peer_model_ids": list(self.peer_model_ids),
            "case_argument_hashes": list(self.case_argument_hashes),
        }


def ranked_context_models(
    *,
    profiles: dict[str, HierarchicalFingerprintProfile],
    fingerprint: str,
    domain: str,
) -> tuple[str, ...]:
    minimum_work = min(item.expected_work() for item in profiles.values())
    ranked = sorted(
        profiles.values(),
        key=lambda item: (
            0.75 * item.context_reliability(fingerprint, domain) + 0.25 * item.global_posterior
            - 0.04 * (item.expected_work() / minimum_work - 1.0),
            item.model_id,
        ),
        reverse=True,
    )
    return tuple(item.model_id for item in ranked)


def build_second_ranked_model_map(
    *,
    profiles: dict[str, HierarchicalFingerprintProfile],
    item_domains: dict[str, str],
    item_fingerprints: dict[str, str],
) -> dict[str, str]:
    if set(item_domains) != set(item_fingerprints):
        raise ValueError("structural_operator_rank_scope_invalid")
    return {
        item_id: ranked_context_models(
            profiles=profiles, fingerprint=item_fingerprints[item_id], domain=item_domains[item_id]
        )[1]
        for item_id in item_domains
    }


def build_structural_operator_schedule(
    *,
    profiles: dict[str, HierarchicalFingerprintProfile],
    operator_credit: StructuralOperatorCreditSnapshot,
    item_domains: dict[str, str],
    item_fingerprints: dict[str, str],
    budget: int = 4,
    information_value_weight: float = 0.5,
    work_cost_weight: float = 0.02,
) -> dict[str, str]:
    if budget < 0 or budget > len(item_domains) or set(item_domains) != set(item_fingerprints):
        raise ValueError("structural_operator_schedule_inputs_invalid")
    minimum_work = min(item.expected_work() for item in profiles.values())
    candidates = []
    for item_id, fingerprint in item_fingerprints.items():
        domain = item_domains[item_id]
        ranked_ids = ranked_context_models(profiles=profiles, fingerprint=fingerprint, domain=domain)
        primary = profiles[ranked_ids[0]]
        primary_success = 0.75 * primary.context_reliability(fingerprint, domain) + 0.25 * primary.global_posterior
        peer_work = profiles[ranked_ids[1]].expected_work() / minimum_work
        majority_work = sum(profiles[model_id].expected_work() for model_id in ranked_ids[1:]) / minimum_work
        values = (
            _operator_value(operator_credit.get(fingerprint, "PEER_SECOND"), primary_success, peer_work, information_value_weight, work_cost_weight),
            _operator_value(operator_credit.get(fingerprint, "MAJORITY"), primary_success, majority_work, information_value_weight, work_cost_weight),
        )
        utility, operator_id = max((values[0], "PEER_SECOND"), (values[1], "MAJORITY"))
        if utility > 0.0:
            candidates.append((utility, item_id, operator_id))
    return {item_id: operator_id for _, item_id, operator_id in sorted(candidates, reverse=True)[:budget]}


class StructuralOperatorCompetitionPolicy:
    def __init__(
        self,
        *,
        operator_credit: StructuralOperatorCreditSnapshot,
        operator_schedule: dict[str, str],
        item_fingerprints: dict[str, str],
        information_value_weight: float = 0.5,
        work_cost_weight: float = 0.02,
    ) -> None:
        if not set(operator_schedule).issubset(item_fingerprints) or not set(operator_schedule.values()).issubset({"PEER_SECOND", "MAJORITY"}):
            raise ValueError("structural_operator_policy_schedule_invalid")
        self.operator_credit = operator_credit
        self.operator_schedule = dict(operator_schedule)
        self.item_fingerprints = dict(item_fingerprints)
        self.information_value_weight = information_value_weight
        self.work_cost_weight = work_cost_weight
        self.base = CostAwareReviewPolicy()

    def select_primary(self, plans: tuple[CalibratedModelPlan, ...]) -> CalibratedModelPlan:
        return self.base.select_primary(plans)

    def route(self, primary, *, plans, domain: str, reviewer_ledger: ReviewerValueLedger) -> StructuralOperatorDecision:
        del reviewer_ledger
        plan_by_model = {item.model_id: item for item in plans}
        if primary.model_id not in plan_by_model:
            raise ValueError("structural_operator_primary_binding_invalid")
        minimum_work = min(item.expected_work for item in plans)
        primary_utility = self.base._primary_utility(plan_by_model[primary.model_id], minimum_work)
        operator_id = self.operator_schedule.get(primary.item_id, "STOP")
        common = {
            "item_id": primary.item_id, "primary_model_id": primary.model_id,
            "primary_utility": primary_utility, "primary_answer": primary.answer,
        }
        if operator_id == "STOP":
            return StructuralOperatorDecision(
                **common, reviewer_model_id="", peer_model_ids=(), action="STOP_OPERATOR_COMPETITION",
                expected_correction=0.0, expected_harm=0.0, expected_net_cbit=0.0,
                future_information_cbit=0.0, expected_extra_calls=0, work_penalty=0.0,
                operator_utility=0.0, reason="stop_wins_structural_operator_competition", final_answer=primary.answer,
            )
        peers = sorted(
            (item for item in plans if item.model_id != primary.model_id),
            key=lambda item: (item.predicted_success, item.model_id), reverse=True,
        )
        selected = peers[:1] if operator_id == "PEER_SECOND" else peers
        extra_work = sum(item.expected_work for item in selected) / minimum_work
        credit = self.operator_credit.get(self.item_fingerprints[primary.item_id], operator_id)
        correction = (1.0 - primary.calibrated_success) * credit.correction_posterior
        harm = primary.calibrated_success * credit.harm_posterior
        immediate = correction - harm
        future = self.information_value_weight * credit.future_information_cbit
        work_penalty = self.work_cost_weight * extra_work
        utility = immediate + future - work_penalty
        if utility <= 0.0:
            return StructuralOperatorDecision(
                **common, reviewer_model_id="", peer_model_ids=(), action="STOP_RUNTIME_OPERATOR_UTILITY",
                expected_correction=round(correction, 12), expected_harm=round(harm, 12),
                expected_net_cbit=round(immediate, 12), future_information_cbit=round(future, 12),
                expected_extra_calls=0, work_penalty=round(work_penalty, 12), operator_utility=round(utility, 12),
                reason="current_signal_reduces_operator_utility_below_zero", final_answer=primary.answer,
            )
        action = "VERIFY_PEER" if operator_id == "PEER_SECOND" else "ARBITRATE_MAJORITY"
        return StructuralOperatorDecision(
            **common, reviewer_model_id=selected[0].model_id if operator_id == "PEER_SECOND" else "MAJORITY_OPERATOR",
            peer_model_ids=tuple(item.model_id for item in selected), action=action,
            expected_correction=round(correction, 12), expected_harm=round(harm, 12),
            expected_net_cbit=round(immediate, 12), future_information_cbit=round(future, 12),
            expected_extra_calls=len(selected), work_penalty=round(work_penalty, 12),
            operator_utility=round(utility, 12), reason="operator_clears_immediate_information_cost_competition",
        )

    @staticmethod
    def resolve_probe(decision, primary: CalibratedCandidateSignal, peer: CalibratedCandidateSignal):
        if decision.action != "VERIFY_PEER" or decision.reviewer_model_id != peer.model_id:
            raise ValueError("structural_peer_resolution_binding_invalid")
        if primary.answer == peer.answer:
            answer, reason = primary.answer, "peer_verification_agreement"
        elif peer.calibrated_success > primary.calibrated_success:
            answer, reason = peer.answer, "peer_contextual_override"
        else:
            answer, reason = primary.answer, "primary_survived_peer_verification"
        return StructuralOperatorDecision(
            **{**decision.__dict__, "action": "PEER_VERIFICATION_RESOLVED", "reason": reason, "final_answer": answer}
        )

    @staticmethod
    def resolve_majority(decision, primary, peers):
        if decision.action != "ARBITRATE_MAJORITY" or {item.model_id for item in peers} != set(decision.peer_model_ids):
            raise ValueError("structural_majority_resolution_binding_invalid")
        signals = (primary, *peers)
        counts = {answer: sum(item.answer == answer for item in signals) for answer in {item.answer for item in signals}}
        answer, votes = max(counts.items(), key=lambda item: (item[1], item[0]))
        if votes == 1:
            answer = max(signals, key=lambda item: (item.calibrated_success, item.model_id)).answer
            reason = "all_disagree_contextual_fallback"
        else:
            reason = "strict_peer_majority"
        return StructuralOperatorDecision(
            **{**decision.__dict__, "action": "MAJORITY_RESOLVED", "reason": reason, "final_answer": answer}
        )


def _operator_value(credit, primary_success, extra_work, information_weight, work_weight):
    immediate = (1.0 - primary_success) * credit.correction_posterior - primary_success * credit.harm_posterior
    return immediate + information_weight * credit.future_information_cbit - work_weight * extra_work
