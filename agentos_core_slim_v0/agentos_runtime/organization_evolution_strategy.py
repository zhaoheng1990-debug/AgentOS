"""Mechanical operator allocation, winner selection, and credit updates."""

from __future__ import annotations

from agentos_kernel.organization_evolution_eval import (
    OrganizationEvolutionDecision,
    OrganizationHarnessOutcome,
    OrganizationOperatorCredit,
)
from agentos_kernel.organization_evolution_models import (
    ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES,
    OrganizationMutationProposal,
)


class OrganizationEvolutionStrategy:
    """Adapt search allocation from observed credit without semantic guessing."""

    @staticmethod
    def operator_window(
        *,
        applicable: tuple[str, ...],
        credits: tuple[OrganizationOperatorCredit, ...],
        limit: int,
    ) -> tuple[str, ...]:
        by_id = {item.operator_id: item for item in credits}

        def rank(operator_id: str) -> tuple[int, float, str]:
            credit = by_id[operator_id]
            return (int(credit.trials > 0), -credit.mean_reward(), operator_id)

        exploration = sorted(
            (item for item in applicable if ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES[item] == "EXPLORATION"),
            key=rank,
        )
        exploitation = sorted(
            (item for item in applicable if ORGANIZATION_EVOLUTION_OPERATOR_FAMILIES[item] == "EXPLOITATION"),
            key=rank,
        )
        selected: list[str] = []
        if limit >= 2 and exploration and exploitation:
            selected.extend((exploration.pop(0), exploitation.pop(0)))
        for item in sorted((*exploration, *exploitation), key=rank):
            if len(selected) >= limit:
                break
            selected.append(item)
        return tuple(selected or sorted(applicable, key=rank)[:limit])

    @staticmethod
    def winner_index(decisions: tuple[OrganizationEvolutionDecision, ...]) -> int | None:
        eligible = [(index, item) for index, item in enumerate(decisions) if item.accepted]
        if not eligible:
            return None
        return max(eligible, key=lambda pair: (pair[1].candidate_utility, pair[1].primary_score_delta))[0]

    @staticmethod
    def updated_credits(
        *,
        credits: tuple[OrganizationOperatorCredit, ...],
        proposals: tuple[OrganizationMutationProposal, ...],
        outcomes: tuple[OrganizationHarnessOutcome, ...],
        decisions: tuple[OrganizationEvolutionDecision, ...],
        winner_index: int | None,
    ) -> tuple[OrganizationOperatorCredit, ...]:
        by_id = {item.operator_id: item for item in credits}
        for index, (proposal, outcome, decision) in enumerate(zip(proposals, outcomes, decisions, strict=True)):
            by_id[proposal.operator_id] = by_id[proposal.operator_id].update(
                utility_delta=decision.utility_delta,
                cost=outcome.normalized_cost,
                retained=index == winner_index,
            )
        return tuple(by_id[key] for key in sorted(by_id))
