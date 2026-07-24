from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from zipfile import ZipFile

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

FINALIZER_SPEC = importlib.util.spec_from_file_location(
    "receipt_quality_finalizer",
    PACK / "examples" / "finalize_receipt_quality_calibration.py",
)
FINALIZER = importlib.util.module_from_spec(FINALIZER_SPEC)
FINALIZER_SPEC.loader.exec_module(FINALIZER)

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.ambiguity_coordinator_holdout import (  # noqa: E402
    CASES as COORDINATOR_CASES,
)
from local_collective_cognition.ambiguity_hard_null_holdout import (  # noqa: E402
    CASES as HARD_NULL_CASES,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.receipt_quality_calibration_corpus import (  # noqa: E402
    CASES,
    CORPUS_SPEC,
    EVIDENCE_REFS,
    build_receipt_quality_corpus_artifact,
    validate_receipt_quality_corpus_artifact,
    validate_receipt_quality_corpus_spec,
)
from local_collective_cognition.receipt_quality_candidate_runtime import (  # noqa: E402
    ReceiptQualityCandidateRuntime,
    validate_receipt_quality_candidate_run,
)
from local_collective_cognition.receipt_quality_candidate_calibration import (  # noqa: E402
    build_receipt_quality_calibration,
    validate_receipt_quality_calibration,
)
from local_collective_cognition.structure_reference_panel_pack import (  # noqa: E402
    build_reference_panel,
    validate_reference_panel,
)
from local_collective_cognition.structure_semantic_judge_contracts import (  # noqa: E402
    JUDGE_CRITERIA,
    JUDGE_TASK_KIND,
)
from local_collective_cognition.unstated_ambiguity_holdout import (  # noqa: E402
    CASES as DISCOVERY_CASES,
)


class FixtureReceiptQualityAdapter:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-receipt-judge",
            model_id="fixture-judge",
            task_kinds=(JUDGE_TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.seen_inputs = []

    def invoke(self, task):
        self.seen_inputs.append(task.inputs)
        batch_id = task.task_id.rsplit("-fixture-receipt-judge-", 1)[-1]
        candidate = task.inputs["blind_candidates"][0]
        assessment = {
            "blind_candidate_id": candidate["blind_candidate_id"],
            "criteria": {criterion: "PRESENT" for criterion in JUDGE_CRITERIA},
            "confidence": 0.8,
            "audit_note": "Fixture criterion assessment.",
            "fatal_issue": "",
        }
        return {
            "result": {
                "batch_id": batch_id,
                "assessments": [assessment],
                "evidence_refs": list(task.allowed_evidence),
            },
            "usage": {"input_tokens": 20, "output_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_corpus_is_independent_and_balances_targeted_quality_controls():
    validate_receipt_quality_corpus_spec()
    assert CORPUS_SPEC["case_count"] == 14
    assert CORPUS_SPEC["criterion_count"] == 6
    assert all(
        CORPUS_SPEC["construction_target_counts"][criterion] == 2
        for criterion in JUDGE_CRITERIA
    )
    assert CORPUS_SPEC["construction_target_counts"]["FULLY_USABLE_CONTROL"] == 2
    predecessors = (*DISCOVERY_CASES, *COORDINATOR_CASES, *HARD_NULL_CASES)
    assert not ({case.item_id for case in CASES} & {case.item_id for case in predecessors})
    assert not (
        {case.public_prompt for case in CASES}
        & {case.prompt for case in predecessors}
    )


def test_public_panel_packs_hide_construction_targets_and_predecessor_labels():
    corpus = build_receipt_quality_corpus_artifact()
    validate_receipt_quality_corpus_artifact(corpus)
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=corpus,
    )
    public = json.dumps(packs, sort_keys=True)
    assert "construction_target" not in public
    assert "FULLY_USABLE_CONTROL" not in public
    assert "expected_state" not in public
    assert "construction_target" in json.dumps(manifest, sort_keys=True)
    assert {item["annotation_id"] for item in packs[0]["items"]}.isdisjoint(
        {item["annotation_id"] for item in packs[1]["items"]}
    )


def test_candidate_judgments_are_frozen_before_panel_labels_and_replayable():
    corpus = build_receipt_quality_corpus_artifact()
    adapter = FixtureReceiptQualityAdapter()
    run = ReceiptQualityCandidateRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-receipt-quality", adapter=adapter,
    )
    validate_receipt_quality_candidate_run(run, corpus_artifact=corpus)
    assert run["successful_batches"] == len(CASES)
    assert run["failed_batches"] == 0
    assert run["panel_labels_available_at_prediction_time"] is False
    assert run["predecessor_labels_used_for_tuning"] is False
    assert all(
        item["panel_reference_labels"] == "NOT_YET_AVAILABLE"
        and item["predecessor_labels"] == "WITHHELD_AND_FORBIDDEN"
        for item in adapter.seen_inputs
    )


def test_corpus_and_candidate_run_tamper_fail_closed():
    corpus = build_receipt_quality_corpus_artifact()
    tampered = deepcopy(corpus)
    tampered["report"]["ground_truth_claim"] = True
    tampered["artifact_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "artifact_hash"
    })
    with pytest.raises(ValueError, match="semantics_invalid"):
        validate_receipt_quality_corpus_artifact(tampered)

    run = ReceiptQualityCandidateRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-receipt-quality",
        adapter=FixtureReceiptQualityAdapter(),
    )
    run["panel_labels_available_at_prediction_time"] = True
    run["judge_run_hash"] = hash_payload({
        key: value for key, value in run.items() if key != "judge_run_hash"
    })
    with pytest.raises(ValueError, match="binding_invalid"):
        validate_receipt_quality_candidate_run(run, corpus_artifact=corpus)


