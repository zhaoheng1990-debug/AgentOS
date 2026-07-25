from __future__ import annotations

import json

import pytest

from theory_first_r4_relation.role_audit import audit_role_experiment
from theory_first_r4_relation.role_cases import (
    EFFECT_ATTRIBUTES,
    PROVENANCE_ATTRIBUTES,
    ROLE_CASES,
    WIDE_ATTRIBUTES,
)
from theory_first_r4_relation.role_cli import CALLS
from theory_first_r4_relation.role_composer import (
    compile_composed,
    compose_receipts,
    fail_closed_mutation_audit,
    private_outcomes,
)
from theory_first_r4_relation.role_prompts import role_prompt
from theory_first_r4_relation.role_schemas import parse_role_receipts
from theory_first_r4_relation.role_scoring import score_role_experiment


ATTRIBUTES_BY_SCOPE = {
    "wide": WIDE_ATTRIBUTES,
    "provenance": PROVENANCE_ATTRIBUTES,
    "effect": EFFECT_ATTRIBUTES,
}


def _oracle_content(
    scope: str,
    *,
    wrong_source_cases: frozenset[str] = frozenset(),
    forbidden_field: str | None = None,
) -> str:
    attributes = ATTRIBUTES_BY_SCOPE[scope]
    receipts = []
    for case in ROLE_CASES:
        values = case.factorized_dict()
        item = {
            "case_id": case.case_id,
            **{name: values[name] for name in attributes},
            "attribute_evidence_refs": {
                name: list(refs)
                for name, refs in case.expected_refs(attributes).items()
            },
            "missing_facts": [],
        }
        if (
            case.case_id in wrong_source_cases
            and "source_identity" in attributes
        ):
            item["source_identity"] = "UNKNOWN_SOURCE"
        if forbidden_field:
            item[forbidden_field] = "BLOCK"
        receipts.append(item)
    return json.dumps({"receipts": receipts}, sort_keys=True)


def _parsed_calls(*, wide_errors: bool):
    parsed = {}
    wrong = frozenset({"R43K-01", "R43K-05"}) if wide_errors else frozenset()
    for call_id, scope, _ in CALLS:
        selected_wrong = wrong if call_id.startswith("wide_source_p") else frozenset()
        parsed[call_id] = parse_role_receipts(
            _oracle_content(scope, wrong_source_cases=selected_wrong),
            scope,
        )
    return parsed


def _ledger():
    return [
        {
            "logical_call_id": call_id,
            "attempt": 1,
            "status": "VALID",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 100,
                "total_tokens": 200,
                "cache_hit_tokens": 0,
            },
        }
        for call_id, _, _ in CALLS
    ]


def test_corpus_has_frozen_shape():
    assert len(ROLE_CASES) == 16
    assert [case.case_id for case in ROLE_CASES] == [
        f"R43K-{index:02d}" for index in range(1, 17)
    ]
    assert {
        category: sum(case.category == category for case in ROLE_CASES)
        for category in {case.category for case in ROLE_CASES}
    } == {
        "provenance_edge": 4,
        "effect_scope_edge": 4,
        "cross_role_interaction": 4,
        "null_unknown": 4,
    }


def test_deterministic_audit_passes_all_gates():
    result = audit_role_experiment()
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"] == 17


def test_wide_prompt_has_no_extraction_position_signal():
    for reverse in (False, True):
        prompt = role_prompt("wide", reverse)
        assert "wide_source_p" not in prompt
        assert "wide_source_e" not in prompt
        assert prompt == role_prompt("wide", reverse)


def test_scope_prompts_request_only_frozen_attributes():
    provenance = role_prompt("provenance", False)
    effect = role_prompt("effect", False)
    for name in PROVENANCE_ATTRIBUTES:
        assert name in provenance
    for name in EFFECT_ATTRIBUTES:
        assert name not in provenance
    for name in EFFECT_ATTRIBUTES:
        assert name in effect
    for name in PROVENANCE_ATTRIBUTES:
        assert name not in effect


@pytest.mark.parametrize("scope", ("wide", "provenance", "effect"))
def test_parser_accepts_exact_oracle_receipts(scope):
    parsed = parse_role_receipts(_oracle_content(scope), scope)
    assert len(parsed.receipts) == 16
    assert parsed.scope == scope


def test_parser_rejects_provider_action_authority():
    with pytest.raises(ValueError, match="forbidden Provider authority"):
        parse_role_receipts(
            _oracle_content("wide", forbidden_field="action"),
            "wide",
        )


def test_parser_rejects_out_of_case_evidence():
    value = json.loads(_oracle_content("provenance"))
    value["receipts"][0]["attribute_evidence_refs"]["source_identity"] = [
        "evidence://r43k-02/source"
    ]
    with pytest.raises(ValueError, match="evidence scope mismatch"):
        parse_role_receipts(json.dumps(value), "provenance")


def test_private_composer_has_exact_valid_outcomes():
    outcomes = private_outcomes()
    assert len(outcomes) == 16
    assert all(not result["errors"] for result in outcomes.values())


def test_role_composition_matches_private_outcomes():
    provenance = parse_role_receipts(
        _oracle_content("provenance"), "provenance"
    )
    effect = parse_role_receipts(_oracle_content("effect"), "effect")
    receipts = compose_receipts(provenance, effect, "split", "forward")
    expected = private_outcomes()
    for receipt in receipts:
        compiled = compile_composed(receipt)
        assert compiled.relation_state == expected[receipt.case_id]["relation_state"]
        assert compiled.action == expected[receipt.case_id]["action"]


def test_incomplete_and_incoherent_candidates_fail_closed():
    result = fail_closed_mutation_audit()
    assert result == {
        "invalid_status_effect": True,
        "missing_source_witness": True,
        "missing_tolerance_witness": True,
    }


def test_all_correct_arms_do_not_self_pass_causal_gain():
    result = score_role_experiment(
        _parsed_calls(wide_errors=False),
        _ledger(),
        preflight_ok=True,
        replay_identical=True,
    )
    assert result["role_bundle_gains"] == {"forward": 0, "reverse": 0}
    assert result["status"] == "FAIL_NO_DECOMPOSITION_BENEFIT"
    assert not result["gates"]["split_role_bundle_gain"]


def test_frozen_positive_construction_passes_only_with_matched_gain():
    result = score_role_experiment(
        _parsed_calls(wide_errors=True),
        _ledger(),
        preflight_ok=True,
        replay_identical=True,
    )
    assert result["role_bundle_gains"] == {"forward": 2, "reverse": 2}
    assert result["status"] == (
        "PASS_RESPONSIBILITY_BOUNDED_INTERFERENCE_SUPPORTED"
    )
    assert result["gate_pass_count"] == result["gate_count"] == 18


def test_scoring_is_byte_deterministic():
    first = score_role_experiment(
        _parsed_calls(wide_errors=True),
        _ledger(),
        preflight_ok=True,
        replay_identical=True,
    )
    second = score_role_experiment(
        _parsed_calls(wide_errors=True),
        _ledger(),
        preflight_ok=True,
        replay_identical=True,
    )
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
