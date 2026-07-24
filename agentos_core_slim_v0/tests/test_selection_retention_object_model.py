import ast
import sys
from dataclasses import replace
from pathlib import Path

import pytest


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ApplicabilityDelta,
    CognitiveActionReceipt,
    ConsequenceBinding,
    PortfolioSelectionRetentionGate,
    ProspectiveSelectionEvent,
    SemanticOperatorRoute,
    SerialSelectionWitness,
    TypedEvidenceConsensusGate,
    TypedRelationEvidenceBinding,
    ValidityAssessment,
    ValueDelta,
)
from agentos_runtime import (  # noqa: E402
    SelectionRetentionRepository,
    SerialSelectionWitnessAdapter,
)


HASH_A = "a" * 64
HASH_B = "b" * 64
HASH_C = "c" * 64
NOW = "2026-07-25T00:00:00+00:00"
EVIDENCE = ("evidence://selection-test",)


def selection():
    return ProspectiveSelectionEvent.create(
        selection_event_id="selection-1",
        project_scope="project://selection-test",
        selection_context_ref="context://selection-test",
        alternatives=("operator://baseline", "operator://challenge"),
        selected_ref="operator://challenge",
        rejected_refs=("operator://baseline",),
        deferred_refs=(),
        path_change_hypothesis_ref="hypothesis://challenge-changes-path",
        sro_address_ref="sro://selection-test",
        validity_boundary_ref="validity://selection-test",
        reconstruction_ref="replay://selection-test",
        authority_ref="kernel://selection-test",
        evidence_refs=EVIDENCE,
        sealed_at=NOW,
    )


def consequence(value):
    return ConsequenceBinding.create(
        binding_id="consequence-1",
        project_scope=value.project_scope,
        selection_event_hash=value.preconsequence_hash,
        consequence_ref="harness://selection-outcome",
        consequence_kind="IMMEDIATE",
        evidence_refs=EVIDENCE,
        observed_at=NOW,
    )


def portfolio(value, outcome, *, validity_state="CURRENT", cbit=0.7):
    applicability = ApplicabilityDelta(
        selection_event_hash=value.preconsequence_hash,
        consequence_binding_hash=outcome.binding_hash,
        applicability_delta=0.4,
        provider_receipt_hash=HASH_A,
        evidence_refs=EVIDENCE,
    )
    observed_value = ValueDelta(
        selection_event_hash=value.preconsequence_hash,
        consequence_binding_hash=outcome.binding_hash,
        observed_cbit_gain=cbit,
        observed_cost=0.2,
        harness_receipt_hash=HASH_B,
        evidence_refs=EVIDENCE,
    )
    validity = ValidityAssessment(
        selection_event_hash=value.preconsequence_hash,
        validity_state=validity_state,
        boundary_ref=value.validity_boundary_ref,
        provider_receipt_hash=HASH_C,
        evidence_refs=EVIDENCE,
    )
    route = SemanticOperatorRoute(
        route_id="semantic-route-1",
        project_scope=value.project_scope,
        selection_event_hash=value.preconsequence_hash,
        ranked_alternative_refs=value.alternatives,
        selected_ref=value.selected_ref,
        expected_cbit_gain=0.5,
        residual_risk=0.2,
        uncertainty=0.2,
        provider_receipt_hash=HASH_A,
        evidence_refs=EVIDENCE,
    )
    return applicability, observed_value, validity, route


def binding(*, corroborating=(), counter=()):
    return TypedRelationEvidenceBinding(
        relation_id="relation://source-target",
        source_object_ref="object://source",
        target_object_ref="object://target",
        source_object_binding="EXACT_EXPLICIT",
        target_outcome_binding="COREFERENCE",
        evidence_design="INTERVENTION_OR_ROLLBACK",
        primary_evidence_refs=("evidence://primary",),
        corroborating_evidence_refs=corroborating,
        counterevidence_refs=counter,
    )


def witness():
    return SerialSelectionWitness(
        witness_id="legacy-witness-1",
        status="PRECOMMITTED",
        project_scope_ref="project://selection-test",
        selection_context_ref="context://selection-test",
        sro_address_ref="sro://selection-test",
        validity_boundary_ref="validity://selection-test",
        reconstruction_ref="replay://selection-test",
        authority_ref="kernel://legacy-selection",
        privacy_boundary="project-private",
        precommit_hash=HASH_A,
        sealed_at=NOW,
        evidence_refs=EVIDENCE,
    )


def test_cognitive_action_receipt_enforces_role_and_hash():
    receipt = CognitiveActionReceipt.create(
        action_id="action-1",
        action_type="FALSIFY",
        object_ref="claim://one",
        actor_role="ASSESSMENT_SKEPTIC",
        actor_instance="agent://skeptic",
        method="provider-backed review",
        result_state="CHALLENGED",
        result={"objection": "alternative mechanism"},
        evidence_refs=EVIDENCE,
        counterevidence=("evidence://counter",),
        recommended_next_actions=("REPLICATE",),
    )
    assert receipt.as_dict()["kernel_final_state_authority"] is True
    assert receipt.as_dict()["retention_authority"] is False
    with pytest.raises(ValueError, match="outside_role_capability"):
        replace(receipt, action_type="SYNTHESIZE")
    with pytest.raises(ValueError, match="receipt_hash_invalid"):
        replace(receipt, receipt_hash=HASH_A)


