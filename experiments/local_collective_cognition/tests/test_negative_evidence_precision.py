from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_precision_calibration import (  # noqa: E402
    build_precision_calibration,
    validate_precision_calibration,
)
from local_collective_cognition.negative_evidence_precision_contracts import (  # noqa: E402
    CONFIRMATION_TASK_KIND,
    validate_confirmation,
)
from local_collective_cognition.negative_evidence_precision_fusion import (  # noqa: E402
    BASELINE,
    FABRICATION,
    LANES,
    LIVE_AMBIGUITY,
    MONOLITHIC_LANES,
    VETO_CONFIRMATION,
)
from local_collective_cognition.negative_evidence_precision_holdout import (  # noqa: E402
    CASES,
    CATEGORIES,
    SURFACE_STYLES,
    build_precision_corpus_artifact,
    validate_precision_corpus_artifact,
    validate_precision_corpus_spec,
)
from local_collective_cognition.negative_evidence_precision_runtime import (  # noqa: E402
    NegativeEvidencePrecisionRuntime,
    validate_precision_candidate_run,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    build_reference_panel,
    validate_reference_panel,
)
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_CRITERIA,
    JUDGE_TASK_KIND,
)


class FixtureAdapter:
    def __init__(self, lane, *, absent_ids=(), veto_ids=(), reject_ids=()):
        self.lane = lane
        self.absent_ids = set(absent_ids)
        self.veto_ids = set(veto_ids)
        self.reject_ids = set(reject_ids)
        if lane in MONOLITHIC_LANES:
            task_kind = JUDGE_TASK_KIND
        elif lane == LIVE_AMBIGUITY:
            task_kind = TASK_KINDS[LIVE_AMBIGUITY_AUDIT]
        elif lane == FABRICATION:
            task_kind = TASK_KINDS[FABRICATION_AUDIT]
        else:
            task_kind = CONFIRMATION_TASK_KIND
        self.profile = ProviderCapabilityProfile(
            provider_id=f"fixture-{lane.lower()}", model_id="fixture-model",
            task_kinds=(task_kind,), max_timeout_seconds=180,
        )

    def invoke(self, task):
        assessments = []
        for candidate in task.inputs["blind_candidates"]:
            blind_id = candidate["blind_candidate_id"]
            if self.lane in MONOLITHIC_LANES:
                criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
                if blind_id in self.absent_ids:
                    criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                assessments.append({
                    "blind_candidate_id": blind_id, "criteria": criteria,
                    "confidence": 0.8, "audit_note": "Fixture judgment.",
                    "fatal_issue": "",
                })
            elif self.lane in {LIVE_AMBIGUITY, FABRICATION}:
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "state": "VETO" if blind_id in self.veto_ids else "PASS",
                    "evidence_basis": "Fixture evidence.",
                    "counterfactual": "Fixture counterfactual.",
                    "confidence": 0.8,
                })
            else:
                reject = blind_id in self.reject_ids
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "state": "REJECT_VETO" if reject else "CONFIRM_VETO",
                    "requested_object_status": "GENUINELY_OPEN" if reject else "RIVAL_INVALID_OR_EQUIVALENT",
                    "question_function": "WOULD_DISCRIMINATE" if reject else "WOULD_NOT_DISCRIMINATE",
                    "explicit_disambiguator_quote": "",
                    "evidence_basis": "Fixture independent confirmation.",
                    "confidence": 0.8,
                })
        result = {
            "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
            "assessments": assessments,
            "evidence_refs": list(task.allowed_evidence),
        }
        if self.lane in {LIVE_AMBIGUITY, FABRICATION}:
            result["audit_kind"] = LIVE_AMBIGUITY_AUDIT if self.lane == LIVE_AMBIGUITY else FABRICATION_AUDIT
        return {"result": result, "usage": {"input_tokens": 30, "output_tokens": 20}, "provenance_refs": list(task.allowed_evidence)}


class FailingConfirmationAdapter(FixtureAdapter):
    def invoke(self, task):
        raise TimeoutError("fixture confirmation timeout")


def _ids(corpus):
    return [
        item["blind_candidate_id"]
        for batch in corpus["blind_surface"]["batches"]
        for item in batch["public_candidates"]
    ]


def _run(corpus):
    ids = _ids(corpus)
    adapters = {
        lane: FixtureAdapter(
            lane,
            veto_ids=(ids[:4] if lane == LIVE_AMBIGUITY else ids[4:6] if lane == FABRICATION else ()),
            reject_ids=(ids[:2] if lane == VETO_CONFIRMATION else ()),
        )
        for lane in LANES
    }
    return NegativeEvidencePrecisionRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-precision", adapters=adapters,
    )


