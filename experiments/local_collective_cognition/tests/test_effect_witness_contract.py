from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.effect_witness_contract import (  # noqa: E402
    derive_independent_effect_witnesses,
)


def _delta(*, source="O3", lane="EFFECT"):
    return {
        "source_object_id": source,
        "target_object_id": "O1",
        "proposed_admission_lane": lane,
        "source_opportunity_type": lane,
        "source_opportunity_hash": f"opportunity-{source}-{lane}",
        "source_opportunity_evidence_span_ids": ["S2"],
    }


def test_effect_witness_requires_distinct_valid_same_stage_replication():
    receipts = {
        "R1:A2_COMPACT_DELTA:PROVIDER_COMPACT_DELTA:CASE": _delta(),
        "R2:A2_COMPACT_DELTA:PROVIDER_COMPACT_DELTA:CASE": _delta(),
        "R3:A2_COMPACT_DELTA:PROVIDER_COMPACT_DELTA:CASE": _delta(
            source="O4"
        ),
        "R4:A2_COMPACT_DELTA:PROVIDER_COMPACT_DELTA:CASE": _delta(),
    }
    witnesses = derive_independent_effect_witnesses(
        raw_receipts=receipts,
        lineage_valid_keys=[
            "R1:A2_COMPACT_DELTA:CASE",
            "R2:A2_COMPACT_DELTA:CASE",
            "R3:A2_COMPACT_DELTA:CASE",
        ],
        source_replication_id="R1",
        arm_id="A2_COMPACT_DELTA",
        case_id="CASE",
        source_object_id="O3",
        target_object_id="O1",
    )
    assert [value["witness_replication_id"] for value in witnesses] == [
        "R2"
    ]
    assert witnesses[0]["private_truth_used"] is False
    assert witnesses[0]["selection_authority"] is False
