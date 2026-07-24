from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.negative_evidence_audit_contracts import FABRICATION_AUDIT, LIVE_AMBIGUITY_AUDIT, TASK_KINDS  # noqa: E402
from local_collective_cognition.negative_evidence_warrant_calibration import build_warrant_calibration, validate_warrant_calibration  # noqa: E402
from local_collective_cognition.negative_evidence_warrant_contracts import WARRANT_TASK_KIND, derive_runtime_warrant_state  # noqa: E402
from local_collective_cognition.negative_evidence_warrant_fusion import BASELINE, FABRICATION, LANES, LEGACY_LIVE, MONOLITHIC_LANES, WARRANT_LIVE  # noqa: E402
from local_collective_cognition.negative_evidence_warrant_holdout import CASES, CATEGORIES, SURFACE_STYLES, build_warrant_corpus_artifact, validate_warrant_corpus_artifact, validate_warrant_corpus_spec  # noqa: E402
from local_collective_cognition.negative_evidence_warrant_runtime import NegativeEvidenceWarrantRuntime, RECOVERY_RUNTIME_VERSION, validate_warrant_candidate_run  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_panel_pack import build_reference_panel, validate_reference_panel  # noqa: E402
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_CRITERIA, JUDGE_TASK_KIND  # noqa: E402