def test_corpus_evidence_binding_is_distinct_from_prior_holdouts():
    corpus = build_receipt_quality_corpus_artifact()
    assert tuple(corpus["evidence_refs"]) == EVIDENCE_REFS
    assert all(
        trial["construction_expectation_is_ground_truth"] is False
        for trial in corpus["report"]["trials"]
    )


def test_later_reference_scores_frozen_predictions_without_granting_authority():
    corpus = build_receipt_quality_corpus_artifact()
    run = ReceiptQualityCandidateRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-receipt-quality",
        adapter=FixtureReceiptQualityAdapter(),
    )
    labels = [{
        "blind_candidate_id": blind_id,
        "criteria": {criterion: "PRESENT" for criterion in JUDGE_CRITERIA},
        "criterion_sources": {
            criterion: "GPT_GEMINI_AGREEMENT" for criterion in JUDGE_CRITERIA
        },
        "criterion_confidence": {criterion: 0.9 for criterion in JUDGE_CRITERIA},
    } for blind_id in sorted(corpus["blind_surface"]["bindings"])]
    reference_commitment = {
        "panel_version": "structure_model_reference_panel_v0_1",
        "panel_id": "fixture-panel",
        "panel_manifest_hash": "a" * 64,
        "adjudication_manifest_hash": "b" * 64,
        "adjudication_pack_hash": "c" * 64,
        "adjudication_response_hash": None,
        "labels": labels,
        "label_count": len(labels) * len(JUDGE_CRITERIA),
        "source_counts": {
            "GPT_GEMINI_AGREEMENT": len(labels) * len(JUDGE_CRITERIA),
            "KIMI_K3_ADJUDICATION": 0,
        },
        "uncertain_label_count": 0,
        "adjudicator_unresolved_count": 0,
        "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "human_gold_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    reference = {
        **reference_commitment,
        "artifact_hash": hash_payload(reference_commitment),
    }
    artifact = build_receipt_quality_calibration(
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    validate_receipt_quality_calibration(
        artifact,
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    assert artifact["criterion_agreement"] == 1.0
    assert artifact["packet_state_accuracy"] == 1.0
    assert artifact["candidate_state"] == "RECEIPT_QUALITY_JUDGE_CALIBRATION_CANDIDATE"
    assert artifact["selection_authority"] is False
    assert artifact["retention_authority"] is False


def test_mixed_k3_bundle_selects_only_exact_panel_and_pack(tmp_path):
    panel_id = "current-panel"
    pack_hash = "a" * 64
    current = {
        "panel_id": panel_id,
        "adjudication_pack_hash": pack_hash,
        "blinding_attestation": {"identity_visible": False},
        "decisions": [{"adjudication_id": "current"}],
    }
    historical = {
        "panel_id": "historical-panel",
        "adjudication_pack_hash": "b" * 64,
        "blinding_attestation": {"identity_visible": False},
        "decisions": [{"adjudication_id": "historical"}],
    }
    bundle = tmp_path / "mixed-k3-responses.zip"
    with ZipFile(bundle, "w") as archive:
        archive.writestr("current.json", json.dumps(current))
        archive.writestr("historical.json", json.dumps(historical))

    selected = FINALIZER._bundle_response(
        bundle, panel_id=panel_id, pack_hash=pack_hash,
    )

    assert selected == current
