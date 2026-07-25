"""Typed candidate contracts for relation-aware packet composition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any


RELATION_STATES = (
    "INDEPENDENT_DISTINCT",
    "EXACT_DUPLICATE",
    "DEPENDENT_DISTINCT",
    "PARTIAL_OVERLAP",
    "SCOPE_INCOMPATIBLE",
    "UNRESOLVED",
)
PLAN_ACTIONS = ("COMBINE", "DEDUPE_AND_COMBINE", "BLOCK")


def hash_payload(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class CognitivePacket:
    packet_id: str
    prior_y1: float
    probability_y1: float
    evidence_ref: str

    def __post_init__(self) -> None:
        if not self.packet_id or not self.evidence_ref:
            raise ValueError("packet identity and evidence reference are required")
        if not 0.0 < self.prior_y1 < 1.0:
            raise ValueError("packet prior must be between zero and one")
        if not 0.0 < self.probability_y1 < 1.0:
            raise ValueError("packet probability must be between zero and one")


@dataclass(frozen=True)
class PacketRelation:
    left_packet_id: str
    right_packet_id: str
    relation_state: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.left_packet_id == self.right_packet_id:
            raise ValueError("relation requires two distinct packets")
        if self.relation_state not in RELATION_STATES:
            raise ValueError("unknown relation state")
        if not self.evidence_refs:
            raise ValueError("relation evidence references are required")

    @property
    def pair(self) -> tuple[str, str]:
        return tuple(sorted((self.left_packet_id, self.right_packet_id)))


@dataclass(frozen=True)
class RelationGraphCase:
    case_id: str
    packets: tuple[CognitivePacket, ...]
    relations: tuple[PacketRelation, ...]
    expected_action: str
    expected_probability_y1: float | None
    expected_selected_packet_ids: tuple[str, ...]
    expected_excluded_duplicate_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.expected_action not in PLAN_ACTIONS:
            raise ValueError("unknown expected action")
        if len(self.packets) < 2:
            raise ValueError("at least two packets are required")


@dataclass(frozen=True)
class CompositionPlan:
    case_id: str
    action: str
    selected_packet_ids: tuple[str, ...]
    excluded_duplicate_ids: tuple[str, ...]
    errors: tuple[str, ...]
    graph_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CompositionReceipt:
    case_id: str
    action: str
    probability_y1: float | None
    selected_packet_ids: tuple[str, ...]
    excluded_duplicate_ids: tuple[str, ...]
    graph_hash: str
    formula: str
    provider_calls: int
    receipt_hash: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
