"""Kernel-owned gates and ranking for contextual organization policies."""

from __future__ import annotations

import re
from typing import Any

from .contextual_policy_models import (
    CONTEXTUAL_POLICY_IDS,
    ContextualOrganizationPolicyDecision,
    ContextualPolicyCandidateEvaluation,
    ContextualProblemStructure,
    ContextualProviderPolicyAssessment,
    ContextualRolePolicy,
    MatchedPolicyEvidence,
    OrganizationBudgetEnvelope,
    OrganizationRiskEnvelope,
    hash_payload,
)


class ContextualOrganizationPolicySelector:
    """Select one bounded role policy while retaining final Kernel authority."""

    def __init__(self, *, structural_role_threshold: float = 0.60, adverse_delta: float = -0.02) -> None:
        if not 0.0 <= float(structural_role_threshold) <= 1.0:
            raise ValueError("contextual_policy_structural_role_threshold_invalid")
        if not -1.0 <= float(adverse_delta) <= 0.0:
            raise ValueError("contextual_policy_adverse_delta_invalid")
        self.structural_role_threshold = float(structural_role_threshold)
        self.adverse_delta = float(adverse_delta)

    def select(
        self,
        *,
        decision_id: str,
        problem: ContextualProblemStructure,
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        policies: tuple[ContextualRolePolicy, ...],
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        provider_assessments: tuple[ContextualProviderPolicyAssessment, ...],
        provider_advice_hash: str,
        feasible_policy_ids: tuple[str, ...],
        kernel_authorization_ref: str,
    ) -> ContextualOrganizationPolicyDecision:
        self._validate_inputs(
            decision_id,
            policies,
            matched_evidence,
            provider_assessments,
            provider_advice_hash,
            feasible_policy_ids,
            kernel_authorization_ref,
        )
        required_roles = self.required_roles(problem)
        evidence_by_policy = {item.policy_id: item for item in matched_evidence}
        assessment_by_policy = {item.policy_id: item for item in provider_assessments}
        evaluations = tuple(
            self._evaluate_candidate(
                policy,
                evidence_by_policy[policy.policy_id],
                assessment_by_policy[policy.policy_id],
                required_roles,
                budget,
                risk,
                feasible_policy_ids,
            )
            for policy in policies
        )
        eligible = [item for item in evaluations if item.eligibility != "BLOCKED"]
        selected = max(eligible, key=lambda item: item.rank_vector) if eligible else None
        activation_mode = self._activation_mode(selected)
        evidence_refs = self._evidence_refs(problem, matched_evidence, provider_assessments)
        return self._decision(
            decision_id=decision_id,
            selected=selected,
            activation_mode=activation_mode,
            kernel_authorization_ref=kernel_authorization_ref,
            required_roles=required_roles,
            evaluations=evaluations,
            problem=problem,
            budget=budget,
            risk=risk,
            provider_advice_hash=provider_advice_hash,
            evidence_refs=evidence_refs,
        )

    def required_roles(self, problem: ContextualProblemStructure) -> tuple[str, ...]:
        roles = ["HYPOTHESIS_GENERATOR"]
        threshold = self.structural_role_threshold
        if problem.premise_uncertainty >= threshold:
            roles.append("ADVERSARIAL_REVIEWER")
        if problem.replication_need >= threshold:
            roles.append("REPLICATOR")
        if max(problem.evidence_conflict, problem.synthesis_need) >= threshold:
            roles.append("SYNTHESIZER")
        if problem.coordination_complexity >= threshold:
            roles.append("COORDINATOR")
        return tuple(roles)

    def _evaluate_candidate(
        self,
        policy: ContextualRolePolicy,
        evidence: MatchedPolicyEvidence,
        assessment: ContextualProviderPolicyAssessment,
        required_roles: tuple[str, ...],
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        feasible_policy_ids: tuple[str, ...],
    ) -> ContextualPolicyCandidateEvaluation:
        failures = []
        if policy.policy_id not in feasible_policy_ids:
            failures.append("no_context_isolated_registered_assignment")
        if not set(required_roles).issubset(policy.roles):
            failures.append("problem_required_role_missing")
        if len(policy.roles) > budget.max_roles:
            failures.append("role_budget_exceeded")
        if policy.provider_call_ceiling > budget.max_provider_calls:
            failures.append("provider_call_budget_exceeded")
        if policy.coordination_step_ceiling > budget.max_coordination_steps:
            failures.append("coordination_step_budget_exceeded")
        observed_cost = max(
            assessment.estimated_normalized_cost,
            evidence.mean_normalized_cost or 0.0,
        )
        if observed_cost > budget.max_normalized_cost:
            failures.append("normalized_cost_budget_exceeded")
        if assessment.residual_risk > risk.max_residual_risk:
            failures.append("residual_risk_ceiling_exceeded")
        if assessment.uncertainty > risk.max_provider_uncertainty:
            failures.append("provider_uncertainty_ceiling_exceeded")
        if assessment.anti_additive_signal > risk.max_anti_additive_signal:
            failures.append("anti_additive_signal_ceiling_exceeded")
        if (
            assessment.residual_risk >= risk.matched_evidence_required_above_risk
            and not evidence.sufficient_matched_evidence
        ):
            failures.append("matched_evidence_required_for_risk_level")
        if evidence.sufficient_matched_evidence and risk.block_adverse_matched_evidence:
            if self._matched_evidence_adverse(evidence):
                failures.append("adverse_matched_evidence")
        if not evidence.sufficient_matched_evidence:
            if not risk.allow_unmatched_exploration:
                failures.append("unmatched_exploration_forbidden")
            if len(policy.roles) > risk.exploration_max_roles:
                failures.append("exploration_role_ceiling_exceeded")
        eligibility = (
            "BLOCKED"
            if failures
            else "AUTHORIZED_ELIGIBLE"
            if evidence.sufficient_matched_evidence
            else "EXPLORATION_ELIGIBLE"
        )
        return ContextualPolicyCandidateEvaluation(
            policy_id=policy.policy_id,
            roles=policy.roles,
            eligibility=eligibility,
            hard_gate_failures=tuple(failures),
            rank_vector=self._rank_vector(policy, evidence, assessment, eligibility, observed_cost),
            matched_evidence_hash=evidence.evidence_hash,
            provider_assessment=assessment,
        )

    @staticmethod
    def _rank_vector(
        policy: ContextualRolePolicy,
        evidence: MatchedPolicyEvidence,
        assessment: ContextualProviderPolicyAssessment,
        eligibility: str,
        observed_cost: float,
    ) -> tuple[float, ...]:
        return (
            1.0 if eligibility == "AUTHORIZED_ELIGIBLE" else 0.0,
            assessment.structure_fit,
            evidence.mean_effectiveness if evidence.mean_effectiveness is not None else -1.0,
            evidence.mean_observed_cbit if evidence.mean_observed_cbit is not None else -1.0,
            assessment.expected_cbit_gain,
            1.0 - max(assessment.residual_risk, assessment.anti_additive_signal, assessment.uncertainty),
            1.0 - observed_cost,
            -float(len(policy.roles)),
        )

    def _matched_evidence_adverse(self, evidence: MatchedPolicyEvidence) -> bool:
        effectiveness = evidence.mean_effectiveness_delta
        cbit = evidence.mean_cbit_delta
        return (
            effectiveness is not None
            and effectiveness < self.adverse_delta
        ) or (cbit is not None and cbit < self.adverse_delta)

    @staticmethod
    def _activation_mode(selected: ContextualPolicyCandidateEvaluation | None) -> str:
        if selected is None:
            return "ABSTAIN"
        if selected.eligibility == "AUTHORIZED_ELIGIBLE":
            return "AUTHORIZED_PROJECT_SCOPED"
        return "EXPLORATORY_TRIAL_ONLY"

    @staticmethod
    def _evidence_refs(
        problem: ContextualProblemStructure,
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        provider_assessments: tuple[ContextualProviderPolicyAssessment, ...],
    ) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                (
                    *problem.evidence_refs,
                    *(ref for item in matched_evidence for ref in item.evidence_refs),
                    *(ref for item in provider_assessments for ref in item.evidence_refs),
                )
            )
        )

    @staticmethod
    def _decision(
        *,
        decision_id: str,
        selected: ContextualPolicyCandidateEvaluation | None,
        activation_mode: str,
        kernel_authorization_ref: str,
        required_roles: tuple[str, ...],
        evaluations: tuple[ContextualPolicyCandidateEvaluation, ...],
        problem: ContextualProblemStructure,
        budget: OrganizationBudgetEnvelope,
        risk: OrganizationRiskEnvelope,
        provider_advice_hash: str,
        evidence_refs: tuple[str, ...],
    ) -> ContextualOrganizationPolicyDecision:
        committed = {
            "decision_id": decision_id,
            "selected_policy_id": selected.policy_id if selected else "",
            "selected_roles": list(selected.roles) if selected else [],
            "activation_mode": activation_mode,
            "execution_authorized": activation_mode == "AUTHORIZED_PROJECT_SCOPED",
            "trial_authorized": activation_mode != "ABSTAIN",
            "kernel_authorization_ref": kernel_authorization_ref,
            "required_roles": list(required_roles),
            "candidate_evaluations": [item.as_dict() for item in evaluations],
            "reason": (
                "contextual_policy_passed_kernel_gates"
                if selected
                else "no_contextual_policy_passed_kernel_gates"
            ),
            "problem_structure_hash": problem.as_dict()["problem_structure_hash"],
            "budget_hash": budget.as_dict()["budget_hash"],
            "risk_hash": risk.as_dict()["risk_hash"],
            "provider_advice_hash": provider_advice_hash,
            "evidence_refs": list(evidence_refs),
        }
        return ContextualOrganizationPolicyDecision(
            decision_id=decision_id,
            selected_policy_id=committed["selected_policy_id"],
            selected_roles=tuple(committed["selected_roles"]),
            activation_mode=activation_mode,
            execution_authorized=committed["execution_authorized"],
            trial_authorized=committed["trial_authorized"],
            kernel_authorization_ref=kernel_authorization_ref,
            required_roles=required_roles,
            candidate_evaluations=evaluations,
            reason=committed["reason"],
            problem_structure_hash=committed["problem_structure_hash"],
            budget_hash=committed["budget_hash"],
            risk_hash=committed["risk_hash"],
            provider_advice_hash=provider_advice_hash,
            evidence_refs=evidence_refs,
            decision_hash=hash_payload(committed),
        )

    @staticmethod
    def _validate_inputs(
        decision_id: str,
        policies: tuple[ContextualRolePolicy, ...],
        matched_evidence: tuple[MatchedPolicyEvidence, ...],
        provider_assessments: tuple[ContextualProviderPolicyAssessment, ...],
        provider_advice_hash: str,
        feasible_policy_ids: tuple[str, ...],
        kernel_authorization_ref: str,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", decision_id):
            raise ValueError("contextual_policy_decision_id_invalid")
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("contextual_policy_kernel_authorization_required")
        if not re.fullmatch(r"[0-9a-f]{64}", provider_advice_hash):
            raise ValueError("contextual_policy_provider_advice_hash_invalid")
        expected = set(CONTEXTUAL_POLICY_IDS)
        for name, values in (
            ("catalog", tuple(item.policy_id for item in policies)),
            ("matched_evidence", tuple(item.policy_id for item in matched_evidence)),
            ("provider_assessments", tuple(item.policy_id for item in provider_assessments)),
        ):
            if len(values) != len(set(values)) or set(values) != expected:
                raise ValueError(f"contextual_policy_{name}_coverage_invalid")
        if not set(feasible_policy_ids).issubset(expected):
            raise ValueError("contextual_policy_feasible_set_invalid")
