from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    audit_marginal_scarcity_transfer,
    audit_marginal_scarcity_transfer_v0_59_1,
    build_marginal_scarcity_transfer_holdout,
    build_marginal_scarcity_transfer_holdout_v0_59_1,
)


def test_transfer_holdout_rotates_target_and_balances_drop_pool():
    corpus = build_marginal_scarcity_transfer_holdout()
    audit = audit_marginal_scarcity_transfer(corpus)
    assert corpus["case_count"] == 6
    assert audit["valid_cell_count"] == 6
    assert audit["target_position_coverage"] == 5
    assert set(audit["target_position_counts"]) == {
        "O2", "O3", "O4", "O5", "O6"
    }
    assert audit["drop_pool_counts"] == {
        "BASE:C1": 2,
        "BASE:C2": 2,
        "BASE:C3": 2,
    }
    assert audit["drop_pool_balance_valid"] is True


def test_transfer_public_surface_hides_target_and_drop_bindings():
    corpus = build_marginal_scarcity_transfer_holdout()
    public = corpus["public_surface"]
    encoded = str(public["items"])
    assert "designed_target_relation" not in encoded
    assert "designed_drop_pool_id" not in encoded
    assert public["private_outcomes_exposed"] is False
    assert corpus["private_provenance"]["available_to_provider"] is False


def test_repair_changes_only_two_evidence_spans_not_hidden_design():
    original = build_marginal_scarcity_transfer_holdout()
    repaired = build_marginal_scarcity_transfer_holdout_v0_59_1()
    original_items = {
        value["case_id"]: value for value in original["public_surface"]["items"]
    }
    repaired_items = {
        value["case_id"]: value for value in repaired["public_surface"]["items"]
    }
    changed = []
    for case_id in original_items:
        before = {
            value["span_id"]: value["text"]
            for value in original_items[case_id]["evidence_spans"]
        }
        after = {
            value["span_id"]: value["text"]
            for value in repaired_items[case_id]["evidence_spans"]
        }
        changed.extend(
            (case_id, span_id)
            for span_id in before
            if before[span_id] != after[span_id]
        )
        assert (
            original_items[case_id]["frozen_active_portfolio"]
            == repaired_items[case_id]["frozen_active_portfolio"]
        )
    assert sorted(changed) == [("MT-CROP", "S3"), ("MT-ORBIT", "S4")]
    for case_id, binding in original["private_provenance"]["bindings"].items():
        repaired_binding = repaired["private_provenance"]["bindings"][case_id]
        assert (
            binding["designed_target_relation"]
            == repaired_binding["designed_target_relation"]
        )
        assert (
            binding["designed_drop_pool_id"]
            == repaired_binding["designed_drop_pool_id"]
        )
    audit = audit_marginal_scarcity_transfer_v0_59_1(repaired)
    assert audit["valid_cell_count"] == 6
