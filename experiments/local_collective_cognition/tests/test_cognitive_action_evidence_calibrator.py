from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_calibrator import (  # noqa: E402
    EVIDENCE_TASK_KIND,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_evidence_run,
    build_evidence_preregistration,
    normalize_source_receipt,
    run_evidence_arms,
)
from local_collective_cognition.cognitive_action_evidence_holdout import build_evidence_holdout, validate_evidence_holdout  # noqa: E402


class FixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-evidence",
            model_id="fixture-model",
            task_kinds=(EVIDENCE_TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        conflict_id = task.inputs["public_object"]["conflict_id"]
        refs = list(task.allowed_evidence)
        if task.inputs["arm"] == "CONTRASTIVE_SOURCE_CALIBRATOR":
            result = {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "definition_source": "UNDERSPECIFIED_SURFACE",
                "pragmatic_preference": "NONE",
                "assessment_process_state": "COMPLETE",
                "support_quote": "The request gives no definition.",
                "rationale": "Neither candidate is semantically fixed.",
                "confidence": 0.8,
                "evidence_refs": refs,
            }
        else:
            result = {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "selection_basis": "NO_PREFERENCE",
                "pragmatic_preference": "NONE",
                "evidence_state": "SOFT_AMBIGUITY",
                "assessment_process_state": "COMPLETE",
                "action": "CLARIFY",
                "rationale": "Neither candidate is semantically fixed.",
                "confidence": 0.8,
                "evidence_refs": refs,
            }
        return {
            "result": result,
            "usage": {"provider_calls": 1, "input_tokens": 10, "output_tokens": 2, "latency_ms": 1},
            "provenance_refs": refs,
        }


def source_evaluation():
    return {
        "artifact_hash": SOURCE_EVALUATION_HASH,
        "reference_hash": SOURCE_REFERENCE_HASH,
        "anti_additive_gate": "REJECT",
        "candidate_state": "SELECTIVE_ESCALATION_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION",
    }


def test_evidence_holdout_is_fresh_cross_balanced_and_unlabeled():
    corpus = build_evidence_holdout()
    validate_evidence_holdout(corpus)
    assert corpus["case_count"] == 24
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {6}
    assert corpus["calibration_labels_reused_as_validation"] is False
    assert "design_stratum" not in str(corpus["public_surface"])


def test_contrastive_source_is_mechanically_mapped_and_arms_freeze():
    corpus = build_evidence_holdout()
    prereg = build_evidence_preregistration(source_evaluation=source_evaluation())
    run = run_evidence_arms(
        corpus=corpus,
        preregistration=prereg,
        adapter=FixtureProvider(),
    )
    analysis = analyze_evidence_run(corpus=corpus, run=run)
    assert len(run["outputs"]) == 48
    assert not run["failures"]
    assert analysis["coverage"] == {
        "FREE_LABEL_CONTROL": 1.0,
        "CONTRASTIVE_SOURCE_CALIBRATOR": 1.0,
    }
    assert analysis["definition_source_distribution"] == {
        "UNDERSPECIFIED_SURFACE": 24
    }


def test_candidate_option_text_cannot_bypass_source_coherence():
    receipt = {
        "conflict_id": "x",
        "selected_object": "CANDIDATE_A",
        "definition_source": "UNDERSPECIFIED_SURFACE",
        "pragmatic_preference": "CANDIDATE_A",
        "assessment_process_state": "COMPLETE",
        "support_quote": "Candidate A appears in the options.",
        "rationale": "Invalid fixture.",
        "confidence": 0.5,
        "evidence_refs": ["corpus://x"],
    }
    try:
        normalize_source_receipt(receipt, conflict_id="x", evidence_refs=("corpus://x",))
    except ValueError as exc:
        assert str(exc) == "evidence_soft_source_selected_object"
    else:
        raise AssertionError("expected source coherence rejection")
