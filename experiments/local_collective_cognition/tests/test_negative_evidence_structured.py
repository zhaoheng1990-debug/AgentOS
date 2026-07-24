from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.negative_evidence_audit_contracts import FABRICATION_AUDIT, LIVE_AMBIGUITY_AUDIT, TASK_KINDS  # noqa: E402
from local_collective_cognition.negative_evidence_structured_calibration import build_structured_calibration, validate_structured_calibration  # noqa: E402
from local_collective_cognition.negative_evidence_structured_contracts import STRUCTURED_LIVE_TASK_KIND, derive_structured_state  # noqa: E402
from local_collective_cognition.negative_evidence_structured_fusion import BASELINE, FABRICATION, LANES, LEGACY_LIVE, MONOLITHIC_LANES, STRUCTURED_LIVE  # noqa: E402
from local_collective_cognition.negative_evidence_structured_holdout import CASES, CATEGORIES, SURFACE_STYLES, build_structured_corpus_artifact, validate_structured_corpus_artifact, validate_structured_corpus_spec  # noqa: E402
from local_collective_cognition.negative_evidence_structured_runtime import NegativeEvidenceStructuredRuntime, validate_structured_candidate_run  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_panel_pack import build_reference_panel, validate_reference_panel  # noqa: E402
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_TASK_KIND  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, *, absent=(), legacy_veto=(), structured_veto=(), fabrication_veto=()):
        self.lane = lane; self.absent = set(absent); self.legacy_veto = set(legacy_veto)
        self.structured_veto = set(structured_veto); self.fabrication_veto = set(fabrication_veto)
        kind = JUDGE_TASK_KIND if lane in MONOLITHIC_LANES else STRUCTURED_LIVE_TASK_KIND if lane == STRUCTURED_LIVE else TASK_KINDS[LIVE_AMBIGUITY_AUDIT if lane == LEGACY_LIVE else FABRICATION_AUDIT]
        self.profile = ProviderCapabilityProfile(provider_id=f"fixture-{lane.lower()}", model_id="fixture", task_kinds=(kind,), max_timeout_seconds=180)

    def invoke(self, task):
        assessments = []
        for candidate in task.inputs["blind_candidates"]:
            item_id = candidate["blind_candidate_id"]
            if self.lane in MONOLITHIC_LANES:
                criteria = {key: "PRESENT" for key in JUDGE_CRITERIA}
                if item_id in self.absent: criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                assessments.append({"blind_candidate_id": item_id, "criteria": criteria, "confidence": 0.8, "audit_note": "Fixture.", "fatal_issue": ""})
            elif self.lane == STRUCTURED_LIVE:
                veto = item_id in self.structured_veto
                assessments.append({
                    "blind_candidate_id": item_id,
                    "requested_object_status": "EXPLICITLY_FIXED" if veto else "GENUINELY_OPEN",
                    "rival_relation": "RIVAL_A_INVALID" if veto else "BOTH_VALID_DISTINCT",
                    "question_function": "WOULD_DISCRIMINATE",
                    "explicit_disambiguator_quote": "explicit phrase" if veto else "",
                    "evidence_basis": "Fixture semantic subjudgments.", "confidence": 0.8,
                })
            else:
                veto = item_id in (self.legacy_veto if self.lane == LEGACY_LIVE else self.fabrication_veto)
                assessments.append({"blind_candidate_id": item_id, "state": "VETO" if veto else "PASS", "evidence_basis": "Fixture.", "counterfactual": "Fixture flip.", "confidence": 0.8})
        result = {"batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0], "assessments": assessments, "evidence_refs": list(task.allowed_evidence)}
        if self.lane in {LEGACY_LIVE, FABRICATION}: result["audit_kind"] = LIVE_AMBIGUITY_AUDIT if self.lane == LEGACY_LIVE else FABRICATION_AUDIT
        return {"result": result, "usage": {"input_tokens": 30, "output_tokens": 20}, "provenance_refs": list(task.allowed_evidence)}


def _ids(corpus):
    return [x["blind_candidate_id"] for batch in corpus["blind_surface"]["batches"] for x in batch["public_candidates"]]


def _run(corpus, *, absent=()):
    ids = _ids(corpus)
    legacy = set(ids[12:15] + ids[16:19]); structured = set(ids[12:20]); fabrication = set(ids[20:24])
    adapters = {lane: FixtureAdapter(lane, absent=absent, legacy_veto=legacy, structured_veto=structured, fabrication_veto=fabrication) for lane in LANES}
    return NegativeEvidenceStructuredRuntime(corpus_artifact=corpus).evaluate(experiment_id="fixture-structured", adapters=adapters)


def _reference(corpus):
    nonusable = set(_ids(corpus)[12:24]); labels = []
    for item_id in sorted(corpus["blind_surface"]["bindings"]):
        criteria = {key: "PRESENT" for key in JUDGE_CRITERIA}
        if item_id in nonusable: criteria[JUDGE_CRITERIA[0]] = "ABSENT"
        labels.append({"blind_candidate_id": item_id, "criteria": criteria})
    commitment = {"labels": labels, "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE", "ground_truth_claim": False, "selection_authority": False, "retention_authority": False}
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def test_structured_corpus_is_fresh_balanced_and_blind():
    validate_structured_corpus_spec(); corpus = build_structured_corpus_artifact(); validate_structured_corpus_artifact(corpus)
    assert len(CASES) == 24
    assert all(sum(x.construction_category == category for x in CASES) == 4 for category in CATEGORIES)
    assert all(sum(x.surface_style == style for x in CASES) == 6 for style in SURFACE_STYLES)
    packs, manifest = build_reference_panel(semantic_artifact=corpus); validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=corpus)
    assert all(len(pack["items"]) == 24 for pack in packs)


