import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import (
    AGENTOS_CORE_SLIM_PATCH_SEED,
    AGENTOS_CORE_SLIM_FEATURE_SET,
    AGENTOS_CORE_SLIM_VERSION,
    ArtifactIdentity,
    ArtifactVersionStore,
    CognitiveAssetEntry,
    CognitiveAssetLedger,
    EvidenceDimensionRegistry,
    EvidenceDimensionSpec,
    ProviderCapabilityProfile,
    ProviderCognitiveTask,
    ProviderTaskRouter,
    PublicationDecision,
    QualityDecisionMatrix,
    RuntimeTaskLifecycle,
    is_source_audit_excluded,
)


class StaticAdapter:
    def __init__(self, provider_id, result, *, fail=False):
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=f"{provider_id}-model",
            task_kinds=("generic_semantic_task",),
            max_timeout_seconds=120,
        )
        self.result = result
        self.fail = fail

    def invoke(self, task):
        if self.fail:
            raise RuntimeError("provider unavailable")
        return {
            "result": self.result,
            "usage": {"input_tokens": 10, "output_tokens": 5},
            "provenance_refs": ["source://fixture"],
        }


def _task():
    return ProviderCognitiveTask(
        task_id="task-1",
        task_kind="generic_semantic_task",
        objective="Return a bounded semantic judgment.",
        inputs={"object": "ObjectA"},
        allowed_evidence=["source://fixture"],
        expected_schema={
            "required": ["judgment", "confidence"],
            "properties": {
                "judgment": {"type": "string"},
                "confidence": {"type": "number"},
            },
        },
    )


def test_version_preserves_patch_seed_and_declares_sro_retention_runtime_feature_set():
    assert AGENTOS_CORE_SLIM_VERSION == "0.4.0-alpha.10"
    assert AGENTOS_CORE_SLIM_PATCH_SEED == "AgentOS_CoreRefactor_ProviderCognition_QualityLifecycle_Seed_v0_1"
    assert AGENTOS_CORE_SLIM_FEATURE_SET == "provider_backed_sro_retention_runtime_v0_2"


def test_provider_task_routes_through_two_adapters_with_same_contract():
    result = {"judgment": "candidate", "confidence": 0.8}
    envelope_a = ProviderTaskRouter([StaticAdapter("provider-a", result)]).route(_task())
    envelope_b = ProviderTaskRouter([StaticAdapter("provider-b", result)]).route(_task())

    assert envelope_a.status == "COMPLETED"
    assert envelope_b.status == "COMPLETED"
    assert envelope_a.normalized_result == envelope_b.normalized_result
    assert envelope_a.invocation_receipt.input_hash == envelope_b.invocation_receipt.input_hash
    assert envelope_a.semantic_result_present is True


def test_provider_failure_is_typed_and_does_not_fabricate_semantic_output():
    envelope = ProviderTaskRouter([StaticAdapter("provider-a", {}, fail=True)]).route(_task())

    assert envelope.status == "PROVIDER_UNAVAILABLE"
    assert envelope.normalized_result is None
    assert envelope.semantic_result_present is False
    assert envelope.invocation_receipt.fallback_decision.decision == "provider_unavailable"


def test_provider_schema_validation_distinguishes_boolean_number_and_integer():
    task = ProviderCognitiveTask(
        task_id="typed-task",
        task_kind="generic_semantic_task",
        objective="Return typed fields.",
        inputs={},
        allowed_evidence=["source://fixture"],
        expected_schema={
            "required": ["flag", "score", "count"],
            "properties": {
                "flag": {"type": "boolean"},
                "score": {"type": "number"},
                "count": {"type": "integer"},
            },
        },
    )
    adapter = StaticAdapter(
        "provider-a",
        {"flag": [], "score": True, "count": 1.5},
    )

    envelope = ProviderTaskRouter([adapter]).route(task)

    assert envelope.status == "VALIDATION_FAILED"
    assert "field_type_mismatch:flag:boolean" in envelope.validation_errors
    assert "field_type_mismatch:score:number" in envelope.validation_errors
    assert "field_type_mismatch:count:integer" in envelope.validation_errors


def test_router_falls_back_after_schema_invalid_provider_result():
    invalid = StaticAdapter("provider-invalid", {"judgment": "candidate"})
    valid = StaticAdapter("provider-valid", {"judgment": "candidate", "confidence": 0.8})

    envelope = ProviderTaskRouter([invalid, valid]).route(_task())

    assert envelope.status == "COMPLETED"
    assert envelope.invocation_receipt.provider_id == "provider-valid"
    assert envelope.invocation_receipt.retry_count == 1
    assert envelope.invocation_receipt.fallback_decision.attempted_providers == (
        "provider-invalid",
        "provider-valid",
    )


