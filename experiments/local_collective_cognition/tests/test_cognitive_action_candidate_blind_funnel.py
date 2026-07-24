from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_candidate_blind_funnel import (  # noqa: E402
    FUNNEL_TASK_KIND,
    SOURCE_CLOSURE_HASH,
    STATUS_RELATION_MAP,
    analyze_candidate_blind_funnel_smoke,
    build_candidate_blind_funnel_preregistration,
    run_candidate_blind_funnel_smoke,
    validate_source_status_receipt,
)
from local_collective_cognition.cognitive_action_candidate_blind_funnel_holdout import (  # noqa: E402
    build_candidate_blind_funnel_holdout,
    validate_candidate_blind_funnel_holdout,
)


class FunnelFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-funnel",
            model_id="fixture-model",
            task_kinds=(FUNNEL_TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.source_input_keys = []

    def invoke(self, task):
        item = task.inputs
        if item["stage"] == "SOURCE_STATUS":
            self.source_input_keys.append(set(item))
            text = item["evidence_text"]
            folded = text.casefold()
            if "unavailable" in folded or "catalog is absent" in folded:
                status = "MISSING"
            elif "provides no" in folded or "gives no" in folded:
                status = "UNSPECIFIED"
            elif "while" in folded:
                status = "CONFLICTED"
            else:
                status = "AVAILABLE"
            result = {
                "conflict_id": item["conflict_id"],
                "requested_object_quote": text,
                "source_status_quote": text,
                "definition_source_status": status,
                "status_relation": STATUS_RELATION_MAP[status],
                "support_spans": [text],
                "rationale": "Fixture source-status receipt.",
                "confidence": 0.9,
                "evidence_refs": list(task.allowed_evidence),
            }
        else:
            source = item["validated_source_receipt"]
            compositional = "opens two hours" in source[
                "source_status_quote"
            ]
            result = {
                "conflict_id": item["conflict_id"],
                "candidate_entailment": "CANDIDATE_B",
                "entailment_relation": (
                    "JOINTLY_ENTAILS" if compositional else "DEFINES"
                ),
                "contextual_default": "CANDIDATE_B",
                "derivation_steps": ["Compare the frozen definition."],
                "candidate_option_text_used_as_evidence": False,
                "rationale": "Fixture entailment receipt.",
                "confidence": 0.9,
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


def source_closure():
    return {
        "artifact_hash": SOURCE_CLOSURE_HASH,
        "candidate_state": (
            "RELATIONAL_WITNESS_STRUCTURAL_VALIDATION_FAILED_NO_EXTERNAL_PANEL"
        ),
        "external_panel_generated": False,
        "promotion_allowed": False,
    }


def test_candidate_blind_holdout_covers_all_source_branches():
    corpus = build_candidate_blind_funnel_holdout()
    validate_candidate_blind_funnel_holdout(corpus)
    assert corpus["case_count"] == 8
    assert set(corpus["source_status_counts"].values()) == {2}
    assert corpus["private_provenance"][
        "external_semantic_labels_present"
    ] is False


def test_source_receipt_requires_exact_candidate_blind_grounding():
    corpus = build_candidate_blind_funnel_holdout()
    item = corpus["public_surface"]["items"][0]
    text = item["public_prompt"].split(" Candidates ", 1)[0]
    receipt = {
        "conflict_id": item["conflict_id"],
        "requested_object_quote": text,
        "source_status_quote": text,
        "definition_source_status": "AVAILABLE",
        "status_relation": "DEFINITION_PRESENT",
        "support_spans": [text],
        "rationale": "Fixture.",
        "confidence": 0.9,
        "evidence_refs": corpus["evidence_refs"],
    }
    validate_source_status_receipt(
        receipt,
        item=item,
        evidence_refs=tuple(corpus["evidence_refs"]),
    )
    receipt["source_status_quote"] = "not in evidence"
    with pytest.raises(ValueError, match="source_receipt_invalid"):
        validate_source_status_receipt(
            receipt,
            item=item,
            evidence_refs=tuple(corpus["evidence_refs"]),
        )


def test_candidate_blind_funnel_routes_only_available_sources():
    corpus = build_candidate_blind_funnel_holdout()
    preregistration = build_candidate_blind_funnel_preregistration(
        source_closure=source_closure()
    )
    adapter = FunnelFixtureProvider()
    run = run_candidate_blind_funnel_smoke(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_candidate_blind_funnel_smoke(
        corpus=corpus,
        run=run,
        preregistration=preregistration,
    )
    assert len(run["provider_calls"]) == 10
    assert len(run["outputs"]) == 8
    assert not run["failures"]
    assert all(
        keys == {"stage", "evidence_text", "conflict_id"}
        for keys in adapter.source_input_keys
    )
    assert analysis["source_candidate_blind_rate"] == 1.0
    assert analysis["source_status_construction_match_rate"] == 1.0
    assert analysis["entailment_call_count"] == 2
    assert analysis["structural_smoke_gate"] == "PASS"
    assert analysis["full_fresh_holdout_authorized"] is True
