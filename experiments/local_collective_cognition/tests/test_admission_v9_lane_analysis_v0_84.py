import json
from pathlib import Path


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v9_external_panel_v0_84"


def test_v084_lane_agreement_decisively_rejects_a18_mutations():
    analysis = json.loads(
        (OUTPUT / "lane_agreement_analysis.json").read_text(
            encoding="utf-8"
        )
    )

    assert analysis["agreement_count"] == 38
    assert analysis["disagreement_count"] == 10
    assert analysis["mutation_outcome_counts"] == {"HARMED": 4}
    assert analysis["all_mutations_resolved_by_lane_agreement"] is True
    assert analysis["mutation_semantic_decision"] == (
        "REJECT_A18_ALL_MUTATIONS_EXTERNALLY_HARMFUL"
    )
    assert analysis["candidate_acceptance_authorized"] is False