def test_reader_integrity_failure_blocks_only_candidate_revision_and_preserves_published_pointer():
    store = ArtifactVersionStore()
    store.register_identity(ArtifactIdentity("artifact-1", "generic_artifact"))
    published = store.create_candidate_revision("artifact-1", {"body": "published"})
    store.publish(PublicationDecision("PUBLISH_CURRENT", "PublicationRetentionGate", "artifact-1", published.revision_id, "readable"))
    candidate = store.create_candidate_revision("artifact-1", {"body": "broken candidate"}, parent_revision_id=published.revision_id)

    decision = QualityDecisionMatrix().evaluate(
        "ReaderIntegrityGate",
        {
            "revision_id": candidate.revision_id,
            "reader_defects": [{"repair_action": "repair_table", "evidence_refs": ["defect://table"]}],
        },
    )

    assert decision.status == "BLOCKED"
    assert decision.blocked_control_objects == (candidate.revision_id,)
    assert store.current_pointer("artifact-1").revision_id == published.revision_id


def test_scope_coverage_qualified_does_not_block_readability():
    decision = QualityDecisionMatrix().evaluate(
        "ScopeCoverageGate",
        {
            "coverage_objects": [
                {"object_id": "coverage-a", "state": "qualified", "evidence_refs": ["source://partial"]}
            ]
        },
    )

    assert decision.status == "PASS"
    assert decision.findings[0].blocking_effect == "no_readability_block"


def test_failed_supplement_candidate_cannot_overwrite_published_artifact():
    store = ArtifactVersionStore()
    published = store.create_candidate_revision("artifact-2", {"body": "stable"})
    store.publish(PublicationDecision("PUBLISH_CURRENT", "PublicationRetentionGate", "artifact-2", published.revision_id, "readable"))
    failed = store.create_candidate_revision("artifact-2", {"body": "failed supplement"}, parent_revision_id=published.revision_id)
    publication_gate = QualityDecisionMatrix().evaluate(
        "PublicationRetentionGate",
        {"candidate_revision_id": failed.revision_id, "candidate_status": "failed"},
    )

    assert publication_gate.status == "BLOCKED"
    assert store.current_pointer("artifact-2").revision_id == published.revision_id


def test_rollback_restores_prior_revision_pointer_and_replays_from_ledger():
    store = ArtifactVersionStore()
    first = store.create_candidate_revision("artifact-3", {"body": "first"})
    second = store.create_candidate_revision("artifact-3", {"body": "second"}, parent_revision_id=first.revision_id)
    store.publish(PublicationDecision("PUBLISH_CURRENT", "PublicationRetentionGate", "artifact-3", first.revision_id, "publish first"))
    store.publish(PublicationDecision("PUBLISH_CURRENT", "PublicationRetentionGate", "artifact-3", second.revision_id, "publish second"))

    rollback = store.rollback_published_pointer("artifact-3", first.revision_id)
    replayed = store.replay_pointers()

    assert rollback.restored_revision_id == first.revision_id
    assert rollback.receipt_id
    assert replayed[("artifact-3", "published_current")].revision_id == first.revision_id


def test_task_pause_resume_survives_runtime_restart(tmp_path):
    lifecycle = RuntimeTaskLifecycle(tmp_path)
    lifecycle.intake("run-1", "generic_long_running_task", timeout_seconds=60)
    lifecycle.plan("run-1", ["stage-a", "stage-b"])
    lifecycle.start("run-1")
    lifecycle.checkpoint("run-1", "stage-a", {"done": True})
    lifecycle.pause("run-1", "operator requested pause")

    restarted = RuntimeTaskLifecycle(tmp_path)
    loaded = restarted.load("run-1")
    resumed = restarted.resume("run-1")

    assert loaded.state == "PAUSED"
    assert loaded.checkpoints["stage-a"]["payload"] == {"done": True}
    assert resumed.state == "RUNNING"


def test_projection_adapter_renders_without_mutation_or_baseline_authority():
    class MarkdownProjection:
        projection_id = "markdown_projection"

        def render(self, entries):
            return {"projection_id": self.projection_id, "line_count": len(entries)}

    ledger = CognitiveAssetLedger()
    ledger.append(
        CognitiveAssetEntry(
            asset_id="asset-1",
            revision_id="rev-1",
            asset_type="generic_memory",
            status="candidate",
            source_refs=("source://fixture",),
            visibility_boundary="project",
        )
    )

    projection = ledger.project(MarkdownProjection())

    assert projection["line_count"] == 1
    assert projection["projection_mutation_authority"] is False
    assert projection["baseline_write_authority"] is False


def test_evidence_dimension_registry_and_source_hygiene_are_domain_neutral():
    registry = EvidenceDimensionRegistry()
    registry.register(
        EvidenceDimensionSpec(
            dimension_id="generic_support",
            claim_support_model="claim_to_source_support",
            freshness_policy="plugin_defined",
            evidence_admission_requirements=("source_ref", "support_path"),
            conflict_strategy="surface_conflict_for_runtime_resolution",
            coverage_object_model="plugin_defined_coverage_object",
            plugin_owner="example_plugin",
        )
    )

    assert registry.as_read_model()["dimension_count"] == 1
    assert is_source_audit_excluded("outputs/run/return_pack.zip") is True
    assert is_source_audit_excluded("agentos_core_slim_v0/agentos_kernel/provider_execution_plane.py") is False


def test_core_package_contains_no_vc_specific_terms():
    core_root = Path(__file__).resolve().parents[1] / "agentos_kernel"
    forbidden_terms = ("company", "funding", "investment", "market size", "diligence", "vcos")
    hits = []
    for path in core_root.glob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            if term in text:
                hits.append((path.name, term))

    assert hits == []
