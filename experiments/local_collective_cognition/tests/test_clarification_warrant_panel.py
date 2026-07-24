from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.clarification_two_axis_contracts import TWO_AXIS_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_warrant_calibration import build_warrant_calibration  # noqa: E402
from local_collective_cognition.clarification_warrant_holdout import build_warrant_holdout_artifact  # noqa: E402
from local_collective_cognition.clarification_warrant_panel import CRITERIA, PANEL_VERSION, build_warrant_adjudication, build_warrant_panel, build_warrant_reference, validate_adjudication_response, validate_annotation_response, validate_warrant_adjudication, validate_warrant_panel, validate_warrant_reference  # noqa: E402
from local_collective_cognition.clarification_warrant_panel_calibration import build_warrant_panel_recalibration, validate_warrant_panel_recalibration  # noqa: E402
from local_collective_cognition.clarification_warrant_contracts import WARRANT_TASK_KIND  # noqa: E402
from local_collective_cognition.clarification_warrant_runtime import BASELINE_LANE, LANES, ClarificationWarrantRuntime  # noqa: E402
from local_collective_cognition.post_experiment_analysis import build_warrant_panel_recalibration_analysis  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def annotation_response(pack, manifest, oracle, *, disagree=False):
    labels = []
    for item in pack["items"]:
        blind_id = manifest["private_lane_bindings"][pack["lane_id"]][item["annotation_id"]]
        truth = oracle[blind_id]
        criteria = {
            "EXPLICIT_SELECTION": truth["explicit_selection"],
            "PRAGMATIC_PREFERENCE": truth["pragmatic_preference"],
            "ASSESSMENT_COMPLETENESS": "COMPLETE",
        }
        if disagree and not labels:
            criteria["PRAGMATIC_PREFERENCE"] = "NONE" if criteria["PRAGMATIC_PREFERENCE"] != "NONE" else "CANDIDATE_A"
        labels.append({
            "annotation_id": item["annotation_id"],
            "criteria": criteria,
            "criterion_notes": {criterion: "Fixture independent judgment." for criterion in CRITERIA},
            "criterion_confidence": {criterion: 0.8 for criterion in CRITERIA},
        })
    return {
        "panel_version": PANEL_VERSION,
        "panel_id": pack["panel_id"],
        "lane_id": pack["lane_id"],
        "pack_hash": pack["pack_hash"],
        "annotator_provider": pack["expected_annotator"]["provider"],
        "annotator_model": pack["expected_annotator"]["model"],
        "annotation_session_ref": "fixture-session-" + pack["lane_id"],
        "labels": labels,
    }


def test_warrant_panel_builds_blind_packs_and_adjudicates_disagreement():
    corpus = build_warrant_holdout_artifact()
    packs, manifest = build_warrant_panel(corpus_artifact=corpus)
    validate_warrant_panel(packs=packs, manifest=manifest, corpus_artifact=corpus)
    assert [item["annotation_id"] for item in packs[0]["items"]] != [item["annotation_id"] for item in packs[1]["items"]]
    assert all("construction" not in item for pack in packs for item in pack["items"])
    oracle = corpus["private_oracle"]["bindings"]
    responses = (
        annotation_response(packs[0], manifest, oracle),
        annotation_response(packs[1], manifest, oracle, disagree=True),
    )
    for pack, response in zip(packs, responses):
        validate_annotation_response(response, pack=pack)
    adjudication, private = build_warrant_adjudication(packs=packs, panel_manifest=manifest, responses=responses)
    validate_warrant_adjudication(pack=adjudication, manifest=private, panel_packs=packs, panel_manifest=manifest, responses=responses)
    assert private["disagreement_count"] == 1
    assert private["agreement_count"] == 71
    decisions = []
    for item in adjudication["items"]:
        position = item["positions"][0]
        decisions.append({"adjudication_id": item["adjudication_id"], "selected_state": position["state"], "decision_basis": position["position_id"], "confidence": 0.75, "rationale": "Fixture adjudication."})
    k3 = {
        "panel_version": PANEL_VERSION,
        "panel_id": adjudication["panel_id"],
        "adjudication_pack_hash": adjudication["pack_hash"],
        "adjudicator_provider": "Moonshot",
        "adjudicator_model": "Kimi-K3",
        "adjudication_session_ref": "fixture-k3-session",
        "blinding_attestation": {"pack_only_context": True, "annotator_identity_unavailable": True, "source_identity_unavailable": True, "prior_scores_unavailable": True, "external_pairing_not_used": True},
        "decisions": decisions,
    }
    validate_adjudication_response(k3, pack=adjudication)
    reference = build_warrant_reference(adjudication_pack=adjudication, adjudication_manifest=private, response=k3)
    assert reference["candidate_state"] == "WARRANT_MODEL_PANEL_REFERENCE_CANDIDATE"
    assert reference["label_count"] == 72


