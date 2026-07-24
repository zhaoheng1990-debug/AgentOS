from copy import deepcopy
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.bounded_retry_provider import (  # noqa: E402
    BoundedRetryProviderAdapter,
)
from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_generalization_calibration import (  # noqa: E402
    build_generalization_calibration,
    validate_generalization_calibration,
)
from local_collective_cognition.negative_evidence_generalization_fusion import (  # noqa: E402
    BASELINE,
    HETEROGENEOUS_LIVE,
    LANES,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    SAME_MODEL_LIVE,
    SHARED_FABRICATION,
)
from local_collective_cognition.negative_evidence_generalization_holdout import (  # noqa: E402
    CASES,
    CATEGORIES,
    SURFACE_STYLES,
    build_generalization_corpus_artifact,
    validate_generalization_corpus_artifact,
    validate_generalization_corpus_spec,
)
from local_collective_cognition.negative_evidence_generalization_runtime import (  # noqa: E402
    NegativeEvidenceGeneralizationRuntime,
    validate_generalization_candidate_run,
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
        self.lane = lane
        self.absent_ids = set(absent_ids)
        self.veto_ids = set(veto_ids)
        task_kind = (
            JUDGE_TASK_KIND
            if lane in (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3)
            else TASK_KINDS[
                LIVE_AMBIGUITY_AUDIT
                if lane in (SAME_MODEL_LIVE, HETEROGENEOUS_LIVE)
                else FABRICATION_AUDIT
            ]
        )
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
            if self.lane in (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3):
                criteria = {criterion: "PRESENT" for criterion in JUDGE_CRITERIA}
                if blind_id in self.absent_ids:
                    criteria[JUDGE_CRITERIA[0]] = "ABSENT"
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "criteria": criteria,
                    "confidence": 0.8,
                    "audit_note": "Fixture monolithic assessment.",
                    "fatal_issue": "",
                })
            else:
                assessments.append({
                    "blind_candidate_id": blind_id,
                    "state": "VETO" if blind_id in self.veto_ids else "PASS",
                    "evidence_basis": "Fixture evidence basis.",
                    "counterfactual": "Fixture counterfactual.",
                    "confidence": 0.8,
                })
        result = {
            "batch_id": task.expected_schema["properties"]["batch_id"]["enum"][0],
            "assessments": assessments,
            "evidence_refs": list(task.allowed_evidence),
        }
        if self.lane not in (BASELINE, MONOLITHIC_REPEAT_2, MONOLITHIC_REPEAT_3):
            result["audit_kind"] = (
                LIVE_AMBIGUITY_AUDIT
                if self.lane in (SAME_MODEL_LIVE, HETEROGENEOUS_LIVE)
                else FABRICATION_AUDIT
            )
        return {
            "result": result,
            "usage": {"input_tokens": 30, "output_tokens": 20},
            "provenance_refs": list(task.allowed_evidence),
        }


def _ids(corpus):
    return [
        item["blind_candidate_id"]
        for batch in corpus["blind_surface"]["batches"]
        for item in batch["public_candidates"]
    ]


def _run(corpus):
    blind_ids = _ids(corpus)
    adapters = {
        BASELINE: FixtureAdapter(BASELINE, absent_ids={blind_ids[3]}),
        MONOLITHIC_REPEAT_2: FixtureAdapter(
            MONOLITHIC_REPEAT_2, absent_ids={blind_ids[3]},
        ),
        MONOLITHIC_REPEAT_3: FixtureAdapter(
            MONOLITHIC_REPEAT_3, absent_ids={blind_ids[3]},
        ),
        SAME_MODEL_LIVE: FixtureAdapter(
            SAME_MODEL_LIVE, veto_ids=set(blind_ids[:2]),
        ),
        SHARED_FABRICATION: FixtureAdapter(
            SHARED_FABRICATION, veto_ids={blind_ids[2]},
        ),
        HETEROGENEOUS_LIVE: FixtureAdapter(
            HETEROGENEOUS_LIVE, veto_ids={blind_ids[0]},
        ),
    }
    return NegativeEvidenceGeneralizationRuntime(
        corpus_artifact=corpus,
    ).evaluate(experiment_id="fixture-generalization", adapters=adapters)


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


