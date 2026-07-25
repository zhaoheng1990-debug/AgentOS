import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v8_fresh_holdout_v0_83"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v083_boundary_review_is_frozen_as_over_demotion():
    evaluation = read(OUTPUT / "pre_reference_evaluation.json")

    assert evaluation["operational_decision"] == (
        "READY_EXTERNAL_TYPED_PANEL"
    )
    assert evaluation["boundary_mutation_count"] == 15
    assert evaluation["boundary_mutation_counts"] == {
        "ADMIT_EVIDENCE_TO_RETAIN_CONTEXT": 15,
    }
    assert evaluation["candidate"]["evidence_f1"] < 0.37
    assert evaluation["staged"]["evidence_f1"] > 0.97
    assert evaluation["operational_conditions"][
        "reject_partition_invariance"
    ] is True
    assert evaluation["candidate_acceptance_authorized"] is False
