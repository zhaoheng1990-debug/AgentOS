from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_factorial_holdout import (  # noqa: E402
    build_factorial_holdout,
)
from local_collective_cognition.cognitive_action_source_ontology import (  # noqa: E402
    AXIS_SOURCE,
    BASELINE_SOURCE,
    SOURCE_EVALUATION_HASH,
    SOURCE_ONTOLOGY_TASK_KIND,
    SOURCE_REFERENCE_HASH,
    analyze_source_ontology_run,
    build_source_ontology_preregistration,
    collapse_axis_to_legacy,
    normalize_axis_native,
    run_source_ontology_ablation,
)
from local_collective_cognition.cognitive_action_source_ontology_holdout import (  # noqa: E402
    build_source_ontology_holdout,
    validate_source_ontology_holdout,
)
from local_collective_cognition.cognitive_action_source_ontology_panel import (  # noqa: E402
    build_source_ontology_external_adjudication,
    build_source_ontology_external_panel,
    validate_source_ontology_adjudication_response,
    validate_source_ontology_annotation_response,
    validate_source_ontology_external_adjudication,
    validate_source_ontology_external_panel,
)


class OntologyFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-source-ontology",
            model_id="fixture-model",
            task_kinds=(SOURCE_ONTOLOGY_TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.objectives = {}

    def invoke(self, task):
        conflict_id = task.inputs["public_object"]["conflict_id"]
        policy = task.inputs["source_policy"]
        self.objectives[policy] = task.objective
        refs = list(task.allowed_evidence)
        if policy == BASELINE_SOURCE:
            result = {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "definition_source": "UNDERSPECIFIED_SURFACE",
                "pragmatic_preference": "UNCERTAIN",
                "assessment_process_state": "INCOMPLETE",
                "support_quote": "No operational definition is supplied.",
                "rationale": "The displayed surface leaves both options open.",
                "confidence": 0.8,
                "evidence_refs": refs,
            }
        else:
            result = axis_receipt(conflict_id, refs)
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 20,
                "output_tokens": 5,
                "latency_ms": 1,
            },
            "provenance_refs": refs,
        }


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": (
            "EVIDENCE_FACTORIAL_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }


def axis_receipt(conflict_id="x", refs=None, **changes):
    value = {
        "conflict_id": conflict_id,
        "lexical_definition": "NONE",
        "compositional_derivation": "NONE",
        "external_spec_dependency": "NOT_REQUIRED",
        "pragmatic_preference": "UNCERTAIN",
        "assessment_process_state": "INCOMPLETE",
        "support_quotes": {
            "lexical": "NONE",
            "compositional": "NONE",
            "external": "No named external specification is required.",
        },
        "rationale": "The surface leaves both options open.",
        "confidence": 0.8,
        "evidence_refs": refs or ["corpus://x"],
    }
    value.update(changes)
    return value


def normalize(receipt):
    return normalize_axis_native(
        receipt,
        conflict_id=receipt["conflict_id"],
        evidence_refs=tuple(receipt["evidence_refs"]),
    )


def test_source_ontology_holdout_is_fresh_balanced_and_unlabeled():
    corpus = build_source_ontology_holdout()
    validate_source_ontology_holdout(corpus)
    previous = build_factorial_holdout()
    assert corpus["case_count"] == 24
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {6}
    assert {
        item["public_prompt"] for item in corpus["public_surface"]["items"]
    }.isdisjoint({
        item["public_prompt"] for item in previous["public_surface"]["items"]
    })
    assert corpus["v0_20_reference_available_during_inference"] is False


def test_native_gate_distinguishes_direct_composed_open_and_opaque():
    direct = normalize(axis_receipt(
        lexical_definition="CANDIDATE_A",
        pragmatic_preference="NONE",
    ))
    composed = normalize(axis_receipt(
        compositional_derivation="CANDIDATE_B",
        pragmatic_preference="NONE",
    ))
    open_state = normalize(axis_receipt())
    opaque = normalize(axis_receipt(
        external_spec_dependency="REQUIRED_MISSING",
        pragmatic_preference="CANDIDATE_A",
    ))
    assert direct["payload"]["evidence_state"] == "DIRECTLY_DEFINED"
    assert direct["payload"]["selected_object"] == "CANDIDATE_A"
    assert composed["payload"]["evidence_state"] == (
        "COMPOSITIONALLY_DETERMINED"
    )
    assert composed["payload"]["selected_object"] == "CANDIDATE_B"
    assert open_state["payload"]["evidence_state"] == "SOFT_AMBIGUITY"
    assert open_state["payload"]["assessment_process_state"] == "COMPLETE"
    assert opaque["payload"]["evidence_state"] == "OPAQUE_REFERENCE"
    assert opaque["payload"]["pragmatic_preference"] == "NONE"
    assert "OPAQUE_PREFERENCE_TO_NONE" in opaque["gate_transforms"]


def test_native_gate_fails_closed_on_cross_axis_conflict():
    result = normalize(axis_receipt(
        lexical_definition="CANDIDATE_A",
        compositional_derivation="CANDIDATE_B",
        pragmatic_preference="NONE",
        assessment_process_state="COMPLETE",
    ))
    assert result["payload"]["evidence_state"] == "CONFLICTED"
    assert result["payload"]["selected_object"] == "UNCERTAIN"
    assert result["gate_transforms"] == [
        "LEXICAL_COMPOSITIONAL_CONFLICT"
    ]


