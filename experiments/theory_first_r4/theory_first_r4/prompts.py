"""Frozen role and packet-only coordinator prompts."""

from __future__ import annotations

import json

from .cases import CASES, ROLE_IDS
from .schemas import COORDINATOR_BASIS, ROLE_ASSUMPTIONS, ROLE_BASIS


ROLE_SYSTEM = """You are a stateless probability-calibration role.
Use only the common prior and your assigned evidence likelihood ratio.
Return one strict JSON object with a `receipts` array and no other text.
Do not infer or request any other role's evidence or a private answer."""

COORDINATOR_SYSTEM = """You are a packet-only probability coordinator.
Use only the common prior and supplied role packets. Do not reconstruct or
request raw evidence or a private answer. Return one strict JSON object with a
`receipts` array and no other text."""


def role_prompt(role_id: str, replicate: str) -> str:
    role_index = ROLE_IDS.index(role_id)
    ordered_cases = CASES if replicate == "A" else tuple(reversed(CASES))
    cases = [
        {
            "case_id": case.case_id,
            "prior_probability_y1": case.prior_y1,
            "evidence_id": case.evidence_id(role_id),
            "assigned_likelihood_ratio": case.likelihood_ratios[role_index],
        }
        for case in ordered_cases
    ]
    wording = (
        "Convert prior odds by multiplying the assigned likelihood ratio."
        if replicate == "A"
        else "Update the prior odds using only the provided Bayes factor."
    )
    schema = {
        "case_id": "R4-01",
        "role_id": role_id,
        "evidence_id": "R4-01-E?",
        "probability_y1": 0.5,
        "direction": "Y1|Y0|UNRESOLVED",
        "calculation_basis": ROLE_BASIS,
        "assumptions": sorted(ROLE_ASSUMPTIONS),
    }
    return (
        f"{wording}\n"
        "Report probability_y1 to at least six decimal places when needed. "
        "Use UNRESOLVED only when probability_y1 equals 0.5 within 1e-6.\n"
        f"Required receipt schema example:\n{json.dumps(schema, sort_keys=True)}\n"
        f"Assigned cases:\n{json.dumps(cases, sort_keys=True)}\n"
        "Return JSON now."
    )


def coordinator_prompt(
    included_roles: tuple[str, ...],
    role_packets: dict[str, list[dict[str, object]]],
    replicate: str,
) -> str:
    case_order = [case.case_id for case in CASES]
    if replicate == "B":
        case_order.reverse()
    by_role = {
        role: {str(packet["case_id"]): packet for packet in packets}
        for role, packets in role_packets.items()
    }
    cases = []
    for case_id in case_order:
        prior = next(case.prior_y1 for case in CASES if case.case_id == case_id)
        packets = [by_role[role][case_id] for role in included_roles]
        if replicate == "B":
            packets.reverse()
        cases.append(
            {
                "case_id": case_id,
                "prior_probability_y1": prior,
                "role_packets": packets,
            }
        )
    schema = {
        "case_id": "R4-01",
        "included_roles": list(included_roles),
        "probability_y1": 0.5,
        "direction": "Y1|Y0|UNRESOLVED",
        "composition_basis": COORDINATOR_BASIS,
        "raw_evidence_used": False,
        "private_reference_used": False,
    }
    return (
        "Each packet probability was computed from the same common prior and "
        "one conditionally independent evidence item. Combine packets using:\n"
        "combined_log_odds = sum(logit(packet_probability_i)) "
        "- (m - 1) * logit(prior).\n"
        "Use only the supplied packet probabilities. Report at least six "
        "decimal places when needed. Use UNRESOLVED only at probability 0.5 "
        "within 1e-6.\n"
        f"Required receipt schema example:\n{json.dumps(schema, sort_keys=True)}\n"
        f"Packet cases:\n{json.dumps(cases, sort_keys=True)}\n"
        "Return JSON now."
    )