def test_generalization_corpus_is_fresh_balanced_and_surface_shifted():
    validate_generalization_corpus_spec()
    corpus = build_generalization_corpus_artifact()
    validate_generalization_corpus_artifact(corpus)
    assert len(CASES) == 24
    assert all(
        sum(case.construction_category == category for case in CASES) == 4
        for category in CATEGORIES
    )
    assert all(
        sum(case.surface_style == style for case in CASES) == 6
        for style in SURFACE_STYLES
    )
    assert corpus["corpus_spec"]["construction_categories_are_ground_truth"] is False


def test_generalization_panel_is_blind_and_complete():
    corpus = build_generalization_corpus_artifact()
    packs, manifest = build_reference_panel(semantic_artifact=corpus)
    validate_reference_panel(
        packs=packs, manifest=manifest, semantic_artifact=corpus,
    )
    public = json.dumps(packs, sort_keys=True)
    assert "construction_category" not in public
    assert "ADVERSARIAL_CLEAN" not in public
    assert all(len(pack["items"]) == 24 for pack in packs)


def test_four_arms_are_budget_bound_and_split_cannot_promote():
    corpus = build_generalization_corpus_artifact()
    run = _run(corpus)
    validate_generalization_candidate_run(run, corpus_artifact=corpus)
    accounting = run["fusion"]["arm_accounting"]
    assert accounting["SINGLE_MONOLITHIC"]["attributed_provider_calls"] == 12
    assert accounting["BUDGET_MATCHED_MONOLITHIC"]["attributed_provider_calls"] == 36
    assert accounting["SAME_MODEL_SPLIT"]["attributed_provider_calls"] == 36
    assert accounting["HETEROGENEOUS_SPLIT"]["attributed_provider_calls"] == 36
    assert all(
        not (
            item["single_monolithic_state"] != "USABLE"
            and item["same_model_split_state"] == "USABLE"
        )
        for item in run["fusion"]["records"]
    )


def test_role_structure_gain_is_scored_against_budget_matched_monolithic():
    corpus = build_generalization_corpus_artifact()
    run = _run(corpus)
    blind_ids = _ids(corpus)
    reference = _reference(corpus, set(blind_ids[:4]))
    calibration = build_generalization_calibration(
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    validate_generalization_calibration(
        calibration,
        corpus_artifact=corpus,
        candidate_run=run,
        reference_artifact=reference,
    )
    budget = calibration["arm_metrics"]["BUDGET_MATCHED_MONOLITHIC"]
    same = calibration["arm_metrics"]["SAME_MODEL_SPLIT"]
    assert budget["false_usable_rate"] == 0.75
    assert same["false_usable_rate"] == 0
    assert same["packet_accuracy"] - budget["packet_accuracy"] >= 0.10
    assert calibration["candidate_state"] == "ROLE_STRUCTURE_GENERALIZATION_CANDIDATE"
    assert calibration["selection_authority"] is False


def test_generalization_fusion_tamper_fails_after_outer_rehash():
    corpus = build_generalization_corpus_artifact()
    run = _run(corpus)
    tampered = deepcopy(run)
    tampered["fusion"]["records"][0]["same_model_split_state"] = "USABLE"
    tampered["candidate_run_hash"] = hash_payload({
        key: value for key, value in tampered.items() if key != "candidate_run_hash"
    })
    with pytest.raises(ValueError, match="fusion_invalid"):
        validate_generalization_candidate_run(tampered, corpus_artifact=corpus)


def test_bounded_transport_retry_accounts_for_failed_attempt():
    class FlakyAdapter:
        def __init__(self):
            self.profile = object()
            self.calls = 0

        def invoke(self, task):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError("fixture timeout")
            return {
                "result": {"ok": True},
                "usage": {"input_tokens": 4, "output_tokens": 2},
                "provenance_refs": [],
            }

    adapter = BoundedRetryProviderAdapter(
        FlakyAdapter(), max_attempts=2, delay_seconds=0,
    )
    result = adapter.invoke(None)
    assert result["usage"]["provider_calls"] == 2
