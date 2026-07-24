"""Operationally replayable calibrated collaboration across frozen holdouts."""

from __future__ import annotations

from typing import Any, Callable

from .benchmark_routing_calibration import RoutingCalibrationReceipt
from .calibrated_policy import CalibratedCandidateSignal, CalibratedModelPlan, CostAwareReviewPolicy
from .collective_protocol import LocalCollectiveCognitionProtocol, RoleRun
from .holdout_v2_benchmark import HOLDOUT_V2_ITEM_DOMAINS
from .routing_calibration import CalibratedModelProfile, ReviewerValueLedger


CALIBRATED_PROTOCOL_VERSION = "calibrated_collaboration_protocol_v0_4"


class CalibratedCollaborationProtocol:
    def __init__(
        self,
        *,
        base: LocalCollectiveCognitionProtocol,
        calibration_receipt: RoutingCalibrationReceipt,
        profiles: dict[str, CalibratedModelProfile],
        reviewer_ledger: ReviewerValueLedger,
        policy: CostAwareReviewPolicy | None = None,
        item_domains: dict[str, str] | None = None,
        item_contexts: dict[str, str] | None = None,
        arm_namespace: str = "HOLDOUT_V2",
        profile_receipt_hash: str | None = None,
        exploration_schedule: dict[str, str] | None = None,
    ) -> None:
        if set(profiles) != set(base.small_adapters):
            raise ValueError("calibrated_profile_model_coverage_invalid")
        expected_profile_hash = profile_receipt_hash or calibration_receipt.receipt_hash
        if any(item.receipt_hash != expected_profile_hash for item in profiles.values()):
            raise ValueError("calibrated_profile_receipt_binding_invalid")
        if reviewer_ledger.receipt_hash != calibration_receipt.receipt_hash:
            raise ValueError("calibrated_reviewer_ledger_binding_invalid")
        self.base = base
        self.calibration_receipt = calibration_receipt
        self.profiles = profiles
        self.reviewer_ledger = reviewer_ledger
        self.policy = policy or CostAwareReviewPolicy()
        self.item_domains = dict(item_domains or HOLDOUT_V2_ITEM_DOMAINS)
        self.item_contexts = dict(item_contexts or self.item_domains)
        self.arm_namespace = arm_namespace
        self.profile_receipt_hash = expected_profile_hash
        self.exploration_schedule = dict(exploration_schedule or {})
        if set(self.item_domains) != set(base.item_ids):
            raise ValueError("calibrated_item_domain_coverage_invalid")
        if set(self.item_contexts) != set(base.item_ids):
            raise ValueError("calibrated_item_context_coverage_invalid")
        if not set(self.exploration_schedule).issubset(base.item_ids) or not set(self.exploration_schedule.values()).issubset(base.small_adapters):
            raise ValueError("calibrated_exploration_schedule_invalid")

    def run(
        self,
        experiment_id: str,
        *,
        baseline_run: RoleRun | None = None,
        baseline_observer: Callable[[RoleRun], Any] | None = None,
        prepare_small_models: Callable[[], Any] | None = None,
    ) -> dict[str, Any]:
        baseline = baseline_run or self.base.execute_role(
            role_id="holdout-v2-deepseek-32b",
            adapter=self.base.baseline_adapter,
            task_kind="pilot_32b_baseline",
            objective=self.base._answer_objective("Solve holdout v2 independently as the large-model baseline."),
            round_context={"role": "independent_large_model_holdout_v2"},
            itemwise=True,
        )
        if baseline_observer is not None and baseline_run is None:
            baseline_observer(baseline)
        baseline_arm = self.base.score_arm(experiment_id, f"{self.arm_namespace}_DEEPSEEK_32B", (baseline,), baseline.result, 1)
        if prepare_small_models is not None:
            prepare_small_models()

        proposals = tuple(
            self.base.execute_role(
                role_id=f"holdout-v2-independent-{index + 1}",
                adapter=adapter,
                task_kind="pilot_solo_answer",
                objective=self.base._answer_objective("Solve holdout v2 independently without peer outputs."),
                round_context={"role": "holdout_v2_independent", "peer_outputs": "withheld"},
                itemwise=True,
            )
            for index, adapter in enumerate(self.base.small_adapters.values())
        )
        solo_arms = tuple(
            self.base.score_arm(experiment_id, f"{self.arm_namespace}_SOLO_{run.model_id}", (run,), run.result, 1)
            for run in proposals
        )
        majority_result, disagreement_ids = self.base.majority_result(proposals)
        majority_arm = self.base.score_arm(experiment_id, f"{self.arm_namespace}_MAJORITY", proposals, majority_result, 1)
        proposal_by_model = {run.model_id: run for run in proposals}
        pre_route_audit = self._pre_route_audit(experiment_id, proposal_by_model)

        selected_runs: list[RoleRun] = []
        final_answers = []
        route_decisions = []
        exploration_events = []
        for item_id in self.base.item_ids:
            domain = self.item_domains[item_id]
            context = self.item_contexts[item_id]
            plans = self._plans(domain, context)
            primary_plan = self.policy.select_primary(plans)
            primary_run = self.base.slice_item_run(proposal_by_model[primary_plan.model_id], item_id)
            primary_signal = self._signal(primary_run, item_id, domain, context)
            decision = self.policy.route(
                primary_signal,
                plans=plans,
                domain=domain,
                reviewer_ledger=self.reviewer_ledger,
            )
            selected_runs.append(primary_run)
            explorer_model_id = self.exploration_schedule.get(item_id, "")
            if explorer_model_id and explorer_model_id != primary_plan.model_id:
                exploration_run = self.base.slice_item_run(proposal_by_model[explorer_model_id], item_id)
                selected_runs.append(exploration_run)
                exploration_events.append({
                    "item_id": item_id,
                    "domain": domain,
                    "model_id": explorer_model_id,
                    "used_for_current_answer": False,
                    "candidate_only": True,
                })
            if decision.action == "REVIEW":
                review_run = self.base.execute_item(
                    role_id="calibrated-review-" + decision.reviewer_model_id,
                    adapter=self.base.small_adapters[decision.reviewer_model_id],
                    task_kind="pilot_disagreement_review",
                    role_instruction="Independently review the primary answer and return the strongest answer for the target item.",
                    round_context={
                        "role": "calibrated_reviewer",
                        "primary_candidate": dict(primary_signal.__dict__),
                        "domain": domain,
                        "calibration_receipt_ref": self.calibration_receipt.receipt_hash,
                    },
                    item_id=item_id,
                )
                reviewer_signal = self._signal(review_run, item_id, domain, context)
                decision = self.policy.resolve(
                    decision, primary_signal, reviewer_signal,
                    domain=domain, reviewer_ledger=self.reviewer_ledger,
                )
                selected_runs.append(review_run)
            elif decision.action == "ARBITRATE_MAJORITY":
                peer_signals = []
                for peer_model_id in decision.peer_model_ids:
                    peer_run = self.base.slice_item_run(proposal_by_model[peer_model_id], item_id)
                    selected_runs.append(peer_run)
                    peer_signals.append(self._signal(peer_run, item_id, domain, context))
                decision = self.policy.resolve_majority(decision, primary_signal, tuple(peer_signals))
            elif decision.action in {"MICRO_PROBE", "VERIFY_PEER"}:
                peer_run = self.base.slice_item_run(proposal_by_model[decision.reviewer_model_id], item_id)
                selected_runs.append(peer_run)
                peer_signal = self._signal(peer_run, item_id, domain, context)
                decision = self.policy.resolve_probe(decision, primary_signal, peer_signal)
                if decision.action in {"REQUEST_CONTEXT_WITNESS", "REQUEST_CASE_ADJUDICATION"}:
                    decision, post_runs = self._resolve_post_disagreement(
                        decision=decision, primary_signal=primary_signal, peer_signal=peer_signal,
                        proposal_by_model=proposal_by_model, item_id=item_id,
                        domain=domain, context=context,
                    )
                    selected_runs.extend(post_runs)
            final_answers.append({"item_id": item_id, "answer": decision.final_answer})
            route_decisions.append(decision)

        selective_result = {"answers": final_answers, "evidence_refs": list(self.base.harness.evidence_refs)}
        selective_arm = self.base.score_arm(
            experiment_id, f"{self.arm_namespace}_CALIBRATED_REVIEW", tuple(selected_runs), selective_result,
            self._round_count(route_decisions, exploration_events),
        )
        outcome_receipt = self.base.harness.calibrate_routing(
            experiment_id=experiment_id,
            calibration_receipt_hash=self.calibration_receipt.receipt_hash,
            route_decisions=tuple(item.as_dict() for item in route_decisions),
            item_domains=self.item_domains,
        )
        best = max(solo_arms, key=lambda item: (item.harness_receipt.exact_accuracy, -item.total_tokens))
        union_ceiling = self.base.harness.candidate_union_ceiling(tuple(item.result for item in proposals))
        return {
            "experiment_id": experiment_id,
            "protocol": {
                "protocol_version": CALIBRATED_PROTOCOL_VERSION,
                "calibration_benchmark": "local-reasoning-holdout-v0-1",
                "holdout_benchmark": "local-reasoning-holdout-v0-2",
                "calibration_holdout_separated": True,
                "operational_route_replayable_without_peer_outputs": True,
                "comparison_proposals_not_charged_to_calibrated_arm": True,
                "provider_truth_exposure_detected": False,
                "claim_boundary": "single_holdout_pilot_not_production_route_authority",
                "shadow_exploration_used_for_current_answer": False,
            },
            "calibration_receipt": self.calibration_receipt.as_dict(),
            "calibrated_profiles": [item.as_dict() for item in self.profiles.values()],
            "reviewer_value_ledger": self.reviewer_ledger.as_dict(),
            "review_outcome_receipt": outcome_receipt.as_dict(),
            "solo_arms": [item.as_dict() for item in solo_arms],
            "best_small_model": best.as_dict(),
            "majority_arm": majority_arm.as_dict(),
            "calibrated_arm": selective_arm.as_dict(),
            "deepseek_32b_arm": baseline_arm.as_dict(),
            "route_decisions": [item.as_dict() for item in route_decisions],
            "pre_route_audit": pre_route_audit.as_dict() if pre_route_audit is not None else None,
            "exploration_events": exploration_events,
            "comparisons": {
                "independent_disagreement_items": len(disagreement_ids),
                "candidate_union_ceiling": union_ceiling,
                "reviewed_items": sum(item.action == "REVIEW_RESOLVED" for item in route_decisions),
                "arbitrated_items": sum(item.action == "MAJORITY_RESOLVED" for item in route_decisions),
                "micro_probe_items": sum(item.action == "MICRO_PROBE_RESOLVED" for item in route_decisions),
                "peer_verification_items": sum(item.action == "PEER_VERIFICATION_RESOLVED" for item in route_decisions),
                "peer_resolution_items": sum(item.action in {"PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"} for item in route_decisions),
                "exploration_items": len(exploration_events),
                "review_corrections": outcome_receipt.corrected_count,
                "review_harms": outcome_receipt.harmed_count,
                "review_observed_net_cbit": outcome_receipt.observed_net_cbit,
                "stopped_confident_items": sum(item.action == "STOP_CALIBRATED_CONFIDENT" for item in route_decisions),
                "stopped_low_value_items": sum(item.action == "STOP_LOW_VALUE_PER_COST" for item in route_decisions),
                "score_delta_vs_best": round(selective_arm.harness_receipt.exact_accuracy - best.harness_receipt.exact_accuracy, 12),
                "score_delta_vs_majority": round(selective_arm.harness_receipt.exact_accuracy - majority_arm.harness_receipt.exact_accuracy, 12),
                "score_delta_vs_32b": round(selective_arm.harness_receipt.exact_accuracy - baseline_arm.harness_receipt.exact_accuracy, 12),
                "call_ratio_vs_majority": round(len(selective_arm.telemetry) / len(majority_arm.telemetry), 6),
                "token_ratio_vs_majority": round(selective_arm.total_tokens / majority_arm.total_tokens, 6),
                "calibrated_improvement_status": self._status(selective_arm, best, majority_arm),
            },
        }

    def _resolve_post_disagreement(
        self, *, decision, primary_signal, peer_signal, proposal_by_model,
        item_id: str, domain: str, context: str,
    ):
        del domain
        if decision.action != "REQUEST_CONTEXT_WITNESS":
            raise ValueError("calibrated_post_disagreement_action_invalid")
        context_run = self.base.slice_item_run(proposal_by_model[decision.context_model_id], item_id)
        context_signal = self._signal(context_run, item_id, self.item_domains[item_id], context)
        resolved = self.policy.resolve_context(
            decision, primary_signal, peer_signal, context_signal,
        )
        return resolved, (context_run,)

    def _pre_route_audit(self, experiment_id, proposal_by_model):
        del experiment_id, proposal_by_model
        return None

    @staticmethod
    def _round_count(route_decisions, exploration_events) -> int:
        if any(getattr(item, "case_adjudication_used", False) for item in route_decisions):
            return 5
        if any(getattr(item, "context_witness_used", False) for item in route_decisions):
            return 3
        resolved = {
            "REVIEW_RESOLVED", "MAJORITY_RESOLVED", "MICRO_PROBE_RESOLVED",
            "PEER_VERIFICATION_RESOLVED", "PEER_AGREEMENT_RESOLVED",
            "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED",
        }
        return 2 if exploration_events or any(item.action in resolved for item in route_decisions) else 1

    def _plans(self, domain: str, context: str | None = None) -> tuple[CalibratedModelPlan, ...]:
        return tuple(
            CalibratedModelPlan(
                model_id=profile.model_id,
                predicted_success=round(
                    0.75 * (
                        profile.context_reliability(context, domain)
                        if context is not None and hasattr(profile, "context_reliability")
                        else profile.domain_reliability(domain)
                    )
                    + 0.25 * profile.global_posterior,
                    12,
                ),
                expected_work=profile.expected_work(),
            )
            for profile in self.profiles.values()
        )

    def _signal(self, run: RoleRun, item_id: str, domain: str, context: str | None = None) -> CalibratedCandidateSignal:
        answer = next(item for item in run.result["answers"] if item["item_id"] == item_id)
        profile = self.profiles[run.model_id]
        had_retry = any(item.status == "FAILED" for item in run.telemetry)
        calibrated_success = (
            profile.calibrated_success_for_context(context, domain, float(answer["confidence"]), had_retry)
            if context is not None and hasattr(profile, "calibrated_success_for_context")
            else profile.calibrated_success(domain, float(answer["confidence"]), had_retry)
        )
        return CalibratedCandidateSignal(
            model_id=run.model_id, item_id=item_id, answer=answer["answer"].strip().upper(),
            raw_confidence=float(answer["confidence"]),
            calibrated_success=calibrated_success,
            expected_work=profile.expected_work(), had_structured_retry=had_retry,
        )

    @staticmethod
    def _status(calibrated, best, majority) -> str:
        score = calibrated.harness_receipt.exact_accuracy
        if score > best.harness_receipt.exact_accuracy and len(calibrated.telemetry) < len(majority.telemetry):
            return "CALIBRATED_COGNITIVE_GAIN_WITH_LOWER_GROUP_WORK"
        if score >= best.harness_receipt.exact_accuracy and len(calibrated.telemetry) < len(majority.telemetry):
            return "BEST_MEMBER_PRESERVED_WITH_LOWER_GROUP_WORK"
        return "CALIBRATED_POLICY_NOT_YET_EFFECTIVE"
