from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.marginal_scarcity_holdout import (  # noqa: E402
    audit_marginal_scarcity_construction,
    build_marginal_scarcity_holdout,
)


def test_every_fresh_case_has_real_hidden_marginal_scarcity():
    corpus = build_marginal_scarcity_holdout()
    audit = audit_marginal_scarcity_construction(corpus)
    assert corpus["case_count"] == 6
    assert audit["valid_cell_count"] == 6
    assert audit["minimum_designed_gross_cbit_uplift"] == 2.0
    assert audit["provider_calls_added"] == 0
    assert audit["formal_experiment_authorized"] is False
