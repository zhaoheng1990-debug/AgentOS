from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_external_panel import (  # noqa: E402
    annotation_response_contract,
    build_external_panel,
    validate_annotation_response,
    validate_external_panel,
)


OUTPUT = ROOT / "outputs" / "cognitive_action_overnight_v0_16"


def artifacts():
    return (
        json.loads((OUTPUT / "fresh_action_corpus_frozen.json").read_text(encoding="utf-8")),
        json.loads((OUTPUT / "fresh_action_role_run.json").read_text(encoding="utf-8")),
        json.loads((OUTPUT / "blind_coordinator_arms_run.json").read_text(encoding="utf-8")),
    )


def test_external_panel_has_two_disjoint_candidate_blind_lanes():
    corpus, role_run, coordinator_run = artifacts()
    packs, manifest = build_external_panel(corpus=corpus, role_run=role_run, coordinator_run=coordinator_run)
    validate_external_panel(packs=packs, manifest=manifest, corpus=corpus, role_run=role_run, coordinator_run=coordinator_run)
    assert len(packs) == 2
    assert all(len(pack["items"]) == 24 for pack in packs)
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint({item["annotation_id"] for item in packs[1]["items"]})
    assert all("deepseek-r1" not in str(pack).casefold() for pack in packs)
    assert manifest["candidate_outputs_frozen_before_panel_pack"] is True
    assert manifest["candidate_outputs_exposed_to_annotators"] is False


def test_response_contract_accepts_complete_coherent_lane_response():
    corpus, role_run, coordinator_run = artifacts()
    pack = build_external_panel(corpus=corpus, role_run=role_run, coordinator_run=coordinator_run)[0][0]
    contract = annotation_response_contract()
    response = {
        "panel_version": pack["panel_version"], "panel_id": pack["panel_id"], "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"], "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"], "annotation_session_ref": "test-session",
        "blinding_attestation": contract["required_blinding_attestation"],
        "labels": [{
            "annotation_id": item["annotation_id"],
            "criteria": {"SELECTED_OBJECT": "CANDIDATE_A", "SELECTION_BASIS": "COMPOSITIONAL_ENTAILMENT", "PRAGMATIC_PREFERENCE": "CANDIDATE_A", "AXIS_ASSESSMENT_COMPLETE": "COMPLETE"},
            "criterion_notes": {criterion: "Independent assessment note." for criterion in contract["criteria"]},
            "criterion_confidence": {criterion: 0.7 for criterion in contract["criteria"]},
            "tuple_rationale": "The complete tuple is globally coherent.",
        } for item in pack["items"]],
    }
    validate_annotation_response(response, pack=pack)
    broken = deepcopy(response)
    broken["labels"][0]["criteria"]["SELECTED_OBJECT"] = "NONE"
    with pytest.raises(ValueError, match="tuple_incoherent"):
        validate_annotation_response(broken, pack=pack)

