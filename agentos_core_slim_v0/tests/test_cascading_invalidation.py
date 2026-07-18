import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import CascadingInvalidationGraph, DependencyEdge, KnowledgeNode


def node(node_id, node_type="claim"):
    return KnowledgeNode(
        node_id=node_id,
        node_type=node_type,
        scope="project://fixture",
        evidence_refs=(f"evidence://{node_id}",),
    )


def invalidate(graph, node_id):
    return graph.invalidate(
        node_id,
        reason="source_claim_falsified",
        adjudication_ref="decision://falsified",
        evidence_refs=("evidence://falsifier",),
    )


def test_hard_dependency_invalidates_transitive_downstream_assets():
    graph = CascadingInvalidationGraph()
    for item in (node("evidence", "evidence"), node("claim"), node("report", "report")):
        graph.register_node(item)
    graph.add_dependency(DependencyEdge("evidence", "claim", "SUPPORTS"))
    graph.add_dependency(DependencyEdge("claim", "report", "DERIVED_IN"))

    receipt = invalidate(graph, "evidence")

    assert graph.node("evidence").status == "INVALIDATED"
    assert graph.node("claim").status == "INVALIDATED"
    assert graph.node("report").status == "INVALIDATED"
    assert receipt.cascade_size == 2
    assert set(receipt.reuse_blocked_node_ids) == {"evidence", "claim", "report"}


def test_soft_dependency_quarantines_downstream_pending_revalidation():
    graph = CascadingInvalidationGraph()
    graph.register_node(node("operator", "operator"))
    graph.register_node(node("memory", "memory"))
    graph.add_dependency(
        DependencyEdge("operator", "memory", "USED_TO_DERIVE", propagation_mode="QUARANTINE")
    )

    invalidate(graph, "operator")

    assert graph.node("operator").status == "INVALIDATED"
    assert graph.node("memory").status == "QUARANTINED"
    assert graph.is_reuse_blocked("memory") is True


def test_cycle_propagation_terminates_and_records_each_transition_once():
    graph = CascadingInvalidationGraph()
    graph.register_node(node("claim-a"))
    graph.register_node(node("claim-b"))
    graph.add_dependency(DependencyEdge("claim-a", "claim-b", "DEPENDS_ON"))
    graph.add_dependency(DependencyEdge("claim-b", "claim-a", "DEPENDS_ON"))

    receipt = invalidate(graph, "claim-a")

    assert len(receipt.transitions) == 2
    assert receipt.propagation_steps == 2


def test_quarantined_node_cannot_revalidate_while_upstream_is_inactive():
    graph = CascadingInvalidationGraph()
    graph.register_node(node("source", "evidence"))
    graph.register_node(node("claim"))
    graph.add_dependency(
        DependencyEdge("source", "claim", "SUPPORTS", propagation_mode="QUARANTINE")
    )
    invalidate(graph, "source")

    with pytest.raises(ValueError, match="revalidation_blocked_by_inactive_upstream"):
        graph.revalidate(
            "claim",
            adjudication_ref="decision://revalidate",
            evidence_refs=("evidence://new",),
        )


def test_unrelated_nodes_remain_active():
    graph = CascadingInvalidationGraph()
    graph.register_node(node("root"))
    graph.register_node(node("unrelated"))

    invalidate(graph, "root")

    assert graph.node("unrelated").status == "ACTIVE"
    assert graph.is_reuse_blocked("unrelated") is False
