from local_collective_cognition.factorized_benchmarks.claim_scope_receipt import (
    validate_claim_scope,
)
from local_collective_cognition.factorized_benchmarks.evidence_set_receipt import (
    validate_evidence_set,
)
from local_collective_cognition.factorized_benchmarks.kernel_scope_utility import (
    compile_evidence_scope_candidate,
)
from local_collective_cognition.factorized_benchmarks.scifact_v0_88_evaluation import (
    _score_case,
)
from local_collective_cognition.provider_telemetry import (
    hash_payload,
)


def test_evidence_set_requires_complete_partition():
    case = _public_case()
    receipt = _evidence_receipt(case)
    receipt["irrelevant_unit_ids"] = []

    failures = validate_evidence_set(receipt, public_case=case)

    assert "EVIDENCE_SET_PARTITION_INCOMPLETE" in failures


def test_evidence_unit_cannot_belong_to_two_groups():
    case = _public_case()
    receipt = _evidence_receipt(case)
    receipt["evidence_groups"].append({
        "group_id": "G2",
        "relation": "REFUTES",
        "unit_ids": ["10:0"],
        "rationale": "Duplicate use is forbidden.",
    })

    failures = validate_evidence_set(receipt, public_case=case)

    assert "EVIDENCE_SET_UNIT_IN_MULTIPLE_GROUPS" in failures


def test_scope_receipt_covers_every_evidence_group():
    case = _public_case()
    evidence = _evidence_receipt(case)
    scope = _scope_receipt(case, evidence)
    scope["group_assessments"] = []

    failures = validate_claim_scope(
        scope,
        public_case=case,
        evidence_receipt=evidence,
    )

    assert "CLAIM_SCOPE_GROUP_COVERAGE_INVALID" in failures


def test_material_scope_conflict_compiles_to_abstention():
    case = _public_case()
    evidence = _evidence_receipt(case)
    scope = _scope_receipt(case, evidence)
    scope["claim_state"] = "UNCERTAIN"
    scope["exception_effect"] = "MATERIAL_SCOPE_CONFLICT"

    candidate = compile_evidence_scope_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
    )

    assert candidate["runtime_action"] == "ABSTAIN"
    assert candidate["material_scope_conflict"] is True
    assert candidate["selected_unit_ids"] == []


def test_compiler_selects_only_actionable_matching_groups():
    case = _public_case()
    evidence = _evidence_receipt(case)
    evidence["evidence_groups"].append({
        "group_id": "G2",
        "relation": "REFUTES",
        "unit_ids": ["10:1"],
        "rationale": "A subgroup exception.",
    })
    evidence["irrelevant_unit_ids"] = []
    scope = _scope_receipt(case, evidence)
    scope["exception_effect"] = "QUALIFIES_NOT_OVERTURNS"
    scope["group_assessments"].append({
        "group_id": "G2",
        "scope_level": "SUBGROUP",
        "claim_relation": "EXCEPTION",
        "rationale": "The subgroup exception does not overturn the aggregate.",
    })

    candidate = compile_evidence_scope_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
    )

    assert candidate["runtime_action"] == "OPEN_SUPPORTED_CANDIDATE"
    assert candidate["selected_group_ids"] == ["G1"]
    assert candidate["selected_unit_ids"] == ["10:0"]
    assert candidate["promotion_authorized"] is False


def test_official_sentence_score_requires_complete_gold_set():
    candidate = {
        "semantic_state": "SUPPORTED",
        "runtime_action": "OPEN_SUPPORTED_CANDIDATE",
        "selected_unit_ids": ["10:0"],
    }
    private = {
        "expected_state": "SUPPORTED",
        "metadata": {"gold_rationale_sets": [["10:0", "10:1"]]},
    }

    score = _score_case(
        case_id="7",
        private=private,
        candidate=candidate,
    )

    assert score["label_correct"] is True
    assert score["correct_sentence_count"] == 0
    assert score["overselected_sentence_count"] == 1
    assert score["unrecovered_gold_sentence_count"] == 2


def _public_case():
    return {
        "benchmark_id": "SCIFACT",
        "case_id": "7",
        "layer": "SEMANTIC_WARRANT",
        "cognitive_object": {"claim": "Treatment reduces mortality."},
        "evidence_units": [
            {
                "unit_id": "10:0",
                "text": "Mortality was reduced.",
                "source_object_id": "10",
                "metadata": {"title": "Trial", "sentence_index": 0},
            },
            {
                "unit_id": "10:1",
                "text": "A subgroup showed no reduction.",
                "source_object_id": "10",
                "metadata": {"title": "Trial", "sentence_index": 1},
            },
        ],
        "source_revision": "a" * 40,
        "private_reference_exposed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }


def _evidence_receipt(case):
    return {
        "case_id": case["case_id"],
        "receipt_kind": "EVIDENCE_SET",
        "source_public_case_hash": hash_payload(case),
        "evidence_groups": [{
            "group_id": "G1",
            "relation": "SUPPORTS",
            "unit_ids": ["10:0"],
            "rationale": "A complete aggregate result.",
        }],
        "context_unit_ids": [],
        "irrelevant_unit_ids": ["10:1"],
        "all_units_assessed": True,
        "uncertainty_state": "RESOLVED",
        "rationale": "One minimal evidence group was found.",
    }


def _scope_receipt(case, evidence):
    return {
        "case_id": case["case_id"],
        "receipt_kind": "CLAIM_SCOPE",
        "source_public_case_hash": hash_payload(case),
        "source_evidence_set_hash": hash_payload(evidence),
        "claim_scope": "AGGREGATE_GENERALIZATION",
        "group_assessments": [{
            "group_id": "G1",
            "scope_level": "AGGREGATE",
            "claim_relation": "DIRECTLY_RESOLVES",
            "rationale": "The aggregate result directly resolves the claim.",
        }],
        "claim_state": "SUPPORTED",
        "exception_effect": "NO_MATERIAL_EXCEPTION",
        "all_groups_assessed": True,
        "rationale": "The aggregate evidence supports the claim.",
    }