def test_typed_evidence_unions_only_nonconflicting_auxiliary_evidence():
    gate = TypedEvidenceConsensusGate()
    consensus = gate.evaluate(
        binding(corroborating=("evidence://replication",)),
        binding(),
        left_receipt_hash=HASH_A,
        right_receipt_hash=HASH_B,
    )
    assert consensus.ready is True
    assert consensus.relation_binding.corroborating_evidence_refs == (
        "evidence://replication",
    )
    assert consensus.auxiliary_divergences == (
        "corroborating_evidence_refs",
    )
    assert consensus.as_dict()["truth_state_authority"] is False

    conflict = gate.evaluate(
        binding(corroborating=("evidence://replication",)),
        binding(counter=("evidence://replication",)),
        left_receipt_hash=HASH_A,
        right_receipt_hash=HASH_B,
    )
    assert conflict.ready is False
    assert "EVIDENCE_TYPE_CONFLICT" in conflict.conflicts


def test_selection_is_sealed_before_consequence_and_consequence_unassigned():
    value = selection()
    outcome = consequence(value)
    assert value.as_dict()["consequence_known"] is False
    assert value.as_dict()["retention_authority"] is False
    assert outcome.assignment_state == "UNASSIGNED"
    assert outcome.as_dict()["retention_attribution_authority"] is False
    with pytest.raises(ValueError, match="partition_incomplete"):
        replace(value, rejected_refs=())


def test_portfolio_gate_keeps_validity_noncompensable_and_shadow_only():
    value = selection()
    outcome = consequence(value)
    applicability, observed, validity, route = portfolio(value, outcome)
    gate = PortfolioSelectionRetentionGate()
    decision = gate.evaluate(
        selection=value,
        consequences=(outcome,),
        applicability_deltas=(applicability,),
        value_deltas=(observed,),
        validity=validity,
        semantic_route=route,
    )
    assert decision.decision == "CANDIDATE_RETAIN"
    assert decision.candidate_state == "PENDING_RETENTION_REVIEW"
    assert decision.as_dict()["global_memory_write_authority"] is False

    _, huge_value, stale, route = portfolio(
        value, outcome, validity_state="STALE", cbit=1000.0
    )
    blocked = gate.evaluate(
        selection=value,
        consequences=(outcome,),
        applicability_deltas=(applicability,),
        value_deltas=(huge_value,),
        validity=stale,
        semantic_route=route,
    )
    assert blocked.decision == "QUARANTINE"
    assert "VALIDITY_HARD_STOP" in blocked.hard_gate_failures


def test_incomplete_portfolio_observes_without_scalar_guess():
    value = selection()
    decision = PortfolioSelectionRetentionGate().evaluate(
        selection=value,
        consequences=(),
        applicability_deltas=(),
        value_deltas=(),
        validity=None,
        semantic_route=None,
    )
    assert decision.decision == "OBSERVE"
    assert decision.retention_candidate_eligible is False
    assert decision.as_dict()["scalar_legacy_score_authority"] is False


def test_legacy_witness_requires_explicit_selection_reconstruction():
    old = witness()
    adapter = SerialSelectionWitnessAdapter()
    migration = adapter.create(old)
    assert migration.candidate_state == "PENDING_SELECTION_RECONSTRUCTION"
    assert "alternatives" in migration.missing_selection_fields
    assert migration.as_dict()["automatic_promotion_allowed"] is False

    reconstructed = adapter.reconstruct(
        migration=migration,
        witness=old,
        selection_event_id="selection-from-legacy",
        alternatives=("operator://old", "operator://new"),
        selected_ref="operator://new",
        rejected_refs=("operator://old",),
        deferred_refs=(),
        path_change_hypothesis_ref="hypothesis://legacy-reconstructed",
        kernel_authority_ref="kernel://legacy-reconstruction",
    )
    assert reconstructed.evidence_refs == old.evidence_refs
    assert reconstructed.candidate_state == "PRECOMMITTED_SELECTION"


def test_selection_repository_replays_hash_chain_and_unassigned_ledger(
    tmp_path,
):
    value = selection()
    outcome = consequence(value)
    repository = SelectionRetentionRepository(
        runtime_id="selection-runtime",
        project_scope=value.project_scope,
        workspace_root=tmp_path,
    )
    repository.save_selection(value)
    repository.bind_consequence(outcome)
    assert repository.verify_replay()["valid"] is True

    restarted = SelectionRetentionRepository(
        runtime_id="selection-runtime",
        project_scope=value.project_scope,
        workspace_root=tmp_path,
    )
    snapshot = restarted.snapshot()
    assert snapshot.selections == (value,)
    assert snapshot.consequences == (outcome,)
    assert snapshot.as_dict()["retention_write_authority"] is False
    assert restarted.verify_replay()["valid"] is True


def test_selection_retention_components_remain_modular():
    kernel_files = {
        "cognitive_action_models.py": 300,
        "typed_evidence_binding.py": 280,
        "selection_models.py": 230,
        "retention_evidence_models.py": 180,
        "selection_retention_policy.py": 230,
        "selection_retention_models.py": 45,
    }
    forbidden = {"agentos_runtime", "os", "pathlib"}
    for filename, line_limit in kernel_files.items():
        path = CORE_ROOT / "agentos_kernel" / filename
        assert len(path.read_text(encoding="utf-8").splitlines()) <= line_limit
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(
                    alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        assert imports.isdisjoint(forbidden), (filename, imports)

    runtime_limits = {
        "selection_retention_migration.py": 130,
        "selection_retention_repository.py": 220,
    }
    for filename, line_limit in runtime_limits.items():
        path = CORE_ROOT / "agentos_runtime" / filename
        assert len(path.read_text(encoding="utf-8").splitlines()) <= line_limit