def test_warrant_panel_rejects_response_identity_tamper():
    corpus = build_warrant_holdout_artifact()
    packs, manifest = build_warrant_panel(corpus_artifact=corpus)
    response = annotation_response(packs[0], manifest, corpus["private_oracle"]["bindings"])
    response["pack_hash"] = "0" * 64
    with pytest.raises(ValueError, match="binding_invalid"):
        validate_annotation_response(response, pack=packs[0])


def test_warrant_panel_rejects_pack_tamper_even_with_rehashed_pack():
    corpus = build_warrant_holdout_artifact()
    packs, manifest = build_warrant_panel(corpus_artifact=corpus)
    tampered = deepcopy(packs[0])
    tampered["items"][0]["candidate_a"] = "tampered"
    tampered["pack_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "pack_hash"})
    with pytest.raises(ValueError, match="pack_binding_invalid"):
        validate_warrant_panel(packs=(tampered, packs[1]), manifest=manifest, corpus_artifact=corpus)


class CandidateFixtureAdapter:
    def __init__(self, lane, oracle):
        self.lane = lane
        self.oracle = oracle
        kind = TWO_AXIS_TASK_KIND if lane == BASELINE_LANE else WARRANT_TASK_KIND
        self.profile = ProviderCapabilityProfile(provider_id="panel-fixture-" + lane.lower(), model_id="fixture", task_kinds=(kind,), max_timeout_seconds=180)

    def invoke(self, task):
        items = []
        for case in task.inputs["public_cases"]:
            truth = self.oracle[case["blind_case_id"]]
            if self.lane == BASELINE_LANE:
                selection = truth["explicit_selection"] if truth["explicit_selection"] != "NONE" else truth["pragmatic_preference"]
                items.append({"blind_case_id": case["blind_case_id"], "request_object_quote": case["public_prompt"], "object_selection": selection, "assessment_status": "RESOLVED", "decisive_quote": case["public_prompt"], "selection_basis": "Fixture.", "status_basis": "Fixture complete."})
            else:
                hard = truth["construction"] == "EXPLICIT"
                items.append({"blind_case_id": case["blind_case_id"], "request_object_quote": case["public_prompt"], "explicit_selection": truth["explicit_selection"], "pragmatic_preference": truth["pragmatic_preference"], "assessment_status": "RESOLVED", "warrant_type": "EXACT_OBJECT_MENTION" if hard else "DEFAULT_COMPATIBILITY", "warrant_quote": case["public_prompt"] if hard else "NONE", "preference_basis": "Fixture.", "status_basis": "Fixture complete."})
        return {"result": {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0], "assessments": items, "evidence_refs": list(task.allowed_evidence)}, "usage": {"input_tokens": 40, "output_tokens": 30}, "provenance_refs": list(task.allowed_evidence)}


def test_panel_recalibration_is_diagnostic_and_reproducible():
    corpus = build_warrant_holdout_artifact()
    oracle = corpus["private_oracle"]["bindings"]
    run = ClarificationWarrantRuntime(corpus_artifact=corpus).evaluate(experiment_id="panel-audit-fixture", adapters={lane: CandidateFixtureAdapter(lane, oracle) for lane in LANES})
    frozen = build_warrant_calibration(corpus_artifact=corpus, candidate_run=run)
    packs, manifest = build_warrant_panel(corpus_artifact=corpus)
    responses = tuple(annotation_response(pack, manifest, oracle) for pack in packs)
    adjudication, private = build_warrant_adjudication(packs=packs, panel_manifest=manifest, responses=responses)
    reference = build_warrant_reference(adjudication_pack=adjudication, adjudication_manifest=private)
    validate_warrant_reference(reference, adjudication_pack=adjudication, adjudication_manifest=private)
    inputs = {"corpus_artifact": corpus, "candidate_run": run, "frozen_calibration": frozen, "panel_reference": reference}
    audit = build_warrant_panel_recalibration(**inputs)
    validate_warrant_panel_recalibration(audit, **inputs)
    assert audit["metrics"]["runtime_category_accuracy"] == 1.0
    assert audit["post_hoc_admission_gate"] is False
    assert build_warrant_panel_recalibration_analysis(audit)["changes_frozen_gate_or_candidate_state"] is False