def _reference(corpus, nonusable_ids):
    labels = []
    for blind_id in sorted(corpus["blind_surface"]["bindings"]):
        criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
        if blind_id in nonusable_ids:
            criteria[JUDGE_CRITERIA[0]] = "ABSENT"
        labels.append({"blind_candidate_id": blind_id, "criteria": criteria})
    commitment = {
        "labels": labels, "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False, "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def test_precision_corpus_is_fresh_balanced_and_blind():
    validate_precision_corpus_spec()
    corpus = build_precision_corpus_artifact()
    validate_precision_corpus_artifact(corpus)
    assert len(CASES) == 24
    assert all(sum(case.construction_category == category for case in CASES) == 4 for category in CATEGORIES)
    assert all(sum(case.surface_style == style for case in CASES) == 6 for style in SURFACE_STYLES)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=corpus)
    public = json.dumps(packs, sort_keys=True)
    assert "construction_category" not in public
    assert all(len(pack["items"]) == 24 for pack in packs)


def test_confirmation_contract_rejects_inconsistent_restoration():
    payload = {
        "batch_id": "b1",
        "assessments": [{
            "blind_candidate_id": "c1", "state": "REJECT_VETO",
            "requested_object_status": "EXPLICITLY_FIXED",
            "question_function": "WOULD_DISCRIMINATE",
            "explicit_disambiguator_quote": "fixed wording",
            "evidence_basis": "Fixture.", "confidence": 0.8,
        }],
        "evidence_refs": ["corpus://fixture"],
    }
    with pytest.raises(ValueError, match="rejection_inconsistent"):
        validate_confirmation(
            payload, batch_id="b1", candidate_ids=("c1",),
            evidence_refs=("corpus://fixture",),
        )


def test_confirmation_is_conditional_and_cannot_promote_baseline():
    corpus = build_precision_corpus_artifact()
    run = _run(corpus)
    validate_precision_candidate_run(run, corpus_artifact=corpus)
    ids = _ids(corpus)
    assert set(run["fusion"]["confirmation_target_ids"]) == set(ids[:4])
    records = {item["blind_candidate_id"]: item for item in run["fusion"]["records"]}
    assert records[ids[0]]["naive_veto_state"] == "UNUSABLE"
    assert records[ids[0]]["confirmed_veto_state"] == "USABLE"
    assert records[ids[2]]["confirmed_veto_state"] == "UNUSABLE"
    assert run["fusion"]["arm_accounting"]["CONFIRMED_VETO"]["attributed_provider_calls"] <= 48

    adapters = {
        lane: FixtureAdapter(
            lane, absent_ids=(ids[0],),
            veto_ids=(ids[0],) if lane == LIVE_AMBIGUITY else (),
            reject_ids=(ids[0],) if lane == VETO_CONFIRMATION else (),
        )
        for lane in LANES
    }
    blocked = NegativeEvidencePrecisionRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-no-promotion", adapters=adapters,
    )
    record = next(item for item in blocked["fusion"]["records"] if item["blind_candidate_id"] == ids[0])
    assert record["confirmation_requested"] is False
    assert record["confirmed_veto_state"] == "UNUSABLE"


def test_precision_confirmation_gain_passes_frozen_fixture():
    corpus = build_precision_corpus_artifact()
    run = _run(corpus)
    ids = _ids(corpus)
    reference = _reference(corpus, set(ids[2:6]))
    calibration = build_precision_calibration(
        corpus_artifact=corpus, candidate_run=run, reference_artifact=reference,
    )
    validate_precision_calibration(
        calibration, corpus_artifact=corpus,
        candidate_run=run, reference_artifact=reference,
    )
    assert calibration["arm_metrics"]["CONFIRMED_VETO"]["packet_accuracy"] == 1.0
    assert calibration["confirmed_usable_recall_gain_vs_naive"] >= 0.04
    assert calibration["candidate_state"] == "PRECISION_CONFIRMED_VETO_CANDIDATE"


def test_precision_fusion_tamper_fails_after_outer_rehash():
    corpus = build_precision_corpus_artifact()
    run = _run(corpus)
    tampered = deepcopy(run)
    original = tampered["fusion"]["records"][0]["confirmed_veto_state"]
    tampered["fusion"]["records"][0]["confirmed_veto_state"] = (
        "UNUSABLE" if original == "USABLE" else "USABLE"
    )
    tampered["candidate_run_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "candidate_run_hash"
    })
    with pytest.raises(ValueError, match="fusion_invalid"):
        validate_precision_candidate_run(tampered, corpus_artifact=corpus)


def test_confirmation_failure_is_preserved_as_unresolved():
    corpus = build_precision_corpus_artifact()
    ids = _ids(corpus)
    adapters = {
        lane: FixtureAdapter(
            lane, veto_ids=(ids[0],) if lane == LIVE_AMBIGUITY else (),
        )
        for lane in LANES
    }
    adapters[VETO_CONFIRMATION] = FailingConfirmationAdapter(VETO_CONFIRMATION)
    run = NegativeEvidencePrecisionRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-confirmation-failure", adapters=adapters,
    )
    validate_precision_candidate_run(run, corpus_artifact=corpus)
    record = next(item for item in run["fusion"]["records"] if item["blind_candidate_id"] == ids[0])
    assert record["confirmation_requested"] is True
    assert record["confirmation_state"] == "MISSING"
    assert record["confirmed_veto_state"] == "UNRESOLVED"
