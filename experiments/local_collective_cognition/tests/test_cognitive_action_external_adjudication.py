from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.cognitive_action_external_panel import (  # noqa: E402
    adjudication_response_contract,
    build_external_adjudication,
    validate_adjudication_response,
    validate_external_adjudication,
)


PANEL = ROOT / "outputs" / "cognitive_action_overnight_v0_16" / "external_panel"
SOURCE = PANEL.parent


def inputs():
    packs = (
        json.loads((PANEL / "gpt_5_6_cognitive_action_fresh_pack.json").read_text(encoding="utf-8")),
        json.loads((PANEL / "gemini_3_1_cognitive_action_fresh_pack.json").read_text(encoding="utf-8")),
    )
    manifest = json.loads((PANEL / "private_external_panel_manifest.json").read_text(encoding="utf-8"))
    responses = (
        json.loads((PANEL / "gpt_5_6_cognitive_action_fresh_response.json").read_text(encoding="utf-8")),
        json.loads((PANEL / "gemini_3_1_cognitive_action_fresh_response.json").read_text(encoding="utf-8")),
    )
    corpus = json.loads((SOURCE / "fresh_action_corpus_frozen.json").read_text(encoding="utf-8"))
    return {"packs": packs, "panel_manifest": manifest, "responses": responses, "corpus": corpus}


def test_adjudication_pack_is_whole_object_anonymous_and_candidate_blind():
    values = inputs()
    pack, manifest = build_external_adjudication(**values)
    validate_external_adjudication(pack=pack, manifest=manifest, source_inputs=values)
    assert manifest["agreement_object_count"] == 11
    assert manifest["disagreement_object_count"] == 13
    assert all(len(item["anonymous_full_tuple_positions"]) == 2 for item in pack["items"])
    assert "gpt-5.6" not in str(pack).casefold() and "gemini-3.1" not in str(pack).casefold()


def test_adjudication_response_requires_exact_whole_position_when_selected():
    pack = build_external_adjudication(**inputs())[0]
    contract = adjudication_response_contract()
    response = {
        "panel_version": pack["panel_version"], "adjudication_version": pack["adjudication_version"],
        "panel_id": pack["panel_id"], "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": pack["expected_adjudicator"]["provider"],
        "adjudicator_model": pack["expected_adjudicator"]["model"], "adjudication_session_ref": "test-k3",
        "blinding_attestation": contract["required_blinding_attestation"],
        "decisions": [{
            "adjudication_id": item["adjudication_id"],
            "criteria": item["anonymous_full_tuple_positions"][0]["criteria"],
            "decision_basis": "POSITION_1", "confidence": 0.7, "rationale": "Selected the stronger coherent full tuple.",
        } for item in pack["items"]],
    }
    validate_adjudication_response(response, pack=pack)
    broken = deepcopy(response)
    broken["decisions"][0]["criteria"] = pack["items"][0]["anonymous_full_tuple_positions"][1]["criteria"]
    with pytest.raises(ValueError, match="position_binding"):
        validate_adjudication_response(broken, pack=pack)
