"""Deterministic relation-graph to composition-plan compiler."""

from __future__ import annotations

from itertools import combinations

from .contracts import CompositionPlan, RelationGraphCase, hash_payload


BLOCKING_RELATIONS = {
    "DEPENDENT_DISTINCT",
    "PARTIAL_OVERLAP",
    "SCOPE_INCOMPATIBLE",
    "UNRESOLVED",
}


class _UnionFind:
    def __init__(self, values: tuple[str, ...]) -> None:
        self.parent = {value: value for value in values}

    def find(self, value: str) -> str:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: str, right: str) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        keep, drop = sorted((left_root, right_root))
        self.parent[drop] = keep


def _graph_hash(case: RelationGraphCase) -> str:
    return hash_payload(
        {
            "case_id": case.case_id,
            "packets": [
                {
                    "packet_id": packet.packet_id,
                    "prior_y1": packet.prior_y1,
                    "probability_y1": packet.probability_y1,
                    "evidence_ref": packet.evidence_ref,
                }
                for packet in sorted(case.packets, key=lambda item: item.packet_id)
            ],
            "relations": [
                {
                    "pair": relation.pair,
                    "relation_state": relation.relation_state,
                    "evidence_refs": sorted(relation.evidence_refs),
                }
                for relation in sorted(case.relations, key=lambda item: item.pair)
            ],
        }
    )


def _blocked(
    case: RelationGraphCase, graph_hash: str, errors: list[str]
) -> CompositionPlan:
    return CompositionPlan(
        case_id=case.case_id,
        action="BLOCK",
        selected_packet_ids=(),
        excluded_duplicate_ids=(),
        errors=tuple(sorted(set(errors))),
        graph_hash=graph_hash,
    )


def compile_plan(case: RelationGraphCase) -> CompositionPlan:
    graph_hash = _graph_hash(case)
    packet_map = {packet.packet_id: packet for packet in case.packets}
    packet_ids = tuple(sorted(packet_map))
    errors: list[str] = []
    if len(packet_map) != len(case.packets):
        errors.append("PACKET_ID_DUPLICATE")
    priors = [packet.prior_y1 for packet in case.packets]
    if max(priors) - min(priors) > 1e-12:
        errors.append("COMMON_PRIOR_MISMATCH")

    expected_pairs = set(combinations(packet_ids, 2))
    relation_map = {}
    for relation in case.relations:
        if not set(relation.pair).issubset(packet_map):
            errors.append("RELATION_PACKET_UNKNOWN")
            continue
        if relation.pair in relation_map:
            errors.append("RELATION_PAIR_DUPLICATE")
        relation_map[relation.pair] = relation
    if set(relation_map) != expected_pairs:
        errors.append("RELATION_GRAPH_INCOMPLETE")
    if errors:
        return _blocked(case, graph_hash, errors)

    for pair, relation in relation_map.items():
        if relation.relation_state in BLOCKING_RELATIONS:
            errors.append(
                f"RELATION_BLOCKED:{relation.relation_state}:{pair[0]}:{pair[1]}"
            )
    if errors:
        return _blocked(case, graph_hash, errors)

    groups = _UnionFind(packet_ids)
    for relation in relation_map.values():
        if relation.relation_state == "EXACT_DUPLICATE":
            groups.union(*relation.pair)

    components: dict[str, list[str]] = {}
    for packet_id in packet_ids:
        components.setdefault(groups.find(packet_id), []).append(packet_id)
    for members in components.values():
        probabilities = [packet_map[member].probability_y1 for member in members]
        if max(probabilities) - min(probabilities) > 1e-12:
            errors.append(f"DUPLICATE_PROBABILITY_CONFLICT:{','.join(members)}")

    for left, right in expected_pairs:
        relation = relation_map[(left, right)]
        same_component = groups.find(left) == groups.find(right)
        expected_state = (
            "EXACT_DUPLICATE" if same_component else "INDEPENDENT_DISTINCT"
        )
        if relation.relation_state != expected_state:
            errors.append(
                f"RELATION_COMPONENT_CONTRADICTION:{left}:{right}"
            )
    if errors:
        return _blocked(case, graph_hash, errors)

    selected = tuple(sorted(min(members) for members in components.values()))
    excluded = tuple(sorted(set(packet_ids) - set(selected)))
    return CompositionPlan(
        case_id=case.case_id,
        action="DEDUPE_AND_COMBINE" if excluded else "COMBINE",
        selected_packet_ids=selected,
        excluded_duplicate_ids=excluded,
        errors=(),
        graph_hash=graph_hash,
    )
