from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_first_holdout import (  # noqa: E402
    build_evidence_first_holdout,
)
from local_collective_cognition.cognitive_action_relational_witness import (  # noqa: E402
    RELATIONAL_WITNESS_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_relational_witness_run,
    build_relational_witness_preregistration,
    run_relational_witness_selective,
    synthesize_relational_tuple,
    validate_relational_witness,
)
from local_collective_cognition.cognitive_action_relational_witness_holdout import (  # noqa: E402
    build_relational_witness_holdout,
    evidence_text,
    validate_relational_witness_holdout,
)


class RelationalFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-relational",
            model_id="fixture-model",
            task_kinds=(RELATIONAL_WITNESS_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs
        if item["stage"] == "BASELINE_SOURCE":
            conflict_id = item["public_object"]["conflict_id"]
            prompt = item["public_object"]["public_prompt"].casefold()
            missing = any(
                marker in prompt for marker in (
                    "unavailable", "registry is absent", "catalog is missing",
                    "cannot be found",
                )
            )
            open_surface = any(
                marker in prompt for marker in (
                    "no activity threshold", "without defining intent",
                    "without an as-of convention", "no size variable",
                )
            )
            result = {
                "conflict_id": conflict_id,
                "selected_object": (
                    "NONE" if missing or open_surface else "CANDIDATE_A"
                ),
                "definition_source": (
                    "MISSING_EXTERNAL_SPECIFICATION"
                    if missing
                    else "UNDERSPECIFIED_SURFACE"
                    if open_surface
                    else "EXPLICIT_REQUEST_DEFINITION"
                ),
                "pragmatic_preference": (
                    "NONE" if missing or open_surface else "CANDIDATE_A"
                ),
                "assessment_process_state": "COMPLETE",
                "support_quote": "Fixture.",
                "rationale": "Fixture baseline.",
                "confidence": 0.8,
                "evidence_refs": list(task.allowed_evidence),
            }
        else:
            text = item["evidence_text"]
            result = {
                "conflict_id": item["conflict_id"],
                "requested_object_quote": text,
                "source_status_quote": text,
                "definition_source_status": "AVAILABLE",
                "support_relation": "DEFINES",
                "support_spans": [text],
                "derivation_steps": [],
                "candidate_entailment": "CANDIDATE_A",
                "contextual_default": "CANDIDATE_A",
                "anti_entailment_reason": "NOT_APPLICABLE",
                "candidate_option_text_used_as_evidence": False,
                "rationale": "Fixture relational witness.",
                "confidence": 0.8,
                "evidence_refs": list(task.allowed_evidence),
            }
        return {
            "result": result,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 10,
                "output_tokens": 2,
                "latency_ms": 1,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": (
            "EVIDENCE_FIRST_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }


def missing_witness(item, refs):
    text = evidence_text(item)
    return {
        "conflict_id": item["conflict_id"],
        "requested_object_quote": text,
        "source_status_quote": text,
        "definition_source_status": "MISSING",
        "support_relation": "INDICATES_ABSENCE",
        "support_spans": [text],
        "derivation_steps": [],
        "candidate_entailment": "NONE",
        "contextual_default": "NONE",
        "anti_entailment_reason": (
            "The named source is unavailable, so neither candidate follows."
        ),
        "candidate_option_text_used_as_evidence": False,
        "rationale": "The source absence blocks candidate entailment.",
        "confidence": 0.9,
        "evidence_refs": list(refs),
    }


def test_relational_holdout_is_fresh_balanced_and_unlabeled():
    corpus = build_relational_witness_holdout()
    validate_relational_witness_holdout(corpus)
    previous = build_evidence_first_holdout()
    assert corpus["case_count"] == 16
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {4}
    assert {
        item["public_prompt"] for item in corpus["public_surface"]["items"]
    }.isdisjoint({
        item["public_prompt"] for item in previous["public_surface"]["items"]
    })
    assert corpus["v0_22_reference_available_during_inference"] is False


def test_missing_source_forces_anti_entailment_and_opaque_tuple():
    corpus = build_relational_witness_holdout()
    item = next(
        item for item in corpus["public_surface"]["items"]
        if "UG-42" in item["public_prompt"]
    )
    refs = tuple(corpus["evidence_refs"])
    witness = missing_witness(item, refs)
    validate_relational_witness(witness, item=item, evidence_refs=refs)
    result = synthesize_relational_tuple(
        witness,
        conflict_id=item["conflict_id"],
        evidence_refs=refs,
    )
    assert result["payload"]["selected_object"] == "NONE"
    assert result["payload"]["evidence_state"] == "OPAQUE_REFERENCE"
    assert result["payload"]["assessment_process_state"] == "COMPLETE"
    witness["candidate_entailment"] = "CANDIDATE_A"
    with pytest.raises(ValueError, match="missing_mismatch"):
        validate_relational_witness(witness, item=item, evidence_refs=refs)


def test_relational_runtime_uses_one_challenge_call_and_preserves_coverage():
    corpus = build_relational_witness_holdout()
    preregistration = build_relational_witness_preregistration(
        source_evaluation=source_evaluation()
    )
    run = run_relational_witness_selective(
        corpus=corpus,
        preregistration=preregistration,
        adapter=RelationalFixtureProvider(),
    )
    analysis = analyze_relational_witness_run(corpus=corpus, run=run)
    assert len(run["challenge_plan"]["admitted_conflict_ids"]) == 6
    assert len(run["provider_calls"]) == 22
    assert len(run["outputs"]) == 32
    assert not run["failures"]
    assert analysis["cell_coverage"] == {
        "BASELINE_LEGACY_SOURCE_REPAIRED_GATE": 1.0,
        "RELATIONAL_WITNESS_RUNTIME_SYNTHESIS": 1.0,
    }
    assert analysis["relational_witness_validation_rate"] == 1.0