def test_runtime_derives_structured_state_from_semantic_fields():
    base = {"requested_object_status": "GENUINELY_OPEN", "rival_relation": "BOTH_VALID_DISTINCT", "question_function": "WOULD_DISCRIMINATE"}
    assert derive_structured_state(base) == "PASS"
    fixed = {**base, "requested_object_status": "EXPLICITLY_FIXED"}
    assert derive_structured_state(fixed) == "VETO"
    uncertain = {**base, "question_function": "UNCERTAIN"}
    assert derive_structured_state(uncertain) == "UNCERTAIN"


def test_equal_budget_arms_cannot_promote_baseline():
    corpus = build_structured_corpus_artifact(); ids = _ids(corpus); run = _run(corpus, absent=(ids[0],))
    validate_structured_candidate_run(run, corpus_artifact=corpus)
    accounting = run["fusion"]["arm_accounting"]
    assert accounting["NAIVE_REPLICATION"]["attributed_provider_calls"] == accounting["STRUCTURED_DEFER"]["attributed_provider_calls"] == 36
    record = next(x for x in run["fusion"]["records"] if x["blind_candidate_id"] == ids[0])
    assert record["naive_replication_state"] == "UNUSABLE"
    assert record["structured_defer_state"] == "UNUSABLE"


def test_dual_admission_gates_identify_fixture_gain_and_tamper():
    corpus = build_structured_corpus_artifact(); run = _run(corpus); reference = _reference(corpus)
    calibration = build_structured_calibration(corpus_artifact=corpus, candidate_run=run, reference_artifact=reference)
    validate_structured_calibration(calibration, corpus_artifact=corpus, candidate_run=run, reference_artifact=reference)
    assert calibration["candidate_state"] == "NAIVE_AND_STRUCTURED_DEFER_CANDIDATES"
    tampered = deepcopy(run); tampered["fusion"]["records"][0]["structured_defer_state"] = "UNUSABLE"; tampered["candidate_run_hash"] = hash_payload({k:v for k,v in tampered.items() if k != "candidate_run_hash"})
    with pytest.raises(ValueError, match="fusion_invalid"):
        validate_structured_candidate_run(tampered, corpus_artifact=corpus)
