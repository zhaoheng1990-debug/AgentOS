import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v10_development_v0_85"


def test_v085_development_result_is_bounded_and_not_acceptable():
    evaluation = json.loads(
        (OUTPUT / "development_evaluation.json").read_text(
            encoding="utf-8"
        )
    )

    assert evaluation["operational_decision"] == (
        "DEVELOPMENT_SCREEN_COMPLETE"
    )
    assert evaluation["relation_mutation_count"] == 2
    assert evaluation["relation_mutation_counts"] == {
        "ADMIT_EVIDENCE_TO_RETAIN_CONTEXT": 1,
        "REJECT_TO_RETAIN_CONTEXT": 1,
    }
    assert evaluation["unauthorized_mutation_count"] == 0
    assert sum(
        evaluation["semantic_conflict_code_counts"].values()
    ) == 38
    assert evaluation["external_acceptance_eligible"] is False
    assert evaluation["candidate_acceptance_authorized"] is False
