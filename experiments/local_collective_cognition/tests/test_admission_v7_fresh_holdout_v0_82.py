from local_collective_cognition.admission_v7_fresh_holdout import (
    SELECTED_PROMPT_IDS,
    build_fresh_holdout,
    build_preregistration,
    prior_surface_ids,
    validate_fresh_holdout,
    validate_preregistration,
)
from local_collective_cognition.benchmark_bridge_sources import (
    ensure_holdout_source,
    ensure_sources,
    holdout_source_manifest,
)


def test_v082_selected_objects_are_disjoint_from_prior_surfaces():
    assert not set(SELECTED_PROMPT_IDS) & prior_surface_ids()


def test_v082_preregisters_staged_invariance_before_provider_calls():
    paths = ensure_sources()
    paths["test_article_ids.txt"] = ensure_holdout_source()
    panel = build_fresh_holdout(
        paths,
        source_manifest=holdout_source_manifest(),
    )
    preregistration = build_preregistration(panel)

    validate_fresh_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    assert panel["label_balance"] == {
        "INCREASED": 4,
        "DECREASED": 4,
        "NO_DIFFERENCE": 4,
    }
    gate = preregistration["operational_gate"]
    assert gate["atomic_evidence_partition_invariance_required"] is True
    assert gate["effect_rejudgment_allowed"] is False
    assert preregistration["holdout_reexecution_allowed"] is False
