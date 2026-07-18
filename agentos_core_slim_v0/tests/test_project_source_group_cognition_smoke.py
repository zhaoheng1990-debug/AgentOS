import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.project_source_group_cognition_smoke import (
    SOURCE_ENTRIES,
    build_member_observations,
    load_source_dossier,
    replicator_consistency_assertions,
    score_fact_alignment,
)
from agentos_kernel import (
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    ProviderBackedRuntimeCognitionLayer,
)


def test_source_dossier_reads_required_entries_and_hashes_without_extraction(tmp_path):
    pack = tmp_path / "source.zip"
    gate = tmp_path / "gates.json"
    gate.write_text(json.dumps({"experiment_id": "LIFE_COG3R", "gates": {"G3": {}}}), encoding="utf-8")
    payloads = {
        SOURCE_ENTRIES[0]: json.dumps({"machine_classification": "FAIL_NEGATIVE_CONTROLS"}),
        SOURCE_ENTRIES[1]: json.dumps({"structural_qa_pass": True}),
        SOURCE_ENTRIES[2]: "# PM summary",
        SOURCE_ENTRIES[3]: "# Receipt",
    }
    with zipfile.ZipFile(pack, "w") as archive:
        for name, payload in payloads.items():
            archive.writestr(name, payload)

    dossier, inventory = load_source_dossier(pack, gate)

    assert dossier["machine_verdict"]["machine_classification"] == "FAIL_NEGATIVE_CONTROLS"
    assert dossier["independent_structural_qa"]["structural_qa_pass"] is True
    assert len(inventory) == 6
    assert all(len(item["sha256"]) == 64 for item in inventory)


def test_fact_alignment_score_uses_frozen_project_truth_not_provider_confidence():
    result = {
        "source_machine_classification": "FAIL_NEGATIVE_CONTROLS",
        "retention_gate_supported": False,
        "local_generalization_gap_supported_rules": ["HighLife", "DayNight"],
        "negative_controls_passed": False,
        "highest_conclusion_allowed": False,
        "boundary_respected": True,
        "confidence": 0.01,
    }

    score, checks = score_fact_alignment(result)

    assert score == 1.0
    assert all(checks.values())


def test_fact_alignment_mechanically_normalizes_registered_rule_labels_with_details():
    result = {
        "source_machine_classification": "FAIL_NEGATIVE_CONTROLS",
        "retention_gate_supported": False,
        "local_generalization_gap_supported_rules": [
            "toroidal DayNight: paired_effect_d=0.5796",
            "toroidal HighLife: corrected_p=0.0006",
        ],
        "negative_controls_passed": False,
        "highest_conclusion_allowed": False,
        "boundary_respected": True,
    }

    score, checks = score_fact_alignment(result)

    assert score == 1.0
    assert checks["local_g4_rules_preserved"] is True


def test_fact_alignment_penalizes_overpromotion():
    result = {
        "source_machine_classification": "PASS_VALIDATION_GATED_RETENTION",
        "retention_gate_supported": True,
        "local_generalization_gap_supported_rules": ["DayNight", "HighLife"],
        "negative_controls_passed": True,
        "highest_conclusion_allowed": True,
        "boundary_respected": False,
    }

    score, checks = score_fact_alignment(result)

    assert score == pytest.approx(1 / 6)
    assert checks["local_g4_rules_preserved"] is True


def test_member_observations_use_each_roles_own_result():
    role_results = {
        "generator": {"hypotheses": ["generator-hypothesis"]},
        "reviewer": {"hypotheses": ["reviewer-hypothesis"]},
        "replicator": {"hypotheses": ["replicator-hypothesis"]},
        "synthesizer": {"hypotheses": ["synthesizer-hypothesis"]},
    }
    fact_scores = {role: (0.5, {}) for role in role_results}
    agent_ids = {role: f"agent-{role}" for role in role_results}
    receipt_refs = {role: f"receipt://{role}" for role in role_results}

    observations = build_member_observations(role_results, fact_scores, agent_ids, receipt_refs)

    assert [item.subject_id for item in observations] == [
        "agent-generator",
        "agent-reviewer",
        "agent-replicator",
    ]
    assert [item.hypotheses for item in observations] == [
        ("generator-hypothesis",),
        ("reviewer-hypothesis",),
        ("replicator-hypothesis",),
    ]


def test_project_replicator_consistency_gate_rejects_conflict_and_accepts_correction():
    layer = ProviderBackedRuntimeCognitionLayer()
    assertions = replicator_consistency_assertions(["evidence://machine-verdict"])
    receipt = {
        "source_machine_classification": "FAIL_NEGATIVE_CONTROLS",
        "retention_gate_supported": False,
        "negative_controls_passed": False,
        "highest_conclusion_allowed": False,
        "boundary_respected": True,
        "gate_results": {
            "G3_retention_eligibility_positive_rules": 0,
            "G4_generalization_gap_positive_rules": 2,
            "G6_negative_controls": False,
        },
        "local_generalization_gap_supported_rules": ["DayNight", "HighLife"],
        "replication_outcome": "FAILED",
        "bounded_claim_replication_outcome": "FAILED",
        "deviations": [],
        "evidence_refs": ["evidence://machine-verdict"],
        "confidence": 0.9,
    }

    conflicted = layer.audit_operation(
        "independent_replication_interpretation",
        {"provider_support_receipt": receipt, "semantic_consistency_assertions": assertions},
    )
    receipt["bounded_claim_replication_outcome"] = "PASSED"
    corrected = layer.audit_operation(
        "independent_replication_interpretation",
        {"provider_support_receipt": receipt, "semantic_consistency_assertions": assertions},
    )

    assert conflicted["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT
    assert corrected["status"] == PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT
