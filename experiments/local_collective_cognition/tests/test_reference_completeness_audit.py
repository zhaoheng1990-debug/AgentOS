from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.reference_complete_portfolio_holdout import (  # noqa: E402
    build_reference_complete_portfolio_holdout,
)
from local_collective_cognition.reference_completeness_audit import (  # noqa: E402
    _expected_reference,
    run_reference_completeness_audit,
    validate_reference_audit_receipt,
    validate_reference_completeness_audit,
)


class AuditFixture:
    def __init__(self, corpus):
        self.corpus = corpus
        self.profile = ProviderCapabilityProfile(
            provider_id="fixture-reference-audit",
            model_id="fixture",
            task_kinds=(TASK_KIND,),
            max_timeout_seconds=180,
        )

    def invoke(self, task):
        item = task.inputs["public_case"]
        expected = _expected_reference(self.corpus)[item["case_id"]]
        raw = {
            "case_id": item["case_id"],
            "all_focal_relations_assessed": True,
            "relation_assessments": [{
                "relation_id": relation_id,
                "relation_truth_state": state,
                "evidence_span_ids": [
                    item["evidence_spans"][index]["span_id"]
                ],
                "rationale": "Fixture exhaustive relation assessment.",
            } for index, (relation_id, state) in enumerate(
                sorted(expected.items())
            )],
            "evidence_refs": list(task.allowed_evidence),
        }
        return {
            "result": raw,
            "usage": {
                "provider_calls": 1,
                "input_tokens": 10,
                "output_tokens": 10,
            },
            "provenance_refs": list(task.allowed_evidence),
        }


def test_reference_audit_requires_exhaustive_relation_coverage():
    corpus = build_reference_complete_portfolio_holdout()
    item = corpus["public_surface"]["items"][0]
    fixture = AuditFixture(corpus)
    task = type("Task", (), {
        "inputs": {"public_case": item},
        "allowed_evidence": corpus["evidence_refs"],
    })()
    receipt = fixture.invoke(task)["result"]
    assert validate_reference_audit_receipt(
        receipt=receipt, item=item, refs=corpus["evidence_refs"]
    ) == []
    incomplete = {
        **receipt,
        "relation_assessments": receipt["relation_assessments"][:-1],
    }
    assert "REFERENCE_AUDIT_RELATION_COVERAGE_INVALID" in (
        validate_reference_audit_receipt(
            receipt=incomplete,
            item=item,
            refs=corpus["evidence_refs"],
        )
    )


def test_dual_role_fixture_closes_reference_preflight():
    corpus = build_reference_complete_portfolio_holdout()
    audit = run_reference_completeness_audit(
        corpus=corpus, adapter=AuditFixture(corpus)
    )
    validate_reference_completeness_audit(
        audit=audit, corpus=corpus
    )
    assert audit["reference_complete"] is True
    assert audit["valid_receipt_count"] == 16
    assert audit["reference_mismatches"] == []
    assert audit["cross_role_disagreements"] == []
    assert audit["private_reference_available_to_provider"] is False
