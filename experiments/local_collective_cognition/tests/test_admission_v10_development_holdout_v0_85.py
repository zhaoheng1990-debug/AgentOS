from local_collective_cognition.admission_v10_development_holdout import (
    SELECTED_PROMPT_IDS,
    build_development_holdout,
    build_preregistration,
    prior_surface_ids,
    validate_development_holdout,
    validate_preregistration,
)
from local_collective_cognition.benchmark_bridge_sources import (
    ensure_sources,
    source_manifest,
)


def test_v085_development_objects_are_disjoint_from_prior_surfaces():
    assert not set(SELECTED_PROMPT_IDS) & prior_surface_ids()


def test_v085_screen_explicitly_forbids_external_acceptance():
    panel = build_development_holdout(
        ensure_sources(),
        source_manifest=source_manifest(),
    )
    preregistration = build_preregistration(panel)

    validate_development_holdout(panel)
    validate_preregistration(preregistration, panel=panel)
    gate = preregistration["operational_gate"]
    assert panel["source_split_role"] == "DEVELOPMENT_SCREEN_ONLY"
    assert panel["external_acceptance_eligible"] is False
    assert preregistration["external_acceptance_allowed"] is False
    assert gate["evidence_to_reject_allowed"] is False
    assert gate["context_to_reject_allowed"] is False
    assert gate["reject_to_evidence_allowed"] is False
    assert gate["provider_disposition_authority"] is False