def test_axis_collapse_preserves_composition_as_legacy_source():
    receipt = axis_receipt(
        compositional_derivation="CANDIDATE_B",
        pragmatic_preference="NONE",
        assessment_process_state="COMPLETE",
    )
    collapsed = collapse_axis_to_legacy(
        receipt,
        conflict_id="x",
        evidence_refs=("corpus://x",),
    )
    assert collapsed["definition_source"] == "COMPOSED_CONSTRAINTS"
    assert collapsed["selected_object"] == "CANDIDATE_B"


def test_ablation_reuses_axis_receipt_and_freezes_three_cells():
    corpus = build_source_ontology_holdout()
    preregistration = build_source_ontology_preregistration(
        source_evaluation=source_evaluation()
    )
    adapter = OntologyFixtureProvider()
    run = run_source_ontology_ablation(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_source_ontology_run(corpus=corpus, run=run)
    assert len(run["source_calls"]) == 48
    assert len(run["outputs"]) == 72
    assert analysis["cell_coverage"] == {
        "BASELINE_LEGACY_SOURCE_REPAIRED_GATE": 1.0,
        "AXIS_SOURCE_COLLAPSED_REPAIRED_GATE": 1.0,
        "AXIS_SOURCE_NATIVE_GATE": 1.0,
    }
    assert run["axis_receipt_reused_across_runtime_paths"] is True
    assert "independent axes" in adapter.objectives[AXIS_SOURCE]
    assert "independent axes" not in adapter.objectives[BASELINE_SOURCE]


def test_external_panel_is_blinded_and_recomputable():
    corpus = build_source_ontology_holdout()
    preregistration = build_source_ontology_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_source_ontology_ablation(
        corpus=corpus,
        preregistration=preregistration,
        adapter=OntologyFixtureProvider(),
    )
    packs, manifest = build_source_ontology_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_source_ontology_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )


def annotation_response(pack, *, alternate_first=False):
    soft = {
        "SELECTED_OBJECT": "NONE",
        "SELECTION_BASIS": "NO_PREFERENCE",
        "PRAGMATIC_PREFERENCE": "NONE",
        "EVIDENCE_STATE": "SOFT_AMBIGUITY",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }
    direct = {
        "SELECTED_OBJECT": "CANDIDATE_A",
        "SELECTION_BASIS": "LEXICAL_EXACT",
        "PRAGMATIC_PREFERENCE": "CANDIDATE_A",
        "EVIDENCE_STATE": "DIRECTLY_DEFINED",
        "ASSESSMENT_PROCESS_STATE": "COMPLETE",
    }
    labels = [{
        "annotation_id": item["annotation_id"],
        "criteria": direct if alternate_first and index == 0 else soft,
        "criterion_notes": {
            axis: "Fixture note." for axis in soft
        },
        "criterion_confidence": {
            axis: 0.9 for axis in soft
        },
        "tuple_rationale": "Fixture rationale.",
    } for index, item in enumerate(pack["items"])]
    return {
        "panel_version": pack["panel_version"],
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture",
        "blinding_attestation": (
            pack["response_contract"]["required_blinding_attestation"]
        ),
        "labels": labels,
    }


def test_annotation_validation_and_anonymous_adjudication_pack():
    corpus = build_source_ontology_holdout()
    preregistration = build_source_ontology_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_source_ontology_ablation(
        corpus=corpus,
        preregistration=preregistration,
        adapter=OntologyFixtureProvider(),
    )
    packs, panel_manifest = build_source_ontology_external_panel(
        corpus=corpus,
        run=run,
    )
    responses = (
        annotation_response(packs[0]),
        annotation_response(packs[1], alternate_first=True),
    )
    for response, pack in zip(responses, packs):
        validate_source_ontology_annotation_response(response, pack=pack)
    adjudication_pack, adjudication_manifest = (
        build_source_ontology_external_adjudication(
            packs=packs,
            panel_manifest=panel_manifest,
            responses=responses,
            corpus=corpus,
        )
    )
    validate_source_ontology_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={
            "packs": packs,
            "panel_manifest": panel_manifest,
            "responses": responses,
            "corpus": corpus,
        },
    )
    assert adjudication_manifest["agreement_object_count"] == 23
    assert adjudication_manifest["disagreement_object_count"] == 1
    item = adjudication_pack["items"][0]
    position = item["anonymous_full_tuple_positions"][0]
    response = {
        "panel_version": adjudication_pack["panel_version"],
        "adjudication_version": adjudication_pack["adjudication_version"],
        "panel_id": adjudication_pack["panel_id"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudicator_provider": "Moonshot",
        "adjudicator_model": "Kimi-K3",
        "adjudication_session_ref": "fixture",
        "blinding_attestation": (
            adjudication_pack["response_contract"][
                "required_blinding_attestation"
            ]
        ),
        "decisions": [{
            "adjudication_id": item["adjudication_id"],
            "criteria": position["criteria"],
            "decision_basis": position["position_id"],
            "confidence": 0.9,
            "rationale": "Fixture adjudication.",
        }],
    }
    validate_source_ontology_adjudication_response(
        response,
        pack=adjudication_pack,
    )
    response["decisions"][0]["criteria"] = {
        **position["criteria"],
        "PRAGMATIC_PREFERENCE": "UNCERTAIN",
    }
    with pytest.raises(ValueError):
        validate_source_ontology_adjudication_response(
            response,
            pack=adjudication_pack,
        )
