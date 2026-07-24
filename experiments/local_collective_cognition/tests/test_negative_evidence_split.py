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
    "negative_evidence_finalizer",
    PACK / "examples" / "finalize_negative_evidence_calibration.py",
)
FINALIZER = importlib.util.module_from_spec(FINALIZER_SPEC)
FINALIZER_SPEC.loader.exec_module(FINALIZER)

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_calibration import (  # noqa: E402
    build_negative_evidence_calibration,
    validate_negative_evidence_calibration,
)
from local_collective_cognition.negative_evidence_candidate_runtime import (  # noqa: E402
    NegativeEvidenceCandidateRuntime,
    validate_negative_evidence_candidate_run,
)
from local_collective_cognition.negative_evidence_holdout import (  # noqa: E402
    CASES,
    CONSTRUCTION_TARGETS,
    build_negative_evidence_corpus_artifact,
    validate_negative_evidence_corpus_artifact,
    validate_negative_evidence_corpus_spec,
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
    def __init__(self, lane, *, absent_ids=(), veto_ids=()):
        task_kind = JUDGE_TASK_KIND if lane == "BASELINE" else TASK_KINDS[lane]
        self.lane = lane
        self.absent_ids = set(absent_ids)
        self.veto_ids = set(veto_ids)
        self.profile = ProviderCapabilityProfile(
            provider_id=f"fixture-{lane.lower()}",
            model_id="fixture-model",
            task_kinds=(task_kind,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        assessments = []
        for candidate in task.inputs["blind_candidates"]:
            blind_id = candidate["blind_candidate_id"]
            if self.lane == "BASELINE":
                criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
                if blind_id in self.absent_ids:
                    criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "criteria": criteria,
                    "confidence": 0.8,
                    "audit_note": "Fixture baseline assessment.",
                    "fatal_issue": "",
                })
            else:
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "state": "VETO" if blind_id in self.veto_ids else "PASS",
                    "evidence_basis": "Fixture evidence basis.",
                    "counterfactual": "Fixture counterfactual wording.",
                    "confidence": 0.8,
                })
        result = {
            "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
            "assessments": assessments,
            "evidence_refs": list(task.allowed_evidence),
        }
        if self.lane != "BASELINE":
            result["audit_kind"] = self.lane
        return {
            "result": result,
            "usage": {"input_tokens": 25, "output_tokens": 15},
            "provenance_refs": list(task.allowed_evidence),
        }


def _candidate_ids(corpus):
    return [
        item["blind_candidate_id"]
        for batch in corpus["blind_surface"]["batches"]
        for item in batch["public_candidates"]
    ]


def _run(corpus):
    blind_ids = _candidate_ids(corpus)
    return NegativeEvidenceCandidateRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="fixture-negative-evidence",
        baseline_adapter=FixtureAdapter("BASELINE", absent_ids={blind_ids[2]}),
        live_adapter=FixtureAdapter(
            LIVE_AMBIGUITY_AUDIT, veto_ids={blind_ids[0]},
        ),
        fabrication_adapter=FixtureAdapter(
            FABRICATION_AUDIT, veto_ids={blind_ids[1]},
        ),
    )


def _reference(corpus, nonusable_ids):
    labels = []
    for blind_id in sorted(corpus["blind_surface"]["bindings"]):
        criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
        if blind_id in nonusable_ids:
            criteria[JUDGE_CRITERIA[0]] = "ABSENT"
        labels.append({"blind_candidate_id": blind_id, "criteria": criteria})
    commitment = {
        "labels": labels,
        "candidate_state": "MODEL_PANEL_REFERENCE_CANDIDATE",
        "ground_truth_claim": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def test_holdout_is_fresh_balanced_and_candidate_only():
    validate_negative_evidence_corpus_spec()
    corpus = build_negative_evidence_corpus_artifact()
    validate_negative_evidence_corpus_artifact(corpus)
    assert len(CASES) == 18
    assert all(
        sum(case.construction_target == target for case in CASES) == 6
        for target in CONSTRUCTION_TARGETS
    )
    assert corpus["report"]["ground_truth_claim"] is False
    assert corpus["corpus_spec"]["construction_targets_are_ground_truth"] is False


def test_panel_packs_support_per_candidate_prompts_without_private_targets():
    corpus = build_negative_evidence_corpus_artifact()
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=corpus,
    )
    public = json.dumps(packs, sort_keys=True)
    assert "construction_target" not in public
    assert "FALSE_AMBIGUITY_CONTROL" not in public
    assert all(len(pack["items"]) == 18 for pack in packs)
    assert all(item["public_prompt"] for pack in packs for item in pack["items"])


