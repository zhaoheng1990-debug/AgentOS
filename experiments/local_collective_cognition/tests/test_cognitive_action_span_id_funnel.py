from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.cognitive_action_span_id_funnel import (  # noqa: E402
    FUNNEL_TASK_KIND,
    SOURCE_CLOSURE_HASH,
    STATUS_RELATION_MAP,
    analyze_span_id_funnel_smoke,
    build_evidence_span_pack,
    build_span_id_funnel_preregistration,
    run_span_id_funnel_smoke,
    validate_evidence_span_pack,
    validate_source_status_receipt,
)
from local_collective_cognition.cognitive_action_span_id_funnel_holdout import (  # noqa: E402
    build_span_id_funnel_holdout,
    validate_span_id_funnel_holdout,
)


class SpanIdFixtureProvider:
    def __init__(self):
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-span-id-funnel",
            model_id="fixture-model",
            task_kinds=(FUNNEL_TASK_KIND,),
            max_timeout_seconds=180,
        )
        self.source_input_keys = []

    def invoke(self, task):
        item = task.inputs
        if item["stage"] == "SOURCE_STATUS":
            self.source_input_keys.append(set(item))
            spans = item["evidence_span_pack"]["spans"]
            text = " ".join(span["text"] for span in spans)
            folded = text.casefold()
            if "unavailable" in folded or "is absent" in folded:
                status = "MISSING"
            elif "supplies no" in folded or "provides no" in folded:
                status = "UNSPECIFIED"
            elif "appendix" in folded or "addendum" in folded:
                status = "CONFLICTED"
            else:
                status = "AVAILABLE"
            source_ids = [span["span_id"] for span in spans]
            result = {
                "conflict_id": item["conflict_id"],
                "requested_object_span_ids": [source_ids[0]],
                "source_status_span_ids": source_ids,
                "definition_source_status": status,
                "status_relation": STATUS_RELATION_MAP[status],
                "rationale": "Fixture source-status receipt.",
                "confidence": 0.9,
                "evidence_refs": list(task.allowed_evidence),
            }
        else:
            spans = item["selected_evidence_spans"]
            compositional = any(
                "Begin observation" in span["text"] for span in spans
            )
            result = {
                "conflict_id": item["conflict_id"],
                "candidate_entailment": "CANDIDATE_B",
                "entailment_relation": (
                    "JOINTLY_ENTAILS" if compositional else "DEFINES"
                ),
                "evidence_span_ids": [span["span_id"] for span in spans],
                "contextual_default": "CANDIDATE_B",
                "derivation_steps": ["Compare the admitted immutable spans."],
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
        "candidate_state": "CANDIDATE_BLIND_FUNNEL_SMOKE_REJECTED_STOP",
        "external_panel_generated": False,
        "promotion_allowed": False,
    }


def test_span_id_holdout_covers_all_source_branches():
    corpus = build_span_id_funnel_holdout()
    validate_span_id_funnel_holdout(corpus)
    assert corpus["case_count"] == 8
    assert set(corpus["source_status_counts"].values()) == {2}
    assert corpus["private_provenance"][
        "external_semantic_labels_present"
    ] is False


def test_runtime_span_ids_and_hashes_are_deterministic_and_candidate_blind():
    corpus = build_span_id_funnel_holdout()
    conflict_items = [
        item for item in corpus["public_surface"]["items"]
        if corpus["private_provenance"]["bindings"][
            item["conflict_id"]
        ]["source_status"] == "CONFLICTED"
    ]
    for item in corpus["public_surface"]["items"]:
        first = build_evidence_span_pack(item)
        second = build_evidence_span_pack(item)
        assert first == second
        validate_evidence_span_pack(first, item=item)
        assert set(first) == {
            "span_pack_version",
            "conflict_id",
            "source_text_hash",
            "spans",
            "span_pack_hash",
        }
        assert all(
            set(span) == {"span_id", "text", "text_hash"}
            for span in first["spans"]
        )
    assert all(
        len(build_evidence_span_pack(item)["spans"]) >= 2
        for item in conflict_items
    )


def test_source_receipt_rejects_unknown_ids_and_single_span_conflict():
    corpus = build_span_id_funnel_holdout()
    item = next(
        item for item in corpus["public_surface"]["items"]
        if corpus["private_provenance"]["bindings"][
            item["conflict_id"]
        ]["source_status"] == "CONFLICTED"
    )
    pack = build_evidence_span_pack(item)
    span_ids = [span["span_id"] for span in pack["spans"]]
    receipt = {
        "conflict_id": item["conflict_id"],
        "requested_object_span_ids": [span_ids[0]],
        "source_status_span_ids": span_ids,
        "definition_source_status": "CONFLICTED",
        "status_relation": "CONFLICTING_DEFINITIONS",
        "rationale": "Fixture.",
        "confidence": 0.9,
        "evidence_refs": corpus["evidence_refs"],
    }
    validate_source_status_receipt(
        receipt,
        item=item,
        span_pack=pack,
        evidence_refs=tuple(corpus["evidence_refs"]),
    )
    receipt["source_status_span_ids"] = [span_ids[0]]
    with pytest.raises(ValueError, match="source_receipt_invalid"):
        validate_source_status_receipt(
            receipt,
            item=item,
            span_pack=pack,
            evidence_refs=tuple(corpus["evidence_refs"]),
        )
    receipt["source_status_span_ids"] = ["S99-outside"]
    with pytest.raises(ValueError, match="source_receipt_invalid"):
        validate_source_status_receipt(
            receipt,
            item=item,
            span_pack=pack,
            evidence_refs=tuple(corpus["evidence_refs"]),
        )


def test_span_id_funnel_routes_only_available_sources():
    corpus = build_span_id_funnel_holdout()
    preregistration = build_span_id_funnel_preregistration(
        source_closure=source_closure()
    )
    adapter = SpanIdFixtureProvider()
    run = run_span_id_funnel_smoke(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_span_id_funnel_smoke(
        corpus=corpus,
        run=run,
        preregistration=preregistration,
    )
    assert len(run["provider_calls"]) == 10
    assert len(run["outputs"]) == 8
    assert not run["failures"]
    assert all(
        keys == {"stage", "evidence_span_pack", "conflict_id"}
        for keys in adapter.source_input_keys
    )
    assert analysis["span_pack_validation_rate"] == 1.0
    assert analysis["source_candidate_blind_rate"] == 1.0
    assert analysis["source_status_construction_match_rate"] == 1.0
    assert analysis["false_available_promotion_count"] == 0
    assert analysis["entailment_call_count"] == 2
    assert analysis["no_new_span_id_rate"] == 1.0
    assert analysis["structural_smoke_gate"] == "PASS"
    assert analysis["full_fresh_holdout_authorized"] is True
