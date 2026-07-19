"""Dependency-aware invalidation and quarantine propagation graph."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any


CASCADING_INVALIDATION_VERSION = "cascading_invalidation_graph_v0_1"

NODE_TYPES = {"claim", "evidence", "receipt", "operator", "memory", "report", "problem", "trial"}
NODE_STATUSES = {"ACTIVE", "QUARANTINED", "INVALIDATED"}
PROPAGATION_MODES = {"INVALIDATE", "QUARANTINE"}
STATUS_STRENGTH = {"ACTIVE": 0, "QUARANTINED": 1, "INVALIDATED": 2}


@dataclass(frozen=True)
class KnowledgeNode:
    node_id: str
    node_type: str
    scope: str
    evidence_refs: tuple[str, ...]
    status: str = "ACTIVE"

    def __post_init__(self) -> None:
        if not self.node_id or not self.scope:
            raise ValueError("knowledge_node_identity_required")
        if self.node_type not in NODE_TYPES:
            raise ValueError(f"unknown_knowledge_node_type:{self.node_type}")
        if self.status not in NODE_STATUSES:
            raise ValueError(f"unknown_knowledge_node_status:{self.status}")


@dataclass(frozen=True)
class DependencyEdge:
    upstream_node_id: str
    downstream_node_id: str
    relation: str
    propagation_mode: str = "INVALIDATE"

    def __post_init__(self) -> None:
        if not self.upstream_node_id or not self.downstream_node_id or not self.relation:
            raise ValueError("dependency_edge_identity_required")
        if self.propagation_mode not in PROPAGATION_MODES:
            raise ValueError(f"unknown_propagation_mode:{self.propagation_mode}")


@dataclass(frozen=True)
class InvalidationTransition:
    node_id: str
    previous_status: str
    next_status: str
    caused_by_node_id: str
    relation: str


@dataclass(frozen=True)
class InvalidationReceipt:
    root_node_id: str
    reason: str
    adjudication_ref: str
    evidence_refs: tuple[str, ...]
    transitions: tuple[InvalidationTransition, ...]
    cascade_size: int
    propagation_steps: int
    reuse_blocked_node_ids: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "root_node_id": self.root_node_id,
            "reason": self.reason,
            "adjudication_ref": self.adjudication_ref,
            "evidence_refs": list(self.evidence_refs),
            "transitions": [
                {
                    "node_id": item.node_id,
                    "previous_status": item.previous_status,
                    "next_status": item.next_status,
                    "caused_by_node_id": item.caused_by_node_id,
                    "relation": item.relation,
                }
                for item in self.transitions
            ],
            "cascade_size": self.cascade_size,
            "propagation_steps": self.propagation_steps,
            "reuse_blocked_node_ids": list(self.reuse_blocked_node_ids),
        }


class CascadingInvalidationGraph:
    """P5 knowledge hygiene with deterministic, cycle-safe propagation."""

    module_id = CASCADING_INVALIDATION_VERSION
    capabilities = ("dependency_tracking", "cascade_invalidation", "reuse_blocking")

    def __init__(self) -> None:
        self._nodes: dict[str, KnowledgeNode] = {}
        self._edges: list[DependencyEdge] = []
        self._edge_keys: set[tuple[str, str, str]] = set()

    def register_node(self, node: KnowledgeNode) -> None:
        if node.node_id in self._nodes:
            raise ValueError(f"duplicate_knowledge_node_id:{node.node_id}")
        self._nodes[node.node_id] = node

    def add_dependency(self, edge: DependencyEdge) -> None:
        if edge.upstream_node_id not in self._nodes or edge.downstream_node_id not in self._nodes:
            raise KeyError("dependency_edge_node_not_registered")
        key = (edge.upstream_node_id, edge.downstream_node_id, edge.relation)
        if key in self._edge_keys:
            raise ValueError("duplicate_dependency_edge")
        self._edges.append(edge)
        self._edge_keys.add(key)

    def node(self, node_id: str) -> KnowledgeNode:
        try:
            return self._nodes[node_id]
        except KeyError as exc:
            raise KeyError(f"knowledge_node_not_registered:{node_id}") from exc

    def invalidate(
        self,
        node_id: str,
        *,
        reason: str,
        adjudication_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> InvalidationReceipt:
        if node_id not in self._nodes:
            raise KeyError(f"knowledge_node_not_registered:{node_id}")
        if not reason or not adjudication_ref or not evidence_refs:
            raise ValueError("invalidation_reason_adjudication_and_evidence_required")

        transitions: list[InvalidationTransition] = []
        queue: deque[tuple[str, str, str, str]] = deque(
            [(node_id, "INVALIDATED", node_id, "root_invalidation")]
        )
        propagation_steps = 0
        while queue:
            current_id, requested_status, cause_id, relation = queue.popleft()
            current = self._nodes[current_id]
            if STATUS_STRENGTH[requested_status] <= STATUS_STRENGTH[current.status]:
                continue
            previous_status = current.status
            self._nodes[current_id] = replace(current, status=requested_status)
            transitions.append(
                InvalidationTransition(
                    node_id=current_id,
                    previous_status=previous_status,
                    next_status=requested_status,
                    caused_by_node_id=cause_id,
                    relation=relation,
                )
            )
            propagation_steps += 1
            for edge in self._edges:
                if edge.upstream_node_id != current_id:
                    continue
                downstream_status = (
                    "INVALIDATED"
                    if requested_status == "INVALIDATED" and edge.propagation_mode == "INVALIDATE"
                    else "QUARANTINED"
                )
                queue.append(
                    (
                        edge.downstream_node_id,
                        downstream_status,
                        current_id,
                        edge.relation,
                    )
                )

        blocked = tuple(
            sorted(node.node_id for node in self._nodes.values() if node.status in {"QUARANTINED", "INVALIDATED"})
        )
        return InvalidationReceipt(
            root_node_id=node_id,
            reason=reason,
            adjudication_ref=adjudication_ref,
            evidence_refs=evidence_refs,
            transitions=tuple(transitions),
            cascade_size=max(0, len(transitions) - 1),
            propagation_steps=propagation_steps,
            reuse_blocked_node_ids=blocked,
        )

    def revalidate(
        self,
        node_id: str,
        *,
        adjudication_ref: str,
        evidence_refs: tuple[str, ...],
    ) -> KnowledgeNode:
        node = self.node(node_id)
        if node.status == "INVALIDATED":
            raise ValueError("invalidated_node_requires_versioned_replacement")
        if not adjudication_ref or not evidence_refs:
            raise ValueError("revalidation_adjudication_and_evidence_required")
        upstream_ids = [edge.upstream_node_id for edge in self._edges if edge.downstream_node_id == node_id]
        if any(self._nodes[upstream_id].status != "ACTIVE" for upstream_id in upstream_ids):
            raise ValueError("revalidation_blocked_by_inactive_upstream")
        updated = replace(
            node,
            status="ACTIVE",
            evidence_refs=tuple(dict.fromkeys((*node.evidence_refs, *evidence_refs, adjudication_ref))),
        )
        self._nodes[node_id] = updated
        return updated

    def is_reuse_blocked(self, node_id: str) -> bool:
        return self.node(node_id).status in {"QUARANTINED", "INVALIDATED"}
