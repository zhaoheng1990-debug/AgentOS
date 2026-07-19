"""Provider-backed cognition policy boundary for AgentOS runtime decisions.

This module defines which runtime operations require model/provider cognition
instead of local string or boolean classification. The Kernel remains the
decision owner: providers supply bounded semantic judgments, while local code
performs schema checks, boundary enforcement, replay, hashing, and rollback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


PROVIDER_COGNITION_LAYER_ID = "provider_backed_runtime_cognition_layer_v0_9"

PROVIDER_REQUIRED = "PROVIDER_REQUIRED"
PROVIDER_OPTIONAL = "PROVIDER_OPTIONAL"
PROVIDER_FORBIDDEN = "PROVIDER_FORBIDDEN"

PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT = "PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT"
PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT = "PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT"
BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING = "BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING"
BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT = "BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT"
PASS_MECHANICAL_RUNTIME_OPERATION = "PASS_MECHANICAL_RUNTIME_OPERATION"
BLOCKED_UNKNOWN_COGNITION_OPERATION = "BLOCKED_UNKNOWN_COGNITION_OPERATION"

SEMANTIC_CONSISTENCY_ASSERTIONS = "semantic_consistency_assertions"
_CONSISTENCY_OPERATORS = {
    "equals",
    "not_equals",
    "in",
    "contains_all",
    "length_equals",
    "greater_than_or_equal",
    "less_than_or_equal",
}


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CognitionOperationContract:
    operation_id: str
    layer: str
    provider_requirement: str
    provider_role: str
    runtime_role: str
    required_provider_outputs: tuple[str, ...]
    fail_closed_behavior: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "layer": self.layer,
            "provider_requirement": self.provider_requirement,
            "provider_role": self.provider_role,
            "runtime_role": self.runtime_role,
            "required_provider_outputs": list(self.required_provider_outputs),
            "fail_closed_behavior": self.fail_closed_behavior,
        }


PROVIDER_REQUIRED_OPERATIONS: tuple[CognitionOperationContract, ...] = (
    CognitionOperationContract(
        "temporal_sro_constraint_field_resolution",
        "kernel",
        PROVIDER_REQUIRED,
        "identify task constraint field, hidden constraints, reuse mode, transfer risk, and candidate operator set",
        "validate schema, record SRO receipt, enforce scope and SafetyKernel boundary",
        ("constraint_field", "hidden_constraints", "reuse_mode", "transfer_risk", "operator_candidates", "confidence"),
        "block_or_candidate_only_no_local_semantic_guess",
    ),
    CognitionOperationContract(
        "graded_sro_retention_candidate_routing",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "estimate calibrated structural-role compatibility, route probabilities, uncertainty, drift, validity, and negative-transfer risk for one witness-task pair",
        "validate frozen calibration and evidence scope, apply safety overrides, distinguish observe from abstain, and own the final project-scoped route",
        (
            "route_probabilities",
            "uncertainty",
            "drift_risk",
            "negative_transfer_risk",
            "structural_compatibility",
            "role_compatibility",
            "boundary_compatibility",
            "interface_compatibility",
            "trace_sufficiency",
            "calibration_error",
            "validity_state",
            "evidence_scope",
            "confidence",
        ),
        "abstain_or_observe_no_unvalidated_retention_reuse",
    ),
    CognitionOperationContract(
        "structural_routing_operator_fiber_ranking",
        "kernel",
        PROVIDER_REQUIRED,
        "rank operator compatibility and explain why each operator applies or does not apply",
        "check registered operators, capability envelopes, forbidden actions, and replayability",
        ("ranked_operator_fiber", "applicability_reason", "non_applicability_reason", "risk_notes", "confidence"),
        "block_route_selection_until_provider_support_receipt",
    ),
    CognitionOperationContract(
        "utility_policy_selection",
        "kernel",
        PROVIDER_REQUIRED,
        "estimate expected utility, Cbit gain, residual risk, and route-interaction anti-additive pressure for candidate routes",
        "apply hard gates, permission policy, rollback requirements, and final decision envelope",
        ("utility_estimate", "cbit_gain_estimate", "risk_estimate", "anti_additive_signal", "selected_policy_candidate"),
        "defer_policy_selection_no_local_best_guess",
    ),
    CognitionOperationContract(
        "memory_retention_candidate_evaluation",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "judge transferability, future Cbit gain, supersession, negative transfer, scope, freshness, and reuse value",
        "write only candidate/project-scoped records when authorized; hash, replay, rollback, and expose review packet",
        ("transferability", "future_cbit_gain", "negative_transfer_risk", "scope", "freshness", "recommended_state"),
        "keep_pending_or_quarantine_without_provider_support_receipt",
    ),
    CognitionOperationContract(
        "operator_memory_functional_equivalence_review",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "compare traces by functional equivalence, failure boundary, output improvement, and reuse conditions",
        "validate evidence refs, candidate state, durable write authorization, and replay evidence",
        ("operator_family", "functional_equivalence", "failure_boundary", "reuse_conditions", "confidence"),
        "block_operator_promotion_or_keep_candidate",
    ),
    CognitionOperationContract(
        "validity_drift_watch_assessment",
        "memory_runtime",
        PROVIDER_REQUIRED,
        "detect stale reuse risk, temporal drift, scope mismatch, contradiction, and revalidation need",
        "enforce validity map, drift watch records, quarantine, revocation, and blocked reuse",
        ("drift_type", "stale_reuse_risk", "scope_mismatch", "revalidation_need", "recommended_action"),
        "quarantine_or_revalidate_no_silent_reuse",
    ),
    CognitionOperationContract(
        "evidence_relevance_and_claim_support",
        "evidence_runtime",
        PROVIDER_REQUIRED,
        "judge whether source passages support the claimed object, dimension, timeframe, and scope",
        "preserve source hashes, citation provenance, freshness policy, and candidate-only state",
        ("supported_claims", "unsupported_claims", "evidence_scope", "freshness", "confidence"),
        "do_not_accept_evidence_without_provider_support_judgment",
    ),
    CognitionOperationContract(
        "plugin_object_event_extraction",
        "plugin_middleware",
        PROVIDER_REQUIRED,
        "extract plugin-defined objects, events, relations, and source-backed fields",
        "dedupe mechanically, validate required fields, retain missing fields, and prevent unsupported promotion",
        ("entities", "events", "entity_type", "source_links", "missing_fields", "confidence"),
        "candidate_only_or_insufficient_materials_report",
    ),
    CognitionOperationContract(
        "plugin_scope_synthesis",
        "plugin_middleware",
        PROVIDER_REQUIRED,
        "synthesize a plugin-owned scope from evidence, contradictions, structure, quantitative signals, and uncertainty",
        "render plugin projection, cite references, mark baseline candidate state, and keep provenance separate from prose",
        ("scope_sections", "key_judgments", "quantitative_tables", "uncertainties", "next_evidence_actions"),
        "insufficient_scope_report_no_template_fallback",
    ),
    CognitionOperationContract(
        "next_iteration_action_selection",
        "automation_middleware",
        PROVIDER_REQUIRED,
        "choose next high-Cbit action, object switch, search dimension, or stop condition from current evidence state",
        "execute only authorized local/harness actions, log action receipts, and enforce rollback",
        ("next_action", "expected_cbit_gain", "stop_condition", "object_switch_candidate", "risk_notes"),
        "stop_or_request_direction_no_local_semantic_guess",
    ),
    CognitionOperationContract(
        "group_hypothesis_generation",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "generate scoped hypotheses, assumptions, rival explanations, and falsifiable predictions from the current problem space",
        "preserve hypothesis plurality, validate scope and evidence refs, and register claim candidates without promotion",
        ("hypotheses", "assumptions", "rival_explanations", "falsifiable_predictions", "evidence_refs", "confidence"),
        "keep_problem_open_no_local_hypothesis_fabrication",
    ),
    CognitionOperationContract(
        "adversarial_epistemic_review",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "identify rival explanations, strongest falsifiers, unsupported inference, and scope violations",
        "enforce reviewer independence, frozen gates, receipt completeness, and final bounded epistemic state",
        ("objections", "strongest_falsifier", "rival_set_coverage", "evidence_refs", "recommended_epistemic_state", "confidence"),
        "keep_claim_pending_until_provider_backed_adversarial_review",
    ),
    CognitionOperationContract(
        "independent_replication_interpretation",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "interpret independent replication evidence against the frozen gate and rival set",
        "verify context independence, gate identity, evidence provenance, and final candidate state",
        ("replication_outcome", "gate_results", "deviations", "evidence_refs", "confidence"),
        "keep_claim_pending_until_independent_replication_interpretation",
    ),
    CognitionOperationContract(
        "group_synthesis_and_conflict_resolution",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "synthesize converged claims while preserving unresolved conflicts, minority positions, and uncertainty",
        "validate cited receipts, retain conflicts, enforce scope, and own the final synthesis candidate state",
        ("converged_claims", "unresolved_conflicts", "minority_positions", "evidence_refs", "uncertainties"),
        "emit_insufficient_synthesis_without_local_conflict_erasure",
    ),
    CognitionOperationContract(
        "cognitive_deliberation_coordination",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "propose the next bounded role action from public receipts, unresolved conflicts, evidence gaps, and expected Cbit gain",
        "validate route prerequisites, evidence scope, role and cycle budgets, information barriers, and final Kernel authority",
        (
            "route_action",
            "target_role",
            "rationale",
            "unresolved_questions",
            "evidence_gaps",
            "conflict_message_refs",
            "evidence_refs",
            "expected_cbit_gain",
            "stop_condition",
        ),
        "block_route_change_or_keep_current_problem_open_without_a_valid_coordination_proposal",
    ),
    CognitionOperationContract(
        "group_outcome_quality_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "assess non-mechanical output quality, exposed errors, corrected errors, candidate survival, and negative transfer signals",
        "validate observation schema and evidence refs, then compute deterministic group metrics against member baselines",
        ("quality_score", "errors_exposed", "errors_corrected", "candidate_survival", "negative_transfer_signals", "evidence_refs"),
        "do_not_claim_group_gain_without_supported_quality_observations",
    ),
    CognitionOperationContract(
        "endogenous_problem_generation",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "derive open problems, residual rivals, candidate questions, expected Cbit gain, scope, and uncertainty from current evidence",
        "register provider-backed agenda candidates, apply risk and priority gates, and own select-or-stop decisions",
        ("open_problems", "residual_rivals", "candidate_questions", "expected_cbit_gain", "scope", "evidence_refs"),
        "keep_existing_problem_space_no_local_question_fabrication",
    ),
    CognitionOperationContract(
        "endogenous_problem_framing",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "derive plural problem candidates from admitted anomalies, unresolved conflicts, rivals, and evidence without a seeded question",
        "validate candidate plurality, scope, identifiers, evidence refs, unit metrics, and candidate-only state",
        ("problem_candidates", "generation_rationale", "coverage_notes", "evidence_refs"),
        "keep_problem_space_open_without_locally_fabricated_questions",
    ),
    CognitionOperationContract(
        "problem_candidate_adversarial_review",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "challenge candidate premises, redundancy, negative-transfer risk, and hidden assumptions",
        "validate candidate references, preserve minority objections, and prevent unsupported candidate removal",
        ("candidate_reviews", "surviving_problem_ids", "minority_objections", "evidence_refs"),
        "keep_all_candidates_pending_without_valid_adversarial_review",
    ),
    CognitionOperationContract(
        "problem_researchability_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "independently assess operationalization, falsifiability, tractability, cost, and required Harness capabilities",
        "validate candidate identity, admitted evidence, metric ranges, and capability declarations",
        ("assessments", "researchable_problem_ids", "missing_capabilities", "evidence_refs"),
        "do_not_promote_unassessed_problem_candidates",
    ),
    CognitionOperationContract(
        "group_agenda_synthesis_and_selection",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "select or stop from candidates that survive criticism and independent researchability assessment while preserving conflicts",
        "validate set intersection, priority floor, evidence refs, pending-only seed state, and Kernel final selection authority",
        (
            "decision",
            "selected_problem_id",
            "selection_rationale",
            "rejected_problem_ids",
            "unresolved_conflicts",
            "evidence_refs",
            "expected_cbit_gain",
            "stop_condition",
        ),
        "emit_no_agenda_candidate_without_local_semantic_substitution",
    ),
    CognitionOperationContract(
        "problem_quality_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "judge the prospective quality of one blinded problem candidate across evidence grounding, premise soundness, novelty, falsifiability, discriminatory power, feasibility, expected Cbit, cost, and negative-transfer risk",
        "validate candidate identity, scope, evidence admission, score ranges, and provider provenance; compute deterministic comparisons without trial authority",
        (
            "candidate_id",
            "scope",
            "evidence_grounding",
            "premise_soundness",
            "novelty",
            "falsifiability",
            "discriminatory_power",
            "harness_feasibility",
            "expected_cbit_gain",
            "normalized_cost",
            "negative_transfer_risk",
            "assessment_rationale",
            "evidence_refs",
        ),
        "keep_problem_pending_without_provider_backed_quality_observation",
    ),
    CognitionOperationContract(
        "problem_trial_outcome_interpretation",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "interpret independent Harness trial evidence, rival reduction, observed Cbit, residual problems, cost, and negative-transfer signals",
        "validate trial authorization, Harness receipts, evidence refs, outcome consistency, and terminal candidate state; retain Kernel adjudication authority",
        (
            "trial_resolution",
            "observed_cbit_gain",
            "rival_explanations_reduced",
            "problem_survived",
            "residual_problems",
            "normalized_cost",
            "negative_transfer_signal",
            "independent_replication",
            "interpretation",
            "evidence_refs",
        ),
        "keep_trial_active_or_blocked_without_provider_backed_outcome_interpretation",
    ),
    CognitionOperationContract(
        "independent_problem_baseline_generation",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "generate one falsifiable problem candidate from admitted evidence in an isolated agent context without seeing peer or group candidates",
        "verify agent/provider binding, identical input surface, scope, evidence refs, context isolation, and candidate-only state",
        (
            "problem_id",
            "question",
            "research_object",
            "scope",
            "triggering_anomaly",
            "rival_explanations",
            "falsifier",
            "required_harnesses",
            "expected_cbit_gain",
            "evidence_refs",
        ),
        "keep_member_baseline_missing_without_independent_provider_backed_candidate",
    ),
    CognitionOperationContract(
        "cognitive_team_formation_proposal",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "propose a bounded team from registered agents using problem requirements, independence, capability, cost, and advisory credit signals",
        "validate registered identities, role coverage, capabilities, scope, context and provider diversity, budget, and Kernel activation authority",
        (
            "selected_agent_ids",
            "role_coverage",
            "formation_rationale",
            "expected_cbit_gain",
            "independence_risks",
            "negative_transfer_risks",
            "evidence_refs",
        ),
        "keep_team_unformed_without_valid_provider_backed_proposal",
    ),
    CognitionOperationContract(
        "team_trial_semantic_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "assess one counterfactual team arm over admitted Harness evidence using the frozen trial protocol",
        "validate arm identity, equal evidence and budget, Harness receipt, metric bounds, and no route-selection authority",
        (
            "blind_arm_id",
            "quality_score",
            "observed_cbit_gain",
            "errors_exposed",
            "errors_corrected",
            "negative_transfer_opportunities",
            "negative_transfer_intercepts",
            "normalized_cost",
            "convergence_steps",
            "evidence_refs",
        ),
        "do_not_compare_team_arms_without_provider_backed_semantic_observations",
    ),
    CognitionOperationContract(
        "solo_cognitive_trial",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "independently answer a frozen cognitive trial and classify every public finding while preserving rejection and uncertainty",
        "verify the authorized agent binding, exact finding coverage, admitted evidence, budget, hidden-truth isolation, and candidate-only authority",
        (
            "answer",
            "supported_finding_ids",
            "rejected_finding_ids",
            "unresolved_finding_ids",
            "rival_explanations",
            "falsifier",
            "evidence_refs",
            "uncertainties",
        ),
        "block_the_independent_arm_without_a_complete_provider_backed_candidate",
    ),
    CognitionOperationContract(
        "team_trial_output_normalization",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "normalize formal multi-role execution receipts into one bounded trial candidate without erasing conflict or uncertainty",
        "verify the authorized synthesizer binding, formal receipt provenance, exact finding coverage, admitted evidence, budget, and candidate-only authority",
        (
            "answer",
            "supported_finding_ids",
            "rejected_finding_ids",
            "unresolved_finding_ids",
            "rival_explanations",
            "falsifier",
            "evidence_refs",
            "uncertainties",
        ),
        "block_the_team_arm_without_a_complete_provider_backed_normalized_candidate",
    ),
    CognitionOperationContract(
        "problem_structure_dimension_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "assess the evidence-bound problem constraint field across premise uncertainty, evidence conflict, replication, synthesis, coordination, and novelty dimensions",
        "validate source seed and isolated role receipts, evidence and signal bindings, uncertainty ceilings, revision ancestry, replay, and retain final Kernel admission authority",
        (
            "candidate_hash",
            "dimension_assessments",
            "global_uncertainty",
            "evidence_refs",
        ),
        "keep_the_problem_structure_pending_without_complete_provider_supported_dimensions",
    ),
    CognitionOperationContract(
        "anti_additive_methodology_assessment",
        "kernel_meta_governance",
        PROVIDER_REQUIRED,
        "judge object adequacy, all seven patch-accumulation triggers, effective Cbit gain, complexity cost, object-upgrade gain, abstraction cost, and uncertainty",
        "freeze the candidate and evidence surface, compare gains against costs, choose the bounded methodology state, persist replay, and retain all write authority",
        (
            "current_object_adequacy",
            "trigger_assessments",
            "expected_effective_cbit_gain",
            "complexity_cost",
            "object_upgrade_gain",
            "abstraction_cost",
            "uncertainty",
            "recommended_action",
            "rationale",
            "evidence_refs",
        ),
        "block_candidate_write_without_provider_supported_first_principles_audit",
    ),
    CognitionOperationContract(
        "contextual_organization_policy_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "assess the structural fit, expected Cbit, bounded cost, residual risk, uncertainty, and organization-interaction anti-additive pressure of each registered organization policy for one bound problem",
        "validate exact policy coverage, problem and evidence binding, matched-evidence provenance, budget and risk gates, registry feasibility, and retain final Kernel selection authority",
        (
            "recommended_policy_id",
            "policy_assessments",
            "global_uncertainty",
            "evidence_refs",
        ),
        "abstain_from_contextual_role_selection_without_complete_provider_supported_assessment",
    ),
    CognitionOperationContract(
        "selector_calibration_drift_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "diagnose semantic scope, evidence, model, Harness, Cbit, cost, and residual-risk drift over one exact Selector calibration profile",
        "freeze prediction/outcome bindings, calculate metrics, isolate project/context/evidence-tier/policy profiles, enforce thresholds and lineage, and retain final Kernel calibration state",
        (
            "diagnostic_state",
            "drift_drivers",
            "recommended_action",
            "uncertainty",
            "rationale",
            "evidence_refs",
        ),
        "keep_selector_calibration_pending_without_provider_diagnosis",
    ),
    CognitionOperationContract(
        "cognitive_organization_failure_diagnosis",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "interpret bounded organization failure modes, component hypotheses, coordination cost, and next experiment candidates from admitted trial evidence",
        "compute matched-ablation identifiability and repeated protocol metrics, reject unsupported causality and unknown variants, preserve advisory credit, and own policy candidate state",
        (
            "failure_modes",
            "component_hypotheses",
            "coordination_cost_assessment",
            "next_experiment_variants",
            "confidence",
            "evidence_refs",
        ),
        "keep_the_organization_policy_open_without_a_bounded_provider_supported_diagnosis",
    ),
    CognitionOperationContract(
        "knowledge_invalidation_root_assessment",
        "cognitive_ensemble_runtime",
        PROVIDER_REQUIRED,
        "identify which claims or semantic receipts are invalidated, contradicted, stale, or require revalidation",
        "validate adjudication refs and apply deterministic dependency propagation, quarantine, and reuse blocking",
        ("invalidation_roots", "adjudication_basis", "affected_scope", "revalidation_need", "evidence_refs"),
        "quarantine_candidate_roots_without_local_semantic_invalidation_guess",
    ),
)

MECHANICAL_RUNTIME_OPERATIONS: tuple[CognitionOperationContract, ...] = (
    CognitionOperationContract(
        "anti_additive_methodology_kernel_gate",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "verify candidate and receipt bindings, compare effective Cbit against complexity and object-upgrade gain against abstraction cost, and enforce the final methodology state",
        (),
        "block_patch_accumulation_or_require_object_upgrade",
    ),
    CognitionOperationContract(
        "schema_validation",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "validate JSON schemas, required fields, types, and enum membership",
        (),
        "fail_schema_validation",
    ),
    CognitionOperationContract(
        "hash_replay_rollback",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "compute hashes, replay receipts, rollback local writes, and verify absence checks",
        (),
        "fail_replay_or_rollback",
    ),
    CognitionOperationContract(
        "capability_permission_boundary",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "enforce capability envelopes, allowed paths, forbidden actions, and SafetyKernel hard stops",
        (),
        "block_forbidden_action",
    ),
    CognitionOperationContract(
        "artifact_packaging_manifest",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "package artifacts, generate manifests, and inventory hashes",
        (),
        "fail_packaging",
    ),
    CognitionOperationContract(
        "agent_registry_context_isolation",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "register declared agent bindings and enforce distinct agent, context, capability, and optional provider constraints",
        (),
        "reject_non_isolated_or_unregistered_team",
    ),
    CognitionOperationContract(
        "group_metric_calculation",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "compute group delta, correction rate, survival rate, diversity, convergence, and negative-transfer interception from admitted observations",
        (),
        "fail_invalid_group_observation",
    ),
    CognitionOperationContract(
        "epistemic_credit_ledger_projection",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "append adjudicated credit events and compute bounded advisory profiles without route-selection authority",
        (),
        "reject_unadjudicated_credit_event",
    ),
    CognitionOperationContract(
        "dependency_invalidation_propagation",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "propagate admitted invalidation roots through registered hard and quarantine dependency edges",
        (),
        "block_reuse_for_invalidated_or_quarantined_nodes",
    ),
    CognitionOperationContract(
        "contextual_organization_policy_kernel_selection",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "apply exact-context matched-evidence, role-structure, budget, risk, registry feasibility, and authorization gates to Provider-supported policy assessments",
        (),
        "abstain_when_no_registered_policy_passes_kernel_gates",
    ),
    CognitionOperationContract(
        "organization_matched_ablation_and_protocol_calibration",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "pair organization ablations within one context, evidence tier, and trial group; compute component effects and repeated protocol statistics",
        (),
        "withhold_component_causality_or_protocol_selection_when_matched_evidence_is_insufficient",
    ),
    CognitionOperationContract(
        "selector_prediction_outcome_calibration",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "bind selected-policy predictions to admitted Harness outcomes and calculate exact-scope error, bias, coverage, and independent-source statistics",
        (),
        "reject_unbound_cross_scope_or_duplicate_calibration_observation",
    ),
    CognitionOperationContract(
        "contextual_selector_calibration_control",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "consume replay-valid latest calibration receipts and apply exact-scope exploration downgrade, trusted authorization eligibility, or drift blocking",
        (),
        "reject_missing_stale_cross_scope_or_internally_inconsistent_calibration_control",
    ),
    CognitionOperationContract(
        "anti_additive_prediction_outcome_calibration",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "bind methodology predictions to admitted Harness outcomes and calculate exact project, change-kind, and target-type error and margin-survival profiles",
        (),
        "reject_unbound_cross_scope_duplicate_or_nonexecuted_calibration_observation",
    ),
    CognitionOperationContract(
        "anti_additive_receipt_authority_resolution",
        "runtime_mechanical",
        PROVIDER_FORBIDDEN,
        "none",
        "verify source replay and latest receipt identity, enforce exact candidate payload and target binding, and distinguish candidate-only from durable-project-write authority",
        (),
        "reject_stale_unbound_or_insufficient_authority_receipt",
    ),
)


class ProviderBackedRuntimeCognitionLayer:
    """Kernel-owned policy boundary for provider-supported cognition."""

    layer_id = PROVIDER_COGNITION_LAYER_ID
    final_decision_owner = "AgentOSKernel"
    provider_final_decision_owner = False

    def __init__(self) -> None:
        contracts = PROVIDER_REQUIRED_OPERATIONS + MECHANICAL_RUNTIME_OPERATIONS
        self._contracts = {contract.operation_id: contract for contract in contracts}

    def contract(self) -> dict[str, Any]:
        provider_required = [item.as_dict() for item in PROVIDER_REQUIRED_OPERATIONS]
        mechanical = [item.as_dict() for item in MECHANICAL_RUNTIME_OPERATIONS]
        payload = {
            "layer_id": self.layer_id,
            "purpose": "route provider-supported semantic work while preserving kernel-owned cognition, final decision, and mechanical runtime enforcement",
            "provider_final_decision_owner": False,
            "final_decision_owner": self.final_decision_owner,
            "provider_required_operations": provider_required,
            "mechanical_runtime_operations": mechanical,
            "invariant": "runtime_remains_cognitive_subject; provider_supports_bounded_semantic_work; local_runtime_code_owns_validation_enforcement_recording_replay_and_final_candidate_state",
        }
        payload["contract_hash"] = _hash_payload(payload)
        return payload

    def operation_contract(self, operation_id: str) -> dict[str, Any]:
        contract = self._contracts.get(operation_id)
        if not contract:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_UNKNOWN_COGNITION_OPERATION,
                "reason": "operation_not_registered_in_provider_cognition_layer",
            }
        return contract.as_dict()

    def audit_operation(self, operation_id: str, runtime_record: dict[str, Any]) -> dict[str, Any]:
        contract = self._contracts.get(operation_id)
        if not contract:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_UNKNOWN_COGNITION_OPERATION,
                "provider_required": None,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        if contract.provider_requirement == PROVIDER_FORBIDDEN:
            return {
                "operation_id": operation_id,
                "status": PASS_MECHANICAL_RUNTIME_OPERATION,
                "provider_required": False,
                "runtime_cognitive_owner": self.final_decision_owner,
                "provider_support_role": "forbidden_for_deterministic_runtime_boundary",
                "runtime_role": contract.runtime_role,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        support_receipt = runtime_record.get("provider_support_receipt")
        missing_outputs = self._missing_provider_outputs(contract, support_receipt)
        if missing_outputs:
            return {
                "operation_id": operation_id,
                "status": BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
                "provider_required": True,
                "runtime_cognitive_owner": self.final_decision_owner,
                "provider_support_role": "semantic_support_required",
                "missing_provider_outputs": missing_outputs,
                "fail_closed_behavior": contract.fail_closed_behavior,
                "runtime_record_hash": _hash_payload(runtime_record),
            }

        receipt_hash = runtime_record.get("provider_support_receipt_hash") or _hash_payload(support_receipt)
        assertions = runtime_record.get(SEMANTIC_CONSISTENCY_ASSERTIONS, ())
        if assertions:
            consistency = self._audit_consistency_assertions(support_receipt, assertions)
            if consistency["failed_count"]:
                return {
                    "operation_id": operation_id,
                    "status": BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
                    "provider_required": True,
                    "runtime_cognitive_owner": self.final_decision_owner,
                    "provider_support_role": "semantic_support_conflicted",
                    "runtime_role": contract.runtime_role,
                    "provider_support_receipt_hash": receipt_hash,
                    "semantic_consistency": consistency,
                    "fail_closed_behavior": contract.fail_closed_behavior,
                    "runtime_record_hash": _hash_payload(runtime_record),
                }
            return {
                "operation_id": operation_id,
                "status": PASS_PROVIDER_SUPPORT_RECEIPT_CONSISTENT,
                "provider_required": True,
                "runtime_cognitive_owner": self.final_decision_owner,
                "provider_support_role": "semantic_support_consistent",
                "runtime_role": contract.runtime_role,
                "provider_support_receipt_hash": receipt_hash,
                "semantic_consistency": consistency,
                "runtime_record_hash": _hash_payload(runtime_record),
            }
        return {
            "operation_id": operation_id,
            "status": PASS_PROVIDER_SUPPORT_RECEIPT_PRESENT,
            "provider_required": True,
            "runtime_cognitive_owner": self.final_decision_owner,
            "provider_support_role": "semantic_support_present",
            "runtime_role": contract.runtime_role,
            "provider_support_receipt_hash": receipt_hash,
            "runtime_record_hash": _hash_payload(runtime_record),
        }

    def audit_pipeline(self, operation_records: list[dict[str, Any]]) -> dict[str, Any]:
        audits = [self.audit_operation(item.get("operation_id", ""), item) for item in operation_records]
        hard_blocks = [
            item
            for item in audits
            if item["status"]
            in {
                BLOCKED_PROVIDER_SUPPORT_RECEIPT_MISSING,
                BLOCKED_PROVIDER_SUPPORT_RECEIPT_INCONSISTENT,
                BLOCKED_UNKNOWN_COGNITION_OPERATION,
            }
        ]
        return {
            "layer_id": self.layer_id,
            "status": "BLOCKED" if hard_blocks else "PASS",
            "operation_count": len(audits),
            "blocked_count": len(hard_blocks),
            "audits": audits,
            "pipeline_hash": _hash_payload(audits),
        }

    @staticmethod
    def _missing_provider_outputs(contract: CognitionOperationContract, judgment: Any) -> list[str]:
        if not isinstance(judgment, dict):
            return list(contract.required_provider_outputs)
        return [field for field in contract.required_provider_outputs if field not in judgment]

    @classmethod
    def _audit_consistency_assertions(cls, receipt: dict[str, Any], assertions: Any) -> dict[str, Any]:
        if not isinstance(assertions, (list, tuple)):
            assertions = (assertions,)
        results = [cls._evaluate_consistency_assertion(receipt, assertion, index) for index, assertion in enumerate(assertions)]
        failures = [result for result in results if not result["passed"]]
        payload = {
            "assertion_count": len(results),
            "passed_count": len(results) - len(failures),
            "failed_count": len(failures),
            "results": results,
        }
        payload["assertions_hash"] = _hash_payload(assertions)
        return payload

    @classmethod
    def _evaluate_consistency_assertion(
        cls,
        receipt: dict[str, Any],
        assertion: Any,
        index: int,
    ) -> dict[str, Any]:
        if not isinstance(assertion, dict):
            return {
                "assertion_id": f"assertion-{index}",
                "passed": False,
                "reason": "assertion_must_be_object",
            }
        assertion_id = str(assertion.get("assertion_id") or f"assertion-{index}")
        path = assertion.get("path")
        operator = assertion.get("operator")
        expected = assertion.get("expected")
        evidence_refs = assertion.get("evidence_refs", [])
        base = {
            "assertion_id": assertion_id,
            "path": path,
            "operator": operator,
            "expected": expected,
            "evidence_refs": list(evidence_refs) if isinstance(evidence_refs, (list, tuple)) else [],
        }
        if not isinstance(path, str) or not path:
            return {**base, "passed": False, "reason": "assertion_path_required"}
        if operator not in _CONSISTENCY_OPERATORS:
            return {**base, "passed": False, "reason": "assertion_operator_unsupported"}
        found, observed = cls._resolve_json_path(receipt, path)
        if not found:
            return {**base, "passed": False, "reason": "assertion_path_missing"}
        try:
            passed = cls._compare_consistency_value(observed, operator, expected)
        except (TypeError, ValueError):
            return {
                **base,
                "observed": observed,
                "passed": False,
                "reason": "assertion_comparison_type_error",
            }
        return {
            **base,
            "observed": observed,
            "passed": passed,
            "reason": "assertion_satisfied" if passed else "assertion_value_mismatch",
        }

    @staticmethod
    def _resolve_json_path(payload: dict[str, Any], path: str) -> tuple[bool, Any]:
        current: Any = payload
        for segment in path.split("."):
            if not isinstance(current, dict) or segment not in current:
                return False, None
            current = current[segment]
        return True, current

    @staticmethod
    def _compare_consistency_value(observed: Any, operator: str, expected: Any) -> bool:
        if operator == "equals":
            return observed == expected and type(observed) is type(expected)
        if operator == "not_equals":
            return observed != expected or type(observed) is not type(expected)
        if operator == "in":
            return observed in expected
        if operator == "contains_all":
            return isinstance(observed, (list, tuple, set)) and all(item in observed for item in expected)
        if operator == "length_equals":
            return len(observed) == expected
        if operator == "greater_than_or_equal":
            return not isinstance(observed, bool) and observed >= expected
        if operator == "less_than_or_equal":
            return not isinstance(observed, bool) and observed <= expected
        raise ValueError(f"unsupported_consistency_operator:{operator}")
