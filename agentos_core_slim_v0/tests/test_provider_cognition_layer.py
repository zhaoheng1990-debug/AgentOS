import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    BLOCKED_PROVIDER_JUDGMENT_MISSING,
    PASS_MECHANICAL_RUNTIME_OPERATION,
    PASS_PROVIDER_JUDGMENT_PRESENT,
    PROVIDER_COGNITION_LAYER_ID,
    ProviderBackedRuntimeCognitionLayer,
)


def test_contract_declares_provider_required_runtime_cognition_operations():
    layer = ProviderBackedRuntimeCognitionLayer()
    contract = layer.contract()
    operation_ids = {item["operation_id"] for item in contract["provider_required_operations"]}

    assert contract["layer_id"] == PROVIDER_COGNITION_LAYER_ID
    assert contract["provider_decision_owner"] is False
    assert contract["final_decision_owner"] == "AgentOSKernel"
    assert "temporal_sro_constraint_field_resolution" in operation_ids
    assert "memory_retention_candidate_evaluation" in operation_ids
    assert "entity_and_event_extraction" in operation_ids
    assert "domain_scope_synthesis" in operation_ids
    assert contract["contract_hash"]


def test_semantic_operation_without_provider_judgment_blocks_closed():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "entity_and_event_extraction",
        {
            "operation_id": "entity_and_event_extraction",
            "local_guess": {"entity": "ObjectA", "entity_type": "plugin_defined_object"},
        },
    )

    assert audit["status"] == BLOCKED_PROVIDER_JUDGMENT_MISSING
    assert audit["provider_required"] is True
    assert audit["semantic_owner"] == "provider"
    assert "entities" in audit["missing_provider_outputs"]
    assert audit["fail_closed_behavior"] == "candidate_only_or_insufficient_materials_report"


def test_semantic_operation_passes_with_complete_provider_judgment():
    layer = ProviderBackedRuntimeCognitionLayer()

    audit = layer.audit_operation(
        "entity_and_event_extraction",
        {
            "operation_id": "entity_and_event_extraction",
            "provider_judgment": {
                "entities": [{"name": "ObjectA", "entity_type": "plugin_defined_object"}],
                "events": [],
                "entity_type": "plugin_defined_object",
                "source_links": ["https://example.test/object-a"],
                "missing_fields": [],
                "confidence": 0.82,
            },
        },
    )

    assert audit["status"] == PASS_PROVIDER_JUDGMENT_PRESENT
    assert audit["provider_required"] is True
    assert audit["semantic_owner"] == "provider"
    assert audit["provider_judgment_hash"]


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
    assert audit["semantic_owner"] == "none"


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
