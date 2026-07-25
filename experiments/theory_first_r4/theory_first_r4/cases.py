"""Frozen R4 probability objects and private exact references."""

from __future__ import annotations

from dataclasses import dataclass
from functools import reduce
from operator import mul


ROLE_IDS = ("ROLE_A", "ROLE_B", "ROLE_C")


@dataclass(frozen=True)
class Case:
    case_id: str
    prior_y1: float
    likelihood_ratios: tuple[float, float, float]

    def evidence_id(self, role_id: str) -> str:
        suffix = {"ROLE_A": "EA", "ROLE_B": "EB", "ROLE_C": "EC"}[role_id]
        return f"{self.case_id}-{suffix}"


CASES = (
    Case("R4-01", 0.50, (4.00, 2.50, 0.40)),
    Case("R4-02", 0.50, (0.25, 0.40, 2.50)),
    Case("R4-03", 0.35, (4.00, 0.67, 1.50)),
    Case("R4-04", 0.65, (0.25, 1.50, 0.67)),
    Case("R4-05", 0.20, (4.00, 4.00, 0.67)),
    Case("R4-06", 0.80, (0.25, 0.25, 1.50)),
    Case("R4-07", 0.50, (1.50, 0.67, 1.00)),
    Case("R4-08", 0.35, (2.50, 0.40, 1.00)),
    Case("R4-09", 0.65, (0.40, 2.50, 1.00)),
    Case("R4-10", 0.50, (4.00, 0.25, 1.00)),
    Case("R4-11", 0.20, (2.50, 2.50, 0.40)),
    Case("R4-12", 0.80, (0.40, 0.40, 2.50)),
)


def posterior(case: Case, roles: tuple[str, ...]) -> float:
    prior_odds = case.prior_y1 / (1.0 - case.prior_y1)
    role_indices = {role: index for index, role in enumerate(ROLE_IDS)}
    likelihood_product = reduce(
        mul,
        (case.likelihood_ratios[role_indices[role]] for role in roles),
        1.0,
    )
    posterior_odds = prior_odds * likelihood_product
    return posterior_odds / (1.0 + posterior_odds)


def exact_reference() -> dict[str, dict[str, float]]:
    subsets = (
        (),
        ("ROLE_A",),
        ("ROLE_B",),
        ("ROLE_C",),
        ("ROLE_A", "ROLE_B"),
        ("ROLE_A", "ROLE_C"),
        ("ROLE_B", "ROLE_C"),
        ROLE_IDS,
    )
    return {
        case.case_id: {
            "+".join(roles) if roles else "PRIOR": posterior(case, roles)
            for roles in subsets
        }
        for case in CASES
    }

