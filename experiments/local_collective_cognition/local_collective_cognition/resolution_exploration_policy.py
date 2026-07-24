"""Bounded exploration for sparse disagreement-resolution fingerprints."""

from __future__ import annotations

from .independent_resolution_policy import IndependentDisagreementResolutionPolicy
from .structural_operator_policy import StructuralOperatorDecision


def build_resolution_exploration_schedule(
    *,
    resolution_credit,
    item_fingerprints: dict[str, str],
    existing_schedule: dict[str, str],
    budget: int = 2,
) -> dict[str, str]:
    if budget < 0 or budget > len(item_fingerprints) or not set(existing_schedule).issubset(item_fingerprints):
        raise ValueError("resolution_exploration_schedule_invalid")
    level_priority = {"GLOBAL": 3, "DOMAIN": 2, "FINGERPRINT": 1}
    candidates = []
    for item_id, fingerprint in item_fingerprints.items():
        if item_id in existing_schedule:
            continue
        credit = resolution_credit.get(fingerprint)
        uncertainty = 1.0 - min(1.0, abs(credit.expected_override_net_cbit))
        sparsity = 1.0 / (1.0 + credit.effective_disagreements)
        score = level_priority[credit.evidence_level] + uncertainty + sparsity
        candidates.append((score, item_id))
    return {item_id: "PEER_SECOND" for _, item_id in sorted(candidates, reverse=True)[:budget]}


class ResolutionExplorationPolicy(IndependentDisagreementResolutionPolicy):
    def __init__(self, *, exploration_items: tuple[str, ...], **values) -> None:
        super().__init__(**values)
        if not set(exploration_items).issubset(self.operator_schedule):
            raise ValueError("resolution_exploration_policy_scope_invalid")
        self.exploration_items = frozenset(exploration_items)

    def route(self, primary, *, plans, domain, reviewer_ledger) -> StructuralOperatorDecision:
        decision = super().route(
            primary, plans=plans, domain=domain, reviewer_ledger=reviewer_ledger,
        )
        if primary.item_id not in self.exploration_items:
            return decision
        peers = sorted(
            (item for item in plans if item.model_id != primary.model_id),
            key=lambda item: (item.predicted_success, item.model_id), reverse=True,
        )
        if not peers:
            raise ValueError("resolution_exploration_peer_missing")
        peer = peers[0]
        credit = self.resolution_credit.get(self.item_fingerprints[primary.item_id])
        minimum_work = min(item.expected_work for item in plans)
        work_penalty = self.work_cost_weight * peer.expected_work / minimum_work
        information = (1.0 - min(1.0, abs(credit.expected_override_net_cbit))) / (
            1.0 + credit.effective_disagreements
        )
        utility = information - work_penalty
        if utility <= 0.0:
            return StructuralOperatorDecision(**{
                **decision.__dict__, "action": "STOP_RESOLUTION_EXPLORATION_COST",
                "reason": "resolution_exploration_information_below_work_cost",
                "resolution_exploration": True,
            })
        return StructuralOperatorDecision(**{
            **decision.__dict__,
            "reviewer_model_id": peer.model_id,
            "peer_model_ids": (peer.model_id,),
            "action": "VERIFY_PEER",
            "expected_extra_calls": 1,
            "future_information_cbit": round(information, 12),
            "work_penalty": round(work_penalty, 12),
            "operator_utility": round(utility, 12),
            "reason": "bounded_resolution_uncertainty_exploration",
            "resolution_exploration": True,
            "final_answer": "",
        })
