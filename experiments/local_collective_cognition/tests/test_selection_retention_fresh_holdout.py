from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.selection_retention_fresh_holdout import (  # noqa: E402
    CASES,
    audit_selection_retention_fresh_holdout,
    build_selection_retention_fresh_holdout,
    validate_selection_retention_fresh_holdout,
)


def test_v064_is_fresh_complete_and_provider_blind():
    corpus = build_selection_retention_fresh_holdout()
    validate_selection_retention_fresh_holdout(corpus)
    assert corpus["case_count"] == 8
    assert corpus["relation_count"] == 40
    assert len({value["domain"] for value in CASES}) == 8
    assert corpus["private_provenance"]["available_to_provider"] is False
    assert corpus["prior_holdout_cases_reused"] is False
    assert corpus["prior_holdout_labels_reused"] is False
    assert corpus["selection_authority"] is False
    assert corpus["retention_authority"] is False


def test_v064_balances_states_auxiliary_types_and_validity():
    audit = audit_selection_retention_fresh_holdout(
        build_selection_retention_fresh_holdout()
    )
    assert audit["formal_execution_authorized"] is True
    assert audit["valid_cell_count"] == 8
    assert audit["relation_count"] == 40
    assert audit["state_counts"] == {
        "SUPPORTED_EFFECT": 16,
        "SUPPORTED_NULL": 10,
        "UNRESOLVED": 14,
    }
    assert audit["auxiliary_counts"] == {
        "corroborating_evidence_span_ids": 16,
        "counterevidence_span_ids": 4,
        "gap_evidence_span_ids": 4,
    }
    assert audit["validity_counts"] == {
        "CURRENT": 6,
        "DRIFTED": 1,
        "STALE": 1,
    }
    assert audit["prior_v0_61_domain_overlap"] == []
    assert audit["provider_calls_added"] == 0


def test_every_case_has_real_partition_and_one_expected_state():
    corpus = build_selection_retention_fresh_holdout()
    retention_states = Counter()
    for item in corpus["public_surface"]["items"]:
        refs = {
            value["alternative_ref"]
            for value in item["selection_alternatives"]
        }
        private = corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        partition = {
            private["expected_selected_ref"],
            *private["expected_rejected_refs"],
            *private["expected_deferred_refs"],
        }
        assert len(refs) == 3
        assert refs == partition
        assert len(private["typed_relation_reference"]) == 5
        retention_states[
            private["expected_retention_candidate_state"]
        ] += 1
    assert retention_states == {
        "PENDING_RETENTION_REVIEW": 5,
        "QUARANTINED_SELECTION_EVIDENCE": 2,
        "PENDING_SELECTION_EVIDENCE": 1,
    }
