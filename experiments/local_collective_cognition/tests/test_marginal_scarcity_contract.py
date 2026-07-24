from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.marginal_scarcity_contract import (  # noqa: E402
    build_discovery_view,
    discovery_schema,
)
from local_collective_cognition.marginal_scarcity_holdout import (  # noqa: E402
    build_marginal_scarcity_holdout,
)


def test_discovery_surface_hides_private_target_and_authority():
    corpus = build_marginal_scarcity_holdout()
    item = corpus["public_surface"]["items"][0]
    view = build_discovery_view(
        item=item, corpus_hash=corpus["artifact_hash"]
    )
    schema = discovery_schema(
        view=view, role="OMITTED_RELATION_PROPOSER",
        refs=corpus["evidence_refs"],
    )
    encoded = str(view) + str(schema)
    assert "designed_target_relation" not in encoded
    assert "designed_gross_cbit_uplift" not in encoded
    assert view["private_truth_available"] is False
    assert view["replacement_authority"] is False
