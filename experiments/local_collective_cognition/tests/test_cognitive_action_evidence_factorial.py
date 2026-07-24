from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_evidence_factorial import (  # noqa: E402
    FACTORIAL_TASK_KIND,
    LEGACY_SOURCE_PROMPT,
    REPAIRED_SOURCE_PROMPT,
    SOURCE_EVALUATION_HASH,
    SOURCE_REFERENCE_HASH,
    analyze_factorial_run,
    build_factorial_preregistration,
    run_factorial,
)
from local_collective_cognition.cognitive_action_evidence_factorial_holdout import (  # noqa: E402
    build_factorial_holdout,
    validate_factorial_holdout,
)
from local_collective_cognition.cognitive_action_evidence_gate_policies import (  # noqa: E402
    LEGACY_GATE,
    REPAIRED_GATE,
    apply_gate_policy,
)
from local_collective_cognition.cognitive_action_evidence_holdout import (  # noqa: E402
    build_evidence_holdout,
)


class FactorialFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-evidence-factorial",
            model_id="fixture-model",
            task_kinds=(FACTORIAL_TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.objectives = {}

    def invoke(self, task):
        conflict_id = task.inputs["public_object"]["conflict_id"]
        policy = task.inputs["source_prompt_policy"]
        self.objectives[policy] = task.objective
        refs = list(task.allowed_evidence)
        return {
            "result": {
                "conflict_id": conflict_id,
                "selected_object": "NONE",
                "definition_source": "UNDERSPECIFIED_SURFACE",
                "pragmatic_preference": "UNCERTAIN",
                "assessment_process_state": "INCOMPLETE",
                "support_quote": "The term is not operationally defined.",
                "rationale": "Multiple candidate meanings remain open.",
                "confidence": 0.8,
                "evidence_refs": refs,
            },
            "usage": {
                "provider_calls": 1,
                "input_tokens": 10,
                "output_tokens": 2,
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
            "EVIDENCE_CALIBRATOR_EXTERNAL_EVALUATION_COMPLETE_NO_PROMOTION"
        ),
    }


def soft_receipt():
    return {
        "conflict_id": "x",
        "selected_object": "NONE",
        "definition_source": "UNDERSPECIFIED_SURFACE",
        "pragmatic_preference": "UNCERTAIN",
        "assessment_process_state": "INCOMPLETE",
        "support_quote": "The term is not operationally defined.",
        "rationale": "Multiple meanings remain open.",
        "confidence": 0.8,
        "evidence_refs": ["corpus://x"],
    }


def test_factorial_holdout_is_new_cross_balanced_and_unlabeled():
    corpus = build_factorial_holdout()
    validate_factorial_holdout(corpus)
    old = build_evidence_holdout()
    assert corpus["case_count"] == 24
    assert set(corpus["family_counts"].values()) == {4}
    assert set(corpus["design_stratum_counts"].values()) == {6}
    assert corpus["artifact_hash"] != old["artifact_hash"]
    assert {
        item["public_prompt"] for item in corpus["public_surface"]["items"]
    }.isdisjoint({
        item["public_prompt"] for item in old["public_surface"]["items"]
    })
    assert corpus["v0_19_labels_available_during_inference"] is False


def test_repaired_gate_preserves_receipt_and_normalizes_open_state():
    receipt = soft_receipt()
    with pytest.raises(ValueError, match="selective_evidence_basis_incoherent"):
        apply_gate_policy(
            LEGACY_GATE,
            receipt,
            conflict_id="x",
            evidence_refs=("corpus://x",),
        )
    repaired = apply_gate_policy(
        REPAIRED_GATE,
        receipt,
        conflict_id="x",
        evidence_refs=("corpus://x",),
    )
    assert receipt["pragmatic_preference"] == "UNCERTAIN"
    assert receipt["assessment_process_state"] == "INCOMPLETE"
    assert repaired["payload"]["pragmatic_preference"] == "NONE"
    assert repaired["payload"]["assessment_process_state"] == "COMPLETE"
    assert repaired["gate_transforms"] == [
        "UNSUPPORTED_PREFERENCE_TO_NONE",
        "RECOGNIZED_OPEN_STATE_TO_COMPLETE_ASSESSMENT",
    ]


def test_repaired_gate_remains_fail_closed_for_decisive_source_without_object():
    receipt = {
        **soft_receipt(),
        "definition_source": "EXPLICIT_REQUEST_DEFINITION",
    }
    with pytest.raises(ValueError, match="decisive_source_without_selection"):
        apply_gate_policy(
            REPAIRED_GATE,
            receipt,
            conflict_id="x",
            evidence_refs=("corpus://x",),
        )


def test_factorial_reuses_each_provider_receipt_across_two_gate_cells():
    corpus = build_factorial_holdout()
    prereg = build_factorial_preregistration(
        source_evaluation=source_evaluation()
    )
    adapter = FactorialFixtureProvider()
    run = run_factorial(
        corpus=corpus,
        preregistration=prereg,
        adapter=adapter,
    )
    analysis = analyze_factorial_run(corpus=corpus, run=run)
    assert len(run["source_calls"]) == 48
    assert len(run["outputs"]) == 48
    assert analysis["cell_coverage"] == {
        "LEGACY_SOURCE_LEGACY_GATE": 0.0,
        "REPAIRED_SOURCE_LEGACY_GATE": 0.0,
        "LEGACY_SOURCE_REPAIRED_GATE": 1.0,
        "REPAIRED_SOURCE_REPAIRED_GATE": 1.0,
    }
    assert run["provider_calls_shared_across_gate_cells"] is True
    assert "must never count as an explicit definition" in adapter.objectives[
        REPAIRED_SOURCE_PROMPT
    ]
    assert "must never count as an explicit definition" not in adapter.objectives[
        LEGACY_SOURCE_PROMPT
    ]
