import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
    BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
    PASS_MECHANICAL_RUNTIME_OPERATION,
    PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
    PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
    PROVIDER_COGNITION_LAYER_ID,
    ProviderBackedRuntimeCognitionLayer,
)


def test_contract_declares_provider_required_runtime_cognition_operations():
    layer = ProviderBackedRuntimeCognitionLayer()
    contract = layer.contract()
    operation_ids = {item["operation_id"] for item in contract["provider_required_operations"]}

    assert contract["layer_id"] == PROVIDER_COGNITION_LAYER_ID
    assert contract["provider_final_decision_owner"] is False
    assert contract["final_decision_owner"] == "AgentOSKernel"
    assert "temporal_sro_constraint_field_resolution" in operation_ids
    assert "memory_retention_candidate_evaluation" in operation_ids
    assert "plugin_object_event_extraction" in operation_ids
    assert "plugin_scope_synthesis" in operation_ids
    assert "group_hypothesis_generation" in operation_ids
    assert "adversarial_epistemic_review" in operation_ids
    assert "independent_replication_interpretation" in operation_ids
    assert "group_synthesis_and_conflict_resolution" in operation_ids
    assert "group_outcome_quality_assessment" in operation_ids
    assert "endogenous_problem_generation" in operation_ids
    assert "knowledge_invalidation_root_assessment" in operation_ids
    assert "domain_scope_synthesis" not in operation_ids
    assert contract["contract_hash"]


def test_semantic_operation_without_provider_support_receipt_blocks_closed():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "plugin_object_event_extraction",
        {
            "operation_id": "plugin_object_event_extraction",
            "local_guess": {"entity": "ObjectA", "entity_type": "plugin_defined_object"},
        },
    )

    assert audit["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING
    assert audit["provider_required"] is True
    assert audit["runtime_cognitive_owner"] == "AgentOSKernel"
    assert audit["provider_support_role"] == "semantic_support_required"
    assert "semantic_owner" not in audit
    assert "entities" in audit["missing_provider_outputs"]
    assert audit["fail_closed_behavior"] == "candidate_only_or_insufficient_materials_report"


def test_semantic_operation_passes_with_complete_provider_support_receipt():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "plugin_object_event_extraction",
        {
            "operation_id": "plugin_object_event_extraction",
            "provider_support_receipt": {
                "entities": [{"name": "ObjectA", "entity_type": "plugin_defined_object"}],
                "events": [],
                "entity_type": "plugin_defined_object",
                "source_links": ["https://example.test/object-a"],
                "missing_fields": [],
                "confidence": 0.82,
            },
        },
    )

    assert audit["status"] == PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT
    assert audit["provider_required"] is True
    assert audit["runtime_cognitive_owner"] == "AgentOSKernel"
    assert audit["provider_support_role"] == "semantic_support_present"
    assert audit["provider_support_receipt_hash"]


def test_mechanical_runtime_operation_does_not_require_provider():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "schema_validation",
        {
            "operation_id": "schema_validation",
            "schema_id": "plugin_record_schema_v0_1",
            "valid": True,
        },
    )

    assert audit["status"] == PASS_MECHANICAL_RUNTIME_OPERATION
    assert audit["provider_required"] is False
    assert audit["runtime_cognitive_owner"] == "AgentOSKernel"
    assert audit["provider_support_role"] == "forbidden_for_deterministic_runtime_boundary"


def test_group_semantic_operation_blocks_without_provider_support():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "adversarial_epistemic_review",
        {
            "operation_id": "adversarial_epistemic_review",
            "local_objection_guess": "measurement_leakage",
        },
    )

    assert audit["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING
    assert "strongest_falsifier" in audit["missing_provider_outputs"]
    assert audit["fail_closed_behavior"] == "keep_claim_pending_until_provider_backed_adversarial_review"


def test_group_semantic_operation_passes_with_complete_provider_support():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "adversarial_epistemic_review",
        {
            "operation_id": "adversarial_epistemic_review",
            "provider_support_receipt": {
                "objections": [{"rival": "measurement_leakage"}],
                "strongest_falsifier": "control://leakage",
                "rival_set_coverage": 0.8,
                "evidence_refs": ["evidence://review"],
                "recommended_epistemic_state": "PENDING",
                "confidence": 0.75,
            },
        },
    )

    assert audit["status"] == PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT
    assert audit["runtime_cognitive_owner"] == "AgentOSKernel"
    assert audit["provider_support_receipt_hash"]


