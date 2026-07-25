"""Strict Provider receipt parsing and validation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .cases import CASES, ROLE_IDS


ROLE_BASIS = "PRIOR_ODDS_TIMES_ASSIGNED_LR"
ROLE_ASSUMPTIONS = {"ONLY_ASSIGNED_EVIDENCE", "COMMON_PRIOR"}
COORDINATOR_BASIS = "PACKET_LOG_ODDS_WITH_SHARED_PRIOR_REMOVAL"


@dataclass(frozen=True)
class RoleReceipt:
    case_id: str
    role_id: str
    evidence_id: str
    probability_y1: float
    direction: str
    calculation_basis: str
    assumptions: tuple[str, ...]


@dataclass(frozen=True)
class CoordinatorReceipt:
    case_id: str
    included_roles: tuple[str, ...]
    probability_y1: float
    direction: str
    composition_basis: str
    raw_evidence_used: bool
    private_reference_used: bool


def expected_direction(probability_y1: float) -> str:
    if abs(probability_y1 - 0.5) <= 1e-6:
        return "UNRESOLVED"
    return "Y1" if probability_y1 > 0.5 else "Y0"


def _root_receipts(content: str) -> list[dict[str, Any]]:
    parsed = json.loads(content)
    if not isinstance(parsed, dict) or not isinstance(parsed.get("receipts"), list):
        raise ValueError("root must be an object with a receipts array")
    return parsed["receipts"]


def _probability(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("probability_y1 must be numeric")
    probability = float(value)
    if not 0.0 < probability < 1.0:
        raise ValueError("probability_y1 must be strictly between zero and one")
    return probability


def parse_role_receipts(content: str, role_id: str) -> list[RoleReceipt]:
    if role_id not in ROLE_IDS:
        raise ValueError("unknown role")
    expected_cases = {case.case_id: case for case in CASES}
    receipts = []
    for item in _root_receipts(content):
        if not isinstance(item, dict):
            raise ValueError("role receipt must be an object")
        case_id = str(item.get("case_id", ""))
        if case_id not in expected_cases:
            raise ValueError(f"unexpected case_id: {case_id}")
        if item.get("role_id") != role_id:
            raise ValueError(f"role mismatch for {case_id}")
        expected_evidence = expected_cases[case_id].evidence_id(role_id)
        if item.get("evidence_id") != expected_evidence:
            raise ValueError(f"evidence mismatch for {case_id}")
        probability = _probability(item.get("probability_y1"))
        direction = str(item.get("direction", ""))
        if direction != expected_direction(probability):
            raise ValueError(f"direction mismatch for {case_id}")
        if item.get("calculation_basis") != ROLE_BASIS:
            raise ValueError(f"basis mismatch for {case_id}")
        assumptions = item.get("assumptions")
        if not isinstance(assumptions, list) or set(assumptions) != ROLE_ASSUMPTIONS:
            raise ValueError(f"assumption mismatch for {case_id}")
        receipts.append(
            RoleReceipt(
                case_id=case_id,
                role_id=role_id,
                evidence_id=expected_evidence,
                probability_y1=probability,
                direction=direction,
                calculation_basis=ROLE_BASIS,
                assumptions=tuple(str(value) for value in assumptions),
            )
        )
    if len(receipts) != len(CASES) or len({item.case_id for item in receipts}) != len(
        CASES
    ):
        raise ValueError("role case coverage must be exact")
    return sorted(receipts, key=lambda item: item.case_id)


def parse_coordinator_receipts(
    content: str, included_roles: tuple[str, ...]
) -> list[CoordinatorReceipt]:
    expected_cases = {case.case_id for case in CASES}
    expected_roles = set(included_roles)
    receipts = []
    for item in _root_receipts(content):
        if not isinstance(item, dict):
            raise ValueError("coordinator receipt must be an object")
        case_id = str(item.get("case_id", ""))
        if case_id not in expected_cases:
            raise ValueError(f"unexpected case_id: {case_id}")
        roles = item.get("included_roles")
        if not isinstance(roles, list) or set(roles) != expected_roles:
            raise ValueError(f"included_roles mismatch for {case_id}")
        probability = _probability(item.get("probability_y1"))
        direction = str(item.get("direction", ""))
        if direction != expected_direction(probability):
            raise ValueError(f"direction mismatch for {case_id}")
        if item.get("composition_basis") != COORDINATOR_BASIS:
            raise ValueError(f"composition basis mismatch for {case_id}")
        if item.get("raw_evidence_used") is not False:
            raise ValueError(f"raw evidence attestation failed for {case_id}")
        if item.get("private_reference_used") is not False:
            raise ValueError(f"private reference attestation failed for {case_id}")
        receipts.append(
            CoordinatorReceipt(
                case_id=case_id,
                included_roles=tuple(sorted(str(role) for role in roles)),
                probability_y1=probability,
                direction=direction,
                composition_basis=COORDINATOR_BASIS,
                raw_evidence_used=False,
                private_reference_used=False,
            )
        )
    if len(receipts) != len(CASES) or len({item.case_id for item in receipts}) != len(
        CASES
    ):
        raise ValueError("coordinator case coverage must be exact")
    return sorted(receipts, key=lambda item: item.case_id)

