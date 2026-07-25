"""Deterministic pre-call corpus audit for R4 v0.3E."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from .contracts import RELATION_STATES
from .hard_cases import HARD_CASES


BANNED_PUBLIC_TERMS = (
    "independent",
    "duplicate",
    "dependent",
    "overlap",
    "incompatible",
    "unresolved",
)


def audit_hard_corpus() -> dict[str, Any]:
    case_ids = [case.case_id for case in HARD_CASES]
    states = Counter(case.private_relation_state for case in HARD_CASES)
    domains = {case.domain for case in HARD_CASES}
    packet_ids = [
        packet_id
        for case in HARD_CASES
        for packet_id in (case.left_packet_id, case.right_packet_id)
    ]
    evidence_refs = [
        evidence_ref
        for case in HARD_CASES
        for evidence_ref in case.evidence_refs
    ]
    public = json.dumps(
        [case.public_dict() for case in HARD_CASES],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    lowered = public.lower()
    non_unresolved = [
        case for case in HARD_CASES if case.private_relation_state != "UNRESOLVED"
    ]
    unresolved = [
        case for case in HARD_CASES if case.private_relation_state == "UNRESOLVED"
    ]
    gates = {
        "case_count_and_identity": len(HARD_CASES) == 18
        and len(set(case_ids)) == 18
        and all(case_id.startswith("R43E-") for case_id in case_ids),
        "state_balance": states == Counter({state: 3 for state in RELATION_STATES}),
        "domain_diversity": len(domains) >= 12,
        "packet_and_evidence_identity": len(packet_ids) == len(set(packet_ids))
        and len(evidence_refs) == len(set(evidence_refs))
        and all(len(case.evidence_refs) == 2 for case in HARD_CASES),
        "lexical_decueing": not any(term in lowered for term in BANNED_PUBLIC_TERMS),
        "private_surface_absent": not any(
            value in public
            for value in (
                "private_relation_state",
                "private_action",
                "private_adjudication_basis",
                "COMBINE",
                "DEDUPE_AND_COMBINE",
                "BLOCK",
            )
        ),
        "non_unresolved_adjudication": all(
            case.private_adjudication_basis
            and case.private_ruled_out_neighbor in RELATION_STATES
            and case.private_ruled_out_neighbor != case.private_relation_state
            and not case.private_compatible_states
            for case in non_unresolved
        ),
        "unresolved_adjudication": len(unresolved) == 3
        and all(
            case.private_adjudication_basis
            and case.private_ruled_out_neighbor is None
            and len(set(case.private_compatible_states)) >= 2
            and all(state in RELATION_STATES for state in case.private_compatible_states)
            for case in unresolved
        ),
        "old_case_ids_absent": "R43B-" not in public,
    }
    return {
        "audit_version": "agentos_r4_hard_corpus_audit_v0_3e",
        "status": "PASS" if all(gates.values()) else "FAIL",
        "case_count": len(HARD_CASES),
        "state_counts": dict(sorted(states.items())),
        "domain_count": len(domains),
        "banned_public_terms": list(BANNED_PUBLIC_TERMS),
        "gates": gates,
        "gate_pass_count": sum(gates.values()),
        "gate_count": len(gates),
    }

