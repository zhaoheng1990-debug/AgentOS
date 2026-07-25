from local_collective_cognition.factorized_benchmarks.claim_atom_binding import (
    validate_claim_atom_binding,
)
from local_collective_cognition.factorized_benchmarks.evidence_binding_challenge import (
    validate_binding_challenge,
)
from local_collective_cognition.factorized_benchmarks.kernel_binding_veto import (
    compile_binding_veto_candidate,
)
from local_collective_cognition.provider_telemetry import hash_payload


def test_binding_requires_every_atom_for_every_group():
    case = _public_case()
    evidence = _evidence_receipt(case)
    receipt = _binding_receipt(case, evidence)
    receipt["group_bindings"][0]["atom_bindings"].pop()

    failures = validate_claim_atom_binding(
        receipt,
        public_case=case,
        evidence_receipt=evidence,
    )

    assert "CLAIM_ATOM_BINDING_ATOM_COVERAGE_INVALID" in failures


def test_binding_requires_bridge_state_consistency():
    case = _public_case()
    evidence = _evidence_receipt(case)
    receipt = _binding_receipt(case, evidence)
    receipt["group_bindings"][0]["unstated_bridge_required"] = True
    receipt["group_bindings"][0]["bridge_description"] = "External link."

    failures = validate_claim_atom_binding(
        receipt,
        public_case=case,
        evidence_receipt=evidence,
    )

    assert "CLAIM_ATOM_BINDING_BRIDGE_INCONSISTENT" in failures


def test_challenger_pass_cannot_carry_veto_issue():
    case = _public_case()
    evidence = _evidence_receipt(case)
    receipt = _challenge_receipt(case, evidence)
    receipt["group_challenges"][0]["issue_codes"] = [
        "UNSTATED_SCIENTIFIC_BRIDGE"
    ]

    failures = validate_binding_challenge(
        receipt,
        public_case=case,
        evidence_receipt=evidence,
    )

    assert "BINDING_CHALLENGE_PASS_ISSUES_INCONSISTENT" in failures


def test_kernel_vetoes_unsupported_bridge():
    case = _public_case()
    evidence = _evidence_receipt(case)
    scope = _scope_receipt(case, evidence, state="SUPPORTED")
    binding = _binding_receipt(case, evidence)
    group = binding["group_bindings"][0]
    group["directness"] = "REQUIRES_UNSTATED_BRIDGE"
    group["unstated_bridge_required"] = True
    group["bridge_description"] = "The direction is not stated."
    challenge = _challenge_receipt(case, evidence)

    candidate = compile_binding_veto_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
        binding_receipt=binding,
        challenge_receipt=challenge,
    )

    assert candidate["runtime_action"] == "ABSTAIN"
    assert candidate["semantic_state"] == "UNCERTAIN"
    assert candidate["selected_unit_ids"] == []
    assert candidate["veto_applied"] is True


def test_kernel_retains_direct_fully_bound_group():
    case = _public_case()
    evidence = _evidence_receipt(case)
    scope = _scope_receipt(case, evidence, state="SUPPORTED")

    candidate = compile_binding_veto_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
        binding_receipt=_binding_receipt(case, evidence),
        challenge_receipt=_challenge_receipt(case, evidence),
    )

    assert candidate["runtime_action"] == "OPEN_SUPPORTED_CANDIDATE"
    assert candidate["selected_group_ids"] == ["G1"]
    assert candidate["selected_unit_ids"] == ["10:0"]
    assert candidate["promotion_authorized"] is False


def test_kernel_cannot_promote_unresolved_baseline():
    case = _public_case()
    evidence = _evidence_receipt(case)
    scope = _scope_receipt(case, evidence, state="NOT_ENOUGH_INFO")

    candidate = compile_binding_veto_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
        binding_receipt=_binding_receipt(case, evidence),
        challenge_receipt=_challenge_receipt(case, evidence),
    )

    assert candidate["runtime_action"] == "RETAIN_UNRESOLVED"
    assert candidate["semantic_state"] == "NOT_ENOUGH_INFO"
    assert candidate["selected_group_ids"] == []
    assert candidate["veto_only"] is True


