from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    audit_portfolio_critic_fresh_holdout,
    audit_portfolio_critic_fresh_holdout_v0_61_1,
    build_portfolio_critic_fresh_holdout,
    build_portfolio_critic_fresh_holdout_v0_61_1,
)


def test_fresh_holdout_balances_three_topologies():
    corpus = build_portfolio_critic_fresh_holdout()
    audit = audit_portfolio_critic_fresh_holdout(corpus)
    assert audit["valid_cell_count"] == 6
    assert audit["topology_counts"] == {
        "MULTIPLE_UNRESOLVED": 2,
        "NO_UNRESOLVED": 2,
        "UNIQUE_UNRESOLVED": 2,
    }
    assert audit["topology_balance_valid"] is True
    assert audit["target_position_coverage"] == 5


def test_fresh_public_surface_hides_topology_and_expected_action():
    corpus = build_portfolio_critic_fresh_holdout()
    encoded = str(corpus["public_surface"]["items"])
    assert "topology" not in encoded
    assert "expected_kernel_action" not in encoded
    assert "eligible_pool_ids" not in encoded
    assert corpus["private_provenance"]["available_to_provider"] is False


def test_v0_61_1_repairs_only_two_focal_outcome_bindings():
    original = build_portfolio_critic_fresh_holdout()
    repaired = build_portfolio_critic_fresh_holdout_v0_61_1()
    before_items = {
        value["case_id"]: value for value in original["public_surface"]["items"]
    }
    after_items = {
        value["case_id"]: value for value in repaired["public_surface"]["items"]
    }
    changed = []
    for case_id, before_item in before_items.items():
        before_spans = {
            value["span_id"]: value["text"]
            for value in before_item["evidence_spans"]
        }
        after_spans = {
            value["span_id"]: value["text"]
            for value in after_items[case_id]["evidence_spans"]
        }
        changed.extend(
            (case_id, span_id)
            for span_id in before_spans
            if before_spans[span_id] != after_spans[span_id]
        )
        assert (
            before_item["frozen_active_portfolio"]
            == after_items[case_id]["frozen_active_portfolio"]
        )
    assert sorted(changed) == [
        ("PC-GENOME", "S3"),
        ("PC-TRAFFIC", "S2"),
    ]
    for case_id, binding in original["private_provenance"]["bindings"].items():
        repaired_binding = repaired["private_provenance"]["bindings"][case_id]
        assert binding["topology"] == repaired_binding["topology"]
        assert (
            binding["designed_target_relation"]
            == repaired_binding["designed_target_relation"]
        )
        assert (
            binding["expected_kernel_action"]
            == repaired_binding["expected_kernel_action"]
        )
    audit = audit_portfolio_critic_fresh_holdout_v0_61_1(repaired)
    assert audit["valid_cell_count"] == 6