def test_specialist_fusion_can_downgrade_but_never_promote_baseline():
    corpus = build_negative_evidence_corpus_artifact()
    run = _run(corpus)
    validate_negative_evidence_candidate_run(run, corpus_artifact=corpus)
    blind_ids = _candidate_ids(corpus)
    records = {
        item["blind_candidate_id"]: item for item in run["fusion"]["records"]
    }
    assert records[blind_ids[0]]["baseline_packet_state"] == "USABLE"
    assert records[blind_ids[0]]["fused_packet_state"] == "UNUSABLE"
    assert records[blind_ids[1]]["fused_packet_state"] == "UNUSABLE"
    assert records[blind_ids[2]]["baseline_packet_state"] == "UNUSABLE"
    assert records[blind_ids[2]]["fused_packet_state"] == "UNUSABLE"
    assert all(
        not (
            item["baseline_packet_state"] != "USABLE"
            and item["fused_packet_state"] == "USABLE"
        )
        for item in records.values()
    )
    assert len({
        binding["context_scope"] for binding in run["role_bindings"].values()
    }) == 3


def test_fusion_tamper_fails_even_after_outer_hash_is_recomputed():
    corpus = build_negative_evidence_corpus_artifact()
    run = _run(corpus)
    tampered = deepcopy(run)
    tampered["fusion"]["records"][0]["fused_packet_state"] = "USABLE"
    tampered["candidate_run_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "candidate_run_hash"
    })
    with pytest.raises(ValueError, match="fusion_semantics_invalid"):
        validate_negative_evidence_candidate_run(tampered, corpus_artifact=corpus)


def test_invalid_specialist_payload_fails_after_receipts_are_rehashed():
    corpus = build_negative_evidence_corpus_artifact()
    run = _run(corpus)
    tampered = deepcopy(run)
    item = tampered["lanes"][LIVE_AMBIGUITY_AUDIT]["judgments"][0]
    item["payload"]["assessments"][0]["state"] = "INVALID"
    item["receipt"]["payload_hash"] = hash_payload(item["payload"])
    item["receipt"]["receipt_hash"] = hash_payload({
        key: value for key, value in item["receipt"].items() if key != "receipt_hash"
    })
    tampered["candidate_run_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "candidate_run_hash"
    })
    with pytest.raises(ValueError, match="audit_state_invalid"):
        validate_negative_evidence_candidate_run(tampered, corpus_artifact=corpus)


def test_frozen_calibration_rewards_false_usable_reduction_without_recall_harm():
    corpus = build_negative_evidence_corpus_artifact()
    run = _run(corpus)
    blind_ids = _candidate_ids(corpus)
    reference = _reference(corpus, set(blind_ids[:3]))
    calibration = build_negative_evidence_calibration(
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    validate_negative_evidence_calibration(
        calibration,
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    assert calibration["baseline_false_usable_rate"] == pytest.approx(2 / 3)
    assert calibration["fused_false_usable_rate"] == 0
    assert calibration["fused_usable_recall"] == 1
    assert calibration["provider_call_multiplier"] == 3
    assert calibration["candidate_state"] == (
        "NEGATIVE_EVIDENCE_SPLIT_CALIBRATION_CANDIDATE"
    )
    assert calibration["selection_authority"] is False


def test_negative_evidence_finalizer_selects_exact_current_k3_response(tmp_path):
    current = {
        "panel_id": "current-panel",
        "adjudication_pack_hash": "a" * 64,
        "blinding_attestation": {"pack_only_context": True},
        "decisions": [{"adjudication_id": "current"}],
    }
    old = {
        "panel_id": "old-panel",
        "adjudication_pack_hash": "b" * 64,
        "blinding_attestation": {"pack_only_context": True},
        "decisions": [{"adjudication_id": "old"}],
    }
    bundle = tmp_path / "mixed-k3.zip"
    with ZipFile(bundle, "w") as archive:
        archive.writestr("current.json", json.dumps(current))
        archive.writestr("old.json", json.dumps(old))
    assert FINALIZER._bundle_response(
        bundle, panel_id="current-panel", pack_hash="a" * 64,
    ) == current