class FixtureAdapter:
    def __init__(self, lane, *, absent=(), legacy_veto=(), warrants=None, fabrication_veto=()):
        self.lane = lane
        self.absent = set(absent)
        self.legacy_veto = set(legacy_veto)
        self.warrants = warrants or {}
        self.fabrication_veto = set(fabrication_veto)
        kind = (
            JUDGE_TASK_KIND if lane in MONOLITHIC_LANES
            else WARRANT_TASK_KIND if lane == WARRANT_LIVE
            else TASK_KINDS[LIVE_AMBIGUITY_AUDIT if lane == LEGACY_LIVE else FABRICATION_AUDIT]
        )
        self.profile = ProviderCapabilityProfile(
            provider_id=f"fixture-{lane.lower()}",
            model_id="fixture",
            task_kinds=(kind,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        assessments = []
        for candidate in task.inputs["blind_candidates"]:
            item_id = candidate["blind_candidate_id"]
            if self.lane in MONOLITHIC_LANES:
                criteria = {key: "PRESENT" for key in JUDGE_CRITERIA}
                if item_id in self.absent:
                    criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                assessments.append({
                    "blind_candidate_id": item_id,
                    "criteria": criteria,
                    "confidence": 0.8,
                    "audit_note": "Fixture.",
                    "fatal_issue": "",
                })
            elif self.lane == WARRANT_LIVE:
                warrant = self.warrants.get(item_id, "NONE")
                relation = {
                    "RIVAL_INVALID": "RIVAL_A_INVALID",
                    "RIVALS_EQUIVALENT": "EQUIVALENT",
                }.get(warrant, "BOTH_VALID_DISTINCT")
                assessments.append({
                    "blind_candidate_id": item_id,
                    "provider_state": "PASS" if warrant == "NONE" else "VETO",
                    "warrant_kind": warrant,
                    "decisive_quote": candidate["public_prompt"].split()[0] if warrant == "EXPLICIT_FIXATION" else "",
                    "rival_relation": relation,
                    "question_effect": "DOES_NOT_DISCRIMINATE" if warrant == "QUESTION_INEFFECTIVE_ONLY" else "DISCRIMINATES",
                    "evidence_basis": "Fixture warrant.",
                    "counterfactual": "Fixture counterfactual.",
                    "confidence": 0.8,
                })
            else:
                veto_ids = self.legacy_veto if self.lane == LEGACY_LIVE else self.fabrication_veto
                assessments.append({
                    "blind_candidate_id": item_id,
                    "state": "VETO" if item_id in veto_ids else "PASS",
                    "evidence_basis": "Fixture.",
                    "counterfactual": "Fixture flip.",
                    "confidence": 0.8,
                })
        result = {
            "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
            "assessments": assessments,
            "evidence_refs": list(task.allowed_evidence),
        }
        if self.lane in {LEGACY_LIVE, FABRICATION}:
            result["audit_kind"] = LIVE_AMBIGUITY_AUDIT if self.lane == LEGACY_LIVE else FABRICATION_AUDIT
        return {
            "result": result,
            "usage": {"input_tokens": 30, "output_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def _ids(corpus):
    return [item["blind_candidate_id"] for batch in corpus["blind_surface"]["batches"] for item in batch["public_candidates"]]


def _run(corpus, *, absent=()):
    ids = _ids(corpus)
    warrants = {
        **{item_id: "EXPLICIT_FIXATION" for item_id in ids[12:16]},
        **{item_id: "RIVAL_INVALID" for item_id in ids[16:18]},
        **{item_id: "RIVALS_EQUIVALENT" for item_id in ids[18:20]},
    }
    adapters = {
        lane: FixtureAdapter(
            lane,
            absent=absent,
            legacy_veto=set(ids[0:4] + ids[12:20]),
            warrants=warrants,
            fabrication_veto=set(ids[20:24]),
        )
        for lane in LANES
    }
    return NegativeEvidenceWarrantRuntime(corpus_artifact=corpus, runtime_version=RECOVERY_RUNTIME_VERSION).evaluate(
        experiment_id="fixture-warrant",
        adapters=adapters,
    )


def _reference(corpus):
    nonusable = set(_ids(corpus)[12:24])
    labels = []
    for item_id in sorted(corpus["blind_surface"]["bindings"]):
        criteria = {key: "PRESENT" for key in JUDGE_CRITERIA}
        if item_id in nonusable:
            criteria[JUDGE_CRITERIA[0]] = "ABSENT"
        labels.append({"blind_candidate_id": item_id, "criteria": criteria})
    commitment = {
        "labels": labels,
        "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def test_warrant_corpus_is_fresh_balanced_and_blind():
    validate_warrant_corpus_spec()
    corpus = build_warrant_corpus_artifact()
    validate_warrant_corpus_artifact(corpus)
    assert len(CASES) == 24
    assert all(sum(item.construction_category == category for item in CASES) == 4 for category in CATEGORIES)
    assert all(sum(item.surface_style == style for item in CASES) == 6 for style in SURFACE_STYLES)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=corpus)
    assert all(len(pack["items"]) == 24 for pack in packs)


def test_runtime_executes_only_frozen_warrant_classes():
    base = {
        "provider_state": "VETO",
        "warrant_kind": "EXPLICIT_FIXATION",
        "decisive_quote": "Report revenue",
        "rival_relation": "BOTH_VALID_DISTINCT",
        "question_effect": "DISCRIMINATES",
    }
    assert derive_runtime_warrant_state(base, public_prompt="Report revenue in euros.") == "EXECUTABLE_VETO"
    assert derive_runtime_warrant_state(base, public_prompt="Give revenue in euros.") == "NON_EXECUTABLE_VETO"
    question_only = {**base, "warrant_kind": "QUESTION_INEFFECTIVE_ONLY", "decisive_quote": "", "question_effect": "DOES_NOT_DISCRIMINATE"}
    assert derive_runtime_warrant_state(question_only, public_prompt="Report revenue in euros.") == "NON_EXECUTABLE_VETO"


def test_equal_budget_arms_cannot_promote_baseline():
    corpus = build_warrant_corpus_artifact()
    ids = _ids(corpus)
    run = _run(corpus, absent=(ids[0],))
    validate_warrant_candidate_run(run, corpus_artifact=corpus)
    accounting = run["fusion"]["arm_accounting"]
    assert accounting["NAIVE_REPLICATION"]["attributed_provider_calls"] == accounting["WARRANTED_VETO"]["attributed_provider_calls"] == 36
    record = next(item for item in run["fusion"]["records"] if item["blind_candidate_id"] == ids[0])
    assert record["naive_replication_state"] == "UNUSABLE"
    assert record["warranted_veto_state"] == "UNUSABLE"


def test_warrant_gate_can_recover_recall_without_false_usable_harm():
    corpus = build_warrant_corpus_artifact()
    run = _run(corpus)
    reference = _reference(corpus)
    calibration = build_warrant_calibration(corpus_artifact=corpus, candidate_run=run, reference_artifact=reference)
    validate_warrant_calibration(calibration, corpus_artifact=corpus, candidate_run=run, reference_artifact=reference)
    assert calibration["candidate_state"] == "WARRANTED_VETO_CANDIDATE"
    assert calibration["arm_metrics"]["WARRANTED_VETO"]["usable_recall"] == 1.0
    assert calibration["warranted_gate_results"]["usable_recall_gain_vs_naive"] is True
    tampered = deepcopy(run)
    target = next(item for item in tampered["fusion"]["records"] if item["warranted_veto_state"] == "USABLE")
    target["warranted_veto_state"] = "UNUSABLE"
    tampered["candidate_run_hash"] = hash_payload({key: value for key, value in tampered.items() if key != "candidate_run_hash"})
    with pytest.raises(ValueError, match="fusion_invalid"):
        validate_warrant_candidate_run(tampered, corpus_artifact=corpus)
