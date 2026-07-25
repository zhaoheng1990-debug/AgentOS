import json
from pathlib import Path

import pytest

from local_collective_cognition.admission_v2_external_adjudication import (
    build_adjudication,
    build_typed_reference,
    validate_adjudication,
    validate_adjudication_response,
)
from local_collective_cognition.admission_v2_external_panel import (
    build_external_panel,
    validate_annotation_response,
    validate_external_panel,
)


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "outputs" / "admission_v2_v0_76"
OUTPUT = ROOT / "outputs" / "admission_v2_external_panel_v0_77"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def source_inputs():
    return {
        "panel": read(SOURCE / "calibration_private.json"),
        "run": read(SOURCE / "calibration_candidate_run.json"),
        "score": read(SOURCE / "calibration_score.json"),
        "decision": read(SOURCE / "calibration_decision.json"),
    }


def test_external_panel_is_deterministic_blinded_and_complete():
    packs, manifest = build_external_panel(**source_inputs())
    recorded = (
        read(OUTPUT / "gpt_5_6_typed_admission_pack_v0_77.json"),
        read(OUTPUT / "gemini_3_1_typed_admission_pack_v0_77.json"),
    )
    recorded_manifest = read(OUTPUT / "panel_manifest_private.json")

    assert packs == recorded
    assert manifest == recorded_manifest
    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=source_inputs(),
    )
    assert manifest["span_count"] == 50
    assert manifest["case_count"] == 12
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert manifest["benchmark_gold_exposed_to_annotators"] is False
    assert manifest["v0_75_holdout_reused"] is False
    assert not (
        {item["annotation_id"] for item in packs[0]["items"]}
        & {item["annotation_id"] for item in packs[1]["items"]}
    )
    serialized = json.dumps(packs).casefold()
    assert "private_gold" not in serialized
    assert "gold_rationale" not in serialized
    assert "predicted_label" not in serialized
    assert "deepseek" not in serialized


def test_annotation_response_requires_compatible_typed_labels():
    packs, _ = build_external_panel(**source_inputs())
    response = _response(packs[0])
    validate_annotation_response(response, pack=packs[0])

    response["labels"][0]["disposition"] = "RETAIN_CONTEXT"
    with pytest.raises(
        ValueError,
        match="admission_v2_annotation_label_invalid",
    ):
        validate_annotation_response(response, pack=packs[0])


def test_agreement_only_reference_requires_no_kimi_response():
    packs, manifest = build_external_panel(**source_inputs())
    responses = tuple(_response(pack) for pack in packs)
    adjudication_pack, adjudication_manifest = build_adjudication(
        packs=packs,
        panel_manifest=manifest,
        responses=responses,
    )
    validate_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={
            "packs": packs,
            "panel_manifest": manifest,
            "responses": responses,
        },
    )
    assert adjudication_manifest["agreement_count"] == 50
    assert adjudication_manifest["disagreement_count"] == 0
    reference = build_typed_reference(
        panel_manifest=manifest,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    assert reference["label_count"] == 50
    assert {
        value["reference_basis"] for value in reference["labels"]
    } == {"INDEPENDENT_LANE_AGREEMENT"}


def test_disagreement_is_anonymous_and_kimi_reassessment_is_bound():
    packs, manifest = build_external_panel(**source_inputs())
    responses = [_response(pack) for pack in packs]
    responses[1]["labels"][0].update({
        "object_relation": "EXACT_OBJECT",
        "evidence_utility": "EFFECT_BEARING",
        "disposition": "ADMIT_EVIDENCE",
        "effect_basis_codes": ["NULL_OR_NO_DIFFERENCE"],
    })
    adjudication_pack, adjudication_manifest = build_adjudication(
        packs=packs,
        panel_manifest=manifest,
        responses=tuple(responses),
    )
    assert adjudication_manifest["disagreement_count"] == 1
    serialized = json.dumps(adjudication_pack).casefold()
    assert "gpt-5.6" not in serialized
    assert "gemini-3.1" not in serialized
    assert "openai" not in serialized
    assert "google" not in serialized

    response = _kimi_response(adjudication_pack)
    validate_adjudication_response(
        response,
        pack=adjudication_pack,
    )
    reference = build_typed_reference(
        panel_manifest=manifest,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        adjudication_response=response,
    )
    assert reference["label_count"] == 50
    assert sum(
        value["reference_basis"] == "KIMI_K3_ADJUDICATION"
        for value in reference["labels"]
    ) == 1
    assert reference["runtime_tuning_authority"] is False


def _response(pack):
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": f"test-{pack['lane_id']}",
        "blinding_attestation": pack["response_contract"][
            "required_blinding_attestation"
        ],
        "labels": [
            {
                "annotation_id": item["annotation_id"],
                "object_relation": "IRRELEVANT_OBJECT",
                "evidence_utility": "NONE",
                "disposition": "REJECT",
                "effect_basis_codes": ["NOT_EFFECT_BEARING"],
                "confidence": 0.8,
                "rationale": "Synthetic validator fixture.",
            }
            for item in pack["items"]
        ],
    }


def _kimi_response(pack):
    return {
        "panel_version": pack["panel_version"],
        "adjudication_version": pack["adjudication_version"],
        "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": pack["expected_adjudicator"]["provider"],
        "adjudicator_model": pack["expected_adjudicator"]["model"],
        "adjudication_session_ref": "test-kimi-k3",
        "blinding_attestation": pack["response_contract"][
            "required_blinding_attestation"
        ],
        "decisions": [
            {
                "adjudication_id": item["adjudication_id"],
                "object_relation": "EXACT_OBJECT",
                "evidence_utility": "EFFECT_BEARING",
                "disposition": "ADMIT_EVIDENCE",
                "effect_basis_codes": ["NULL_OR_NO_DIFFERENCE"],
                "decision_basis": "INDEPENDENT_REASSESSMENT",
                "confidence": 0.9,
                "rationale": "Synthetic adjudication fixture.",
            }
            for item in pack["items"]
        ],
    }
