"""Protocol v0.17: opportunity-gated, replay-verified candidate belief revision."""

from __future__ import annotations

from .candidate_revision_case_runtime import CandidateRevisionCaseRuntime
from .candidate_revision_policy import CandidateRevisionPolicy
from .holdout_v15_benchmark import (
    HOLDOUT_V15_BENCHMARK_ID, HOLDOUT_V15_ITEM_DOMAINS, HOLDOUT_V15_ITEM_FINGERPRINTS,
    HOLDOUT_V15_ROUTING_FINGERPRINTS,
)
from .structural_operator_policy import StructuralOperatorDecision
from .verified_case_protocol import VerifiedCaseAdjudicationProtocol


CANDIDATE_REVISION_PROTOCOL_VERSION = "candidate_belief_revision_protocol_v0_17"


class CandidateRevisionProtocol(VerifiedCaseAdjudicationProtocol):
    def __init__(
        self, *, base, profiles, operator_credit_snapshot, operator_schedule,
        resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, **values,
    ) -> None:
        case_runtime = values.pop("case_runtime", CandidateRevisionCaseRuntime(base))
        case_item_fingerprints = values.pop("case_item_fingerprints", HOLDOUT_V15_ITEM_FINGERPRINTS)
        case_benchmark_id = values.pop("case_benchmark_id", HOLDOUT_V15_BENCHMARK_ID)
        case_protocol_version = values.pop("case_protocol_version", CANDIDATE_REVISION_PROTOCOL_VERSION)
        item_domains, item_contexts = (values.pop("item_domains", HOLDOUT_V15_ITEM_DOMAINS),
                                       values.pop("item_contexts", HOLDOUT_V15_ITEM_FINGERPRINTS))
        arm_namespace = values.pop("arm_namespace", "HOLDOUT_V15")
        routing_fingerprints = values.pop("routing_fingerprints", HOLDOUT_V15_ROUTING_FINGERPRINTS)
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=routing_fingerprints,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=case_runtime, case_item_fingerprints=case_item_fingerprints,
            case_benchmark_id=case_benchmark_id, case_protocol_version=case_protocol_version,
            case_source_actions=("PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED",
                                 "CANDIDATE_REVISION_RESOLVED"),
            item_domains=item_domains, item_contexts=item_contexts,
            arm_namespace=arm_namespace, **values,
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
            pairs.append({"item_id": item_id, "primary_model_id": primary.model_id,
                          "peer_model_id": peer.model_id, "primary_answer": primary.answer,
                          "peer_answer": peer.answer})
        receipt = self.base.harness.audit_candidate_revision_opportunities(
            experiment_id=experiment_id + "-revision-opportunity", pairs=tuple(pairs),
        )
        self._opportunity_gate_passed = receipt.gate_passed
        return receipt

    def _resolve_post_disagreement(self, **values):
        if self._opportunity_gate_passed:
            return super()._resolve_post_disagreement(**values)
        decision, primary = values["decision"], values["primary_signal"]
        kept = StructuralOperatorDecision(**{
            **decision.__dict__, "action": "PRIMARY_KEEP_RESOLVED",
            "final_answer": primary.answer, "reason": "primary_error_gate_blocks_revision_work",
            "resolution_policy": "REVISION_OPPORTUNITY_GATE_KEEP",
            "resolution_evidence_level": "AGGREGATE_PRIMARY_ERROR_GATE",
        })
        return kept, ()

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": CANDIDATE_REVISION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V15_BENCHMARK_ID,
            "v16_outcomes_used_as_diagnostic_prior": True,
            "v16_experimental_fingerprints_written_to_stable_history": False,
            "v17_outcomes_used_for_current_route": False,
            "provider_may_revise_or_retract_original_candidate": True,
            "revision_requires_harness_replay_and_blinded_judgment": True,
            "opportunity_gate_basis": "PRIMARY_ERROR_OPPORTUNITY",
            "opportunity_gate_has_routing_authority": False,
        })
        report["candidate_revision_arm"] = report.pop("verified_case_adjudication_arm")
        gate = report["pre_route_audit"]
        decisions = report["route_decisions"]
        receipts = [
            receipt for event in report["case_adjudication_events"]
            for receipt in event["verification_receipts"]
        ]
        report["comparisons"].update({
            "revision_opportunity_gate_passed": gate["gate_passed"],
            "primary_error_opportunities": gate["primary_error_opportunities"],
            "verified_candidate_revisions": sum(
                item["status"] == "VERIFIED" and item["disposition"] == "REVISE" for item in receipts
            ),
            "candidate_retractions": sum(item["status"] == "RETRACTED" for item in receipts),
            "candidate_revision_adoptions": sum(
                item["resolution_policy"] == "PROVIDER_BACKED_CANDIDATE_REVISION"
                for item in decisions
            ),
            "revision_opportunity_gate_keeps": sum(
                item["resolution_policy"] == "REVISION_OPPORTUNITY_GATE_KEEP"
                for item in decisions
            ),
        })
        inherited_status = report["comparisons"].pop("verified_case_improvement_status")
        if not gate["gate_passed"]:
            status = "NOT_ESTIMABLE_NO_PRE_ROUTE_PRIMARY_ERROR_OPPORTUNITY"
        elif not any(item["status"] == "VERIFIED" for item in receipts):
            status = "NO_VERIFIED_REVISION_CONSTRUCTION_FAILURE"
        elif report["comparisons"]["case_observed_net_cbit"] > 0.0:
            status = "POSITIVE_HELDOUT_CANDIDATE_REVISION_CBIT"
        elif report["comparisons"]["case_observed_net_cbit"] < 0.0:
            status = "NEGATIVE_HELDOUT_CANDIDATE_REVISION_CBIT"
        else:
            status = "VERIFIED_REVISIONS_WITH_ZERO_OBSERVED_NET_CBIT"
        report["comparisons"].update({"candidate_revision_primary_keeps": sum(
                item["resolution_policy"] in {
                    "CANDIDATE_REVISION_CONFIRMED_PRIMARY", "CANDIDATE_REVISION_KEEP_PRIMARY",
                    "CASE_PROVIDER_FAILED_KEEP", "REVISION_OPPORTUNITY_GATE_KEEP",
                } for item in decisions
            ),
            "candidate_revision_route_status": inherited_status,
            "candidate_revision_improvement_status": status,
        })
        return report
