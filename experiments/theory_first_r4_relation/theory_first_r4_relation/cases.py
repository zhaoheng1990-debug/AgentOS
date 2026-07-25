"""Frozen v0.3A relation graph cases."""

from __future__ import annotations

from itertools import combinations

from .contracts import CognitivePacket, PacketRelation, RelationGraphCase


def _posterior(prior: float, likelihood_ratio: float) -> float:
    odds = prior / (1.0 - prior) * likelihood_ratio
    return odds / (1.0 + odds)


def _packet(
    packet_id: str,
    likelihood_ratio: float,
    *,
    prior: float = 0.5,
    probability: float | None = None,
) -> CognitivePacket:
    return CognitivePacket(
        packet_id=packet_id,
        prior_y1=prior,
        probability_y1=(
            probability
            if probability is not None
            else _posterior(prior, likelihood_ratio)
        ),
        evidence_ref=f"evidence://{packet_id}",
    )


def _relation(left: str, right: str, state: str) -> PacketRelation:
    return PacketRelation(
        left_packet_id=left,
        right_packet_id=right,
        relation_state=state,
        evidence_refs=(f"descriptor://{left}", f"descriptor://{right}"),
    )


def _all_independent(packet_ids: tuple[str, ...]) -> tuple[PacketRelation, ...]:
    return tuple(
        _relation(left, right, "INDEPENDENT_DISTINCT")
        for left, right in combinations(packet_ids, 2)
    )


CASES = (
    RelationGraphCase(
        "R43A-01",
        (_packet("P1", 4.0), _packet("P2", 2.0)),
        (_relation("P1", "P2", "INDEPENDENT_DISTINCT"),),
        "COMBINE",
        _posterior(0.5, 8.0),
        ("P1", "P2"),
        (),
    ),
    RelationGraphCase(
        "R43A-02",
        (_packet("P1", 4.0), _packet("P2", 0.25), _packet("P3", 2.0)),
        _all_independent(("P1", "P2", "P3")),
        "COMBINE",
        _posterior(0.5, 2.0),
        ("P1", "P2", "P3"),
        (),
    ),
    RelationGraphCase(
        "R43A-03",
        (_packet("P1", 4.0), _packet("P2", 4.0)),
        (_relation("P1", "P2", "EXACT_DUPLICATE"),),
        "DEDUPE_AND_COMBINE",
        _posterior(0.5, 4.0),
        ("P1",),
        ("P2",),
    ),
    RelationGraphCase(
        "R43A-04",
        (_packet("P1", 4.0), _packet("P2", 4.0), _packet("P3", 0.5)),
        (
            _relation("P1", "P2", "EXACT_DUPLICATE"),
            _relation("P1", "P3", "INDEPENDENT_DISTINCT"),
            _relation("P2", "P3", "INDEPENDENT_DISTINCT"),
        ),
        "DEDUPE_AND_COMBINE",
        _posterior(0.5, 2.0),
        ("P1", "P3"),
        ("P2",),
    ),
    RelationGraphCase(
        "R43A-05",
        (_packet("P1", 4.0), _packet("P2", 2.0)),
        (_relation("P1", "P2", "DEPENDENT_DISTINCT"),),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-06",
        (_packet("P1", 4.0), _packet("P2", 2.0)),
        (_relation("P1", "P2", "PARTIAL_OVERLAP"),),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-07",
        (_packet("P1", 4.0), _packet("P2", 2.0)),
        (_relation("P1", "P2", "SCOPE_INCOMPATIBLE"),),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-08",
        (_packet("P1", 4.0), _packet("P2", 2.0)),
        (_relation("P1", "P2", "UNRESOLVED"),),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-09",
        (_packet("P1", 4.0), _packet("P2", 2.0), _packet("P3", 0.5)),
        (
            _relation("P1", "P2", "INDEPENDENT_DISTINCT"),
            _relation("P1", "P3", "INDEPENDENT_DISTINCT"),
        ),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-10",
        (
            _packet("P1", 4.0, probability=0.8),
            _packet("P2", 4.0, probability=0.7),
        ),
        (_relation("P1", "P2", "EXACT_DUPLICATE"),),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-11",
        (_packet("P1", 4.0), _packet("P2", 4.0), _packet("P3", 0.5)),
        (
            _relation("P1", "P2", "EXACT_DUPLICATE"),
            _relation("P1", "P3", "INDEPENDENT_DISTINCT"),
            _relation("P2", "P3", "DEPENDENT_DISTINCT"),
        ),
        "BLOCK",
        None,
        (),
        (),
    ),
    RelationGraphCase(
        "R43A-12",
        (_packet("P1", 4.0), _packet("P2", 2.0, prior=0.4)),
        (_relation("P1", "P2", "INDEPENDENT_DISTINCT"),),
        "BLOCK",
        None,
        (),
        (),
    ),
)
