"""Protocol v0.16: opportunity-gated single-expression case adjudication."""

from __future__ import annotations

from .holdout_v14_benchmark import (
    HOLDOUT_V14_BENCHMARK_ID, HOLDOUT_V14_ITEM_DOMAINS, HOLDOUT_V14_ITEM_FINGERPRINTS,
    HOLDOUT_V14_ROUTING_FINGERPRINTS,
)
from .single_expression_case_runtime import SingleExpressionCaseRuntime
from .structural_operator_policy import StructuralOperatorDecision
from .verified_case_policy import VerifiedCaseAdjudicationPolicy
from .verified_case_protocol import VerifiedCaseAdjudicationProtocol


SINGLE_EXPRESSION_PROTOCOL_VERSION = "single_expression_opportunity_protocol_v0_16"


class SingleExpressionAdjudicationProtocol(VerifiedCaseAdjudicationProtocol):
    def __init__(
        self, *, base, profiles, operator_credit_snapshot, operator_schedule,
        resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, **values,
    ) -> None:
        values["policy"] = values.get("policy") or VerifiedCaseAdjudicationPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V14_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=SingleExpressionCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V14_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V14_BENCHMARK_ID,
            case_protocol_version=SINGLE_EXPRESSION_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V14_ITEM_DOMAINS, item_contexts=HOLDOUT_V14_ITEM_FINGERPRINTS,
            arm_namespace="HOLDOUT_V14", **values,
        )
        self._opportunity_gate_passed = False

    def _pre_route_audit(self, experiment_id, proposal_by_model):
        pairs = []
        for item_id in self.base.item_ids:
            domain, context = self.item_domains[item_id], self.item_contexts[item_id]
            plans = self._plans(domain, context)
            primary_plan = self.policy.select_primary(plans)
            primary_run = self.base.slice_item_run(proposal_by_model[primary_plan.model_id], item_id)
            primary = self._signal(primary_run, item_id, domain, context)
            decision = self.policy.route(
                primary, plans=plans, domain=domain, reviewer_ledger=self.reviewer_ledger,
            )
            if decision.action != "VERIFY_PEER":
                continue
            peer_run = self.base.slice_item_run(proposal_by_model[decision.reviewer_model_id], item_id)
            peer = self._signal(peer_run, item_id, domain, context)
            pairs.append({
                "item_id": item_id, "primary_model_id": primary.model_id,
                "peer_model_id": peer.model_id, "primary_answer": primary.answer,
                "peer_answer": peer.answer,
            })
        receipt = self.base.harness.audit_argument_opportunities(
            experiment_id=experiment_id + "-opportunity", pairs=tuple(pairs),
        )
        self._opportunity_gate_passed = receipt.gate_passed
        return receipt

    def _resolve_post_disagreement(self, **values):
        if self._opportunity_gate_passed:
            return super()._resolve_post_disagreement(**values)
        decision, primary = values["decision"], values["primary_signal"]
        kept = StructuralOperatorDecision(**{
            **decision.__dict__, "action": "PRIMARY_KEEP_RESOLVED",
            "final_answer": primary.answer, "reason": "opportunity_gate_blocks_uninformative_case_work",
            "resolution_policy": "OPPORTUNITY_GATE_KEEP",
            "resolution_evidence_level": "AGGREGATE_OPPORTUNITY_GATE",
        })
        return kept, ()

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": SINGLE_EXPRESSION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V14_BENCHMARK_ID,
            "v15_outcomes_used_as_diagnostic_prior": True,
            "v15_experimental_fingerprints_written_to_stable_history": False,
            "v16_outcomes_used_for_current_route": False,
            "single_expression_provider_contract": True,
            "harness_derives_replay_result": True,
            "opportunity_gate_item_identity_disclosed": False,
            "opportunity_gate_has_routing_authority": False,
        })
        report["single_expression_adjudication_arm"] = report.pop("verified_case_adjudication_arm")
        gate = report["pre_route_audit"]
        report["comparisons"].update({
            "opportunity_gate_passed": gate["gate_passed"],
            "scheduled_pair_opportunities": gate["scheduled_pairs"],
            "peer_correction_opportunities": gate["peer_correction_opportunities"],
            "peer_harm_opportunities_pre_route": gate["peer_harm_opportunities"],
            "opportunity_gate_keeps": sum(
                item["resolution_policy"] == "OPPORTUNITY_GATE_KEEP"
                for item in report["route_decisions"]
            ),
        })
        if not gate["gate_passed"]:
            report["comparisons"]["single_expression_improvement_status"] = (
                "NOT_ESTIMABLE_NO_PRE_ROUTE_CORRECTION_OPPORTUNITY"
            )
        else:
            report["comparisons"]["single_expression_improvement_status"] = report[
                "comparisons"
            ].pop("verified_case_improvement_status")
        return report