def test_v0_89_refutation_contradiction_is_frozen_as_veto():
    case = _public_case()
    evidence = _evidence_receipt(case)
    evidence["evidence_groups"][0]["relation"] = "REFUTES"
    scope = _scope_receipt(case, evidence, state="REFUTED")
    binding = _binding_receipt(case, evidence)
    binding["source_evidence_set_hash"] = hash_payload(evidence)
    binding["group_bindings"][0]["relation_to_claim"] = "REFUTES"
    binding["group_bindings"][0]["atom_bindings"][2][
        "binding_state"
    ] = "CONTRADICTED"
    challenge = _challenge_receipt(case, evidence)
    challenge["source_evidence_set_hash"] = hash_payload(evidence)

    candidate = compile_binding_veto_candidate(
        public_case=case,
        evidence_receipt=evidence,
        scope_receipt=scope,
        binding_receipt=binding,
        challenge_receipt=challenge,
    )

    assert candidate["runtime_action"] == "ABSTAIN"
    assert any(
        reason.endswith(":CONTRADICTED")
        for reason in candidate["group_decisions"][0]["veto_reasons"]
    )


def _public_case():
    return {
        "benchmark_id": "SCIFACT",
        "case_id": "7",
        "layer": "SEMANTIC_WARRANT",
        "cognitive_object": {"claim": "Treatment reduces mortality."},
        "evidence_units": [
            {
                "unit_id": "10:0",
                "text": "Treatment reduced mortality.",
                "source_object_id": "10",
                "metadata": {"title": "Trial", "sentence_index": 0},
            },
            {
                "unit_id": "10:1",
                "text": "Adverse events were unchanged.",
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
            "rationale": "Direct result.",
        }],
        "context_unit_ids": [],
        "irrelevant_unit_ids": ["10:1"],
        "all_units_assessed": True,
        "uncertainty_state": "RESOLVED",
        "rationale": "One evidence group.",
    }


def _scope_receipt(case, evidence, *, state):
    relation = (
        "DIRECTLY_RESOLVES"
        if state in {"SUPPORTED", "REFUTED"}
        else "QUALIFIES"
    )
    exception = (
        "NO_MATERIAL_EXCEPTION"
        if state == "SUPPORTED"
        else "OVERTURNS"
        if state == "REFUTED"
        else "NOT_APPLICABLE"
    )
    return {
        "case_id": case["case_id"],
        "receipt_kind": "CLAIM_SCOPE",
        "source_public_case_hash": hash_payload(case),
        "source_evidence_set_hash": hash_payload(evidence),
        "claim_scope": "AGGREGATE_GENERALIZATION",
        "group_assessments": [{
            "group_id": "G1",
            "scope_level": "AGGREGATE",
            "claim_relation": relation,
            "rationale": "Scope assessment.",
        }],
        "claim_state": state,
        "exception_effect": exception,
        "all_groups_assessed": True,
        "rationale": "Claim scope assessed.",
    }


def _binding_receipt(case, evidence):
    atoms = [
        {
            "atom_id": "A1",
            "atom_type": "ENTITY_OR_POPULATION",
            "atom_text": "Treatment",
            "required": True,
        },
        {
            "atom_id": "A2",
            "atom_type": "RELATION_OR_OUTCOME",
            "atom_text": "mortality",
            "required": True,
        },
        {
            "atom_id": "A3",
            "atom_type": "DIRECTION_OR_POLARITY",
            "atom_text": "reduces",
            "required": True,
        },
    ]
    return {
        "case_id": case["case_id"],
        "receipt_kind": "CLAIM_ATOM_BINDING",
        "source_public_case_hash": hash_payload(case),
        "source_evidence_set_hash": hash_payload(evidence),
        "claim_atoms": atoms,
        "group_bindings": [{
            "group_id": "G1",
            "relation_to_claim": "SUPPORTS",
            "directness": "DIRECT_EXPLICIT",
            "atom_bindings": [
                {
                    "atom_id": atom["atom_id"],
                    "binding_state": "BOUND_EXPLICIT",
                    "unit_ids": ["10:0"],
                    "rationale": "Explicitly stated.",
                }
                for atom in atoms
            ],
            "unstated_bridge_required": False,
            "bridge_description": "",
            "rationale": "All required atoms are directly bound.",
        }],
        "all_atoms_assessed": True,
        "all_groups_assessed": True,
        "rationale": "Binding complete.",
    }


def _challenge_receipt(case, evidence):
    return {
        "case_id": case["case_id"],
        "receipt_kind": "EVIDENCE_BINDING_CHALLENGE",
        "source_public_case_hash": hash_payload(case),
        "source_evidence_set_hash": hash_payload(evidence),
        "group_challenges": [{
            "group_id": "G1",
            "verdict": "PASS_DIRECT",
            "issue_codes": ["NONE"],
            "unit_ids": ["10:0"],
            "rationale": "The claim is directly stated.",
        }],
        "all_groups_assessed": True,
        "rationale": "No binding defect found.",
    }