def test_group_runtime_mechanics_forbid_provider_override():
    layer = ProviderBackedRuntimeCognitionLayer()

    operation_ids = {
        "agent_registry_context_isolation",
        "group_metric_calculation",
        "epistemic_credit_ledger_projection",
        "dependency_invalidation_propagation",
    }
    audits = [layer.audit_operation(operation_id, {"operation_id": operation_id}) for operation_id in operation_ids]

    assert all(audit["status"] == PASS_MECHANICAL_RUNTIME_OPERATION for audit in audits)
    assert all(audit["provider_required"] is False for audit in audits)


def test_semantic_consistency_assertions_pass_when_receipt_matches_frozen_evidence():
    layer = ProviderBackedRuntimeCognitionLayer()
    receipt = {
        "replication_outcome": "FAILED",
        "bounded_claim_replication_outcome": "PASSED",
        "gate_results": {"G3": 0, "G4": 2, "G6": False},
        "deviations": [],
        "evidence_refs": ["evidence://frozen-verdict"],
        "confidence": 0.9,
    }

    audit = layer.audit_operation(
        "independent_replication_interpretation",
        {
            "provider_support_receipt": receipt,
            "semantic_consistency_assertions": [
                {"assertion_id": "g4-count", "path": "gate_results.G4", "operator": "equals", "expected": 2},
                {
                    "assertion_id": "bounded-outcome",
                    "path": "bounded_claim_replication_outcome",
                    "operator": "equals",
                    "expected": "PASSED",
                },
            ],
        },
    )

    assert audit["status"] == PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT
    assert audit["semantic_consistency"]["failed_count"] == 0
    assert audit["provider_support_role"] == "semantic_support_consistent"


def test_semantic_consistency_assertions_block_conflicting_receipt():
    layer = ProviderBackedRuntimeCognitionLayer()
    receipt = {
        "replication_outcome": "FAILED",
        "bounded_claim_replication_outcome": "FAILED",
        "gate_results": {"G3": 0, "G4": 2, "G6": False},
        "deviations": [],
        "evidence_refs": ["evidence://frozen-verdict"],
        "confidence": 0.9,
    }

    audit = layer.audit_operation(
        "independent_replication_interpretation",
        {
            "provider_support_receipt": receipt,
            "semantic_consistency_assertions": [
                {
                    "assertion_id": "bounded-outcome-matches-g4",
                    "path": "bounded_claim_replication_outcome",
                    "operator": "equals",
                    "expected": "PASSED",
                    "evidence_refs": ["evidence://frozen-verdict"],
                }
            ],
        },
    )

    assert audit["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT
    assert audit["semantic_consistency"]["failed_count"] == 1
    failure = audit["semantic_consistency"]["results"][0]
    assert failure["observed"] == "FAILED"
    assert failure["reason"] == "assertion_value_mismatch"
    assert audit["fail_closed_behavior"] == "keep_claim_pending_until_independent_replication_interpretation"


def test_semantic_consistency_equals_does_not_treat_boolean_as_integer():
    layer = ProviderBackedRuntimeCognitionLayer()
    receipt = {
        "replication_outcome": "FAILED",
        "gate_results": {"G4": False},
        "deviations": [],
        "evidence_refs": ["evidence://frozen-verdict"],
        "confidence": 0.9,
    }

    audit = layer.audit_operation(
        "independent_replication_interpretation",
        {
            "provider_support_receipt": receipt,
            "semantic_consistency_assertions": [
                {"assertion_id": "g4-count", "path": "gate_results.G4", "operator": "equals", "expected": 0}
            ],
        },
    )

    assert audit["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT


def test_pipeline_audit_blocks_when_any_provider_required_operation_lacks_judgment():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_pipeline(
        [
            {
                "operation_id": "schema_validation",
                "valid": True,
            },
            {
                "operation_id": "memory_retention_candidate_evaluation",
                "candidate_id": "candidate_without_provider_review",
            },
        ]
    )

    assert audit["status"] == "BLOCKED"
    assert audit["blocked_count"] == 1


def test_pipeline_audit_blocks_internally_inconsistent_provider_receipt():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_pipeline(
        [
            {
                "operation_id": "independent_replication_interpretation",
                "provider_support_receipt": {
                    "replication_outcome": "FAILED",
                    "gate_results": {"G4": 2},
                    "deviations": [],
                    "evidence_refs": ["evidence://frozen-verdict"],
                    "confidence": 0.9,
                },
                "semantic_consistency_assertions": [
                    {
                        "assertion_id": "overbroad-outcome",
                        "path": "replication_outcome",
                        "operator": "equals",
                        "expected": "PASSED",
                    }
                ],
            }
        ]
    )

    assert audit["status"] == "BLOCKED"
    assert audit["blocked_count"] == 1
    assert audit["audits"][0]["status"] == BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT
