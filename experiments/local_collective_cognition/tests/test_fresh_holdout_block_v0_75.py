import json
from pathlib import Path

from local_collective_cognition.fresh_holdout_block import (
    finalize_admission_block,
)
from local_collective_cognition.provider_telemetry import hash_payload


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "fresh_holdout_v0_75"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_fresh_holdout_stops_before_candidate_and_gold_scoring():
    preregistration = read(OUTPUT / "holdout_preregistration.json")
    baseline = read(OUTPUT / "baseline_run.json")
    recorded = read(OUTPUT / "holdout_block_decision.json")
    replayed = finalize_admission_block(
        preregistration=preregistration,
        baseline_run=baseline,
    )

    assert replayed == recorded
    assert recorded["artifact_hash"] == hash_payload({
        key: value
        for key, value in recorded.items()
        if key != "artifact_hash"
    })
    assert recorded["decision"] == "BLOCKED_BY_ADMISSION_CONTRACT"
    assert recorded["valid_admission_receipts"] == 34
    assert recorded["valid_baseline_receipts"] == 32
    assert recorded["failure_count"] == 4
    assert recorded["candidate_execution_started"] is False
    assert recorded["private_gold_scored"] is False
    assert recorded["fresh_generalization_assessable"] is False
    assert recorded["holdout_reexecution_allowed"] is False
    assert not (OUTPUT / "candidate_run.json").exists()


def test_fresh_holdout_failure_roles_are_preserved():
    recorded = read(OUTPUT / "holdout_block_decision.json")
    failures = {
        value["case_id"]: (
            value["role"],
            value["contract_failures"],
        )
        for value in recorded["failure_records"]
    }
    assert failures == {
        "EI-CAL-11049": (
            "A1_STAGED_BINDING",
            ["SPAN_PARTITION_INCOMPLETE"],
        ),
        "EI-CAL-13742": (
            "A1_SPAN_ADMISSION",
            ["ADMISSION_EMPTY"],
        ),
        "EI-CAL-4226": (
            "A1_SPAN_ADMISSION",
            ["ADMISSION_REJECT_RELATION_CONFLICT"],
        ),
        "EI-CAL-6806": (
            "A1_STAGED_BINDING",
            ["SPAN_PARTITION_INCOMPLETE"],
        ),
    }
