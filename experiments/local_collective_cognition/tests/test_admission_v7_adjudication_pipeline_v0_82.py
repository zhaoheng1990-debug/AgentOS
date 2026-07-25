import json
from pathlib import Path

from local_collective_cognition.admission_v7_external_adjudication import (
    build_adjudication,
    build_typed_reference,
    validate_adjudication,
    validate_adjudication_response,
)
from local_collective_cognition.admission_v7_typed_scoring import (
    score_staged_context_reference,
)


ROOT = Path(__file__).parents[3]
EXTERNAL = ROOT / "outputs" / "admission_v7_external_panel_v0_82"
SOURCE = ROOT / "outputs" / "admission_v7_fresh_holdout_v0_82"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v082_synthetic_lane_disagreement_closes_reference_pipeline():
    packs = (
        read(
            EXTERNAL
            / "gpt_5_6_staged_context_admission_pack_v0_82.json"
        ),
        read(
            EXTERNAL
            / "gemini_3_1_staged_context_admission_pack_v0_82.json"
        ),
    )
    responses = [
        _lane_response(pack, context_first=index == 1)
        for index, pack in enumerate(packs)
    ]
    manifest = read(EXTERNAL / "panel_manifest_private.json")
    pack, adjudication_manifest = build_adjudication(
        packs=packs,
        panel_manifest=manifest,
        responses=responses,
    )

    validate_adjudication(pack=pack, manifest=adjudication_manifest)
    assert adjudication_manifest["agreement_count"] == 47
    assert adjudication_manifest["disagreement_count"] == 1
    assert pack["annotator_identity"] == "WITHHELD"
    assert pack["atomic_system_outputs"] == "WITHHELD"

    kimi_response = _kimi_response(pack)
    validate_adjudication_response(kimi_response, pack=pack)
    reference = build_typed_reference(
        panel_manifest=manifest,
        adjudication_pack=pack,
        adjudication_manifest=adjudication_manifest,
        adjudication_response=kimi_response,
    )
    assert reference["label_count"] == 48
    assert reference["reference_status"] == (
        "EXTERNAL_TYPED_REFERENCE_CANDIDATE"
    )

    score = score_staged_context_reference(
        reference=reference,
        baseline_run=read(SOURCE / "baseline_run.json"),
        atomic_run=read(SOURCE / "atomic_run.json"),
        candidate_run=read(SOURCE / "candidate_run.json"),
    )
    assert score["preregistered_semantic_conditions"][
        "evidence_f1_preserved"
    ] is True
    assert score["candidate_acceptance_authorized"] is False


def _lane_response(pack, *, context_first):
    labels = []
    for index, item in enumerate(pack["items"]):
        if context_first and index == 0:
            label = {
                "object_relation": "CONTEXTUAL_OBJECT",
                "evidence_utility": "CONTEXT_ONLY",
                "disposition": "RETAIN_CONTEXT",
                "effect_basis_codes": ["NOT_EFFECT_BEARING"],
            }
        else:
            label = {
                "object_relation": "IRRELEVANT_OBJECT",
                "evidence_utility": "NONE",
                "disposition": "REJECT",
                "effect_basis_codes": ["NOT_EFFECT_BEARING"],
            }
        labels.append({
            "annotation_id": item["annotation_id"],
            **label,
            "confidence": 0.8,
            "rationale": "synthetic protocol validation label",
        })
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "synthetic-test-session",
        "blinding_attestation": pack["response_contract"][
            "required_blinding_attestation"
        ],
        "labels": labels,
    }


def _kimi_response(pack):
    decisions = []
    for item in pack["items"]:
        position = item["anonymous_positions"][0]
        decisions.append({
            "adjudication_id": item["adjudication_id"],
            "object_relation": position["object_relation"],
            "evidence_utility": position["evidence_utility"],
            "disposition": position["disposition"],
            "effect_basis_codes": position["effect_basis_codes"],
            "decision_basis": position["position_id"],
            "confidence": 0.8,
            "rationale": "synthetic adjudication validation",
        })
    return {
        "panel_version": pack["panel_version"],
        "adjudication_version": pack["adjudication_version"],
        "panel_id": pack["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudicator_provider": pack["expected_adjudicator"]["provider"],
        "adjudicator_model": pack["expected_adjudicator"]["model"],
        "adjudication_session_ref": "synthetic-kimi-session",
        "blinding_attestation": pack["response_contract"][
            "required_blinding_attestation"
        ],
        "decisions": decisions,
    }
