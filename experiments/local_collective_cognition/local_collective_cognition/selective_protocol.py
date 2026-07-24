"""Calibration-backed selective collaboration on a frozen holdout."""

from __future__ import annotations

from typing import Any, Callable

from .collective_protocol import LocalCollectiveCognitionProtocol, RoleRun
from .benchmark_reliability import BenchmarkReliabilityReceipt
from .holdout_benchmark import HOLDOUT_ITEM_DOMAINS
from .selective_calibration import DomainReliabilityProfile
from .selective_policy import CandidateSignal, SelectiveReviewPolicy


SELECTIVE_PROTOCOL_VERSION = "selective_collaboration_protocol_v0_3"


class SelectiveCollaborationProtocol:
    def __init__(
        self,
        *,
        base: LocalCollectiveCognitionProtocol,
        reliability_receipts: tuple[BenchmarkReliabilityReceipt, ...],
        reliability_profiles: dict[str, DomainReliabilityProfile],
        policy: SelectiveReviewPolicy | None = None,
    ) -> None:
        if set(reliability_profiles) != set(base.small_adapters):
            raise ValueError("selective_reliability_model_coverage_invalid")
        if {item.model_id for item in reliability_receipts} != set(reliability_profiles):
            raise ValueError("selective_reliability_receipt_coverage_invalid")
        self.base = base
        self.receipts = reliability_receipts
        self.profiles = reliability_profiles
        self.policy = policy or SelectiveReviewPolicy()

    def run(
        self,
        experiment_id: str,
        *,
        baseline_run: RoleRun | None = None,
        baseline_observer: Callable[[RoleRun], Any] | None = None,
        prepare_small_models: Callable[[], Any] | None = None,
    ) -> dict[str, Any]:
        baseline = baseline_run or self.base.execute_role(
            role_id="holdout-deepseek-32b",
            adapter=self.base.baseline_adapter,
            task_kind="pilot_32b_baseline",
            objective=self.base._answer_objective("Solve the holdout independently as the large-model baseline."),
            round_context={"role": "independent_large_model_holdout"},
            itemwise=True,
        )
        if baseline_observer is not None and baseline_run is None:
            baseline_observer(baseline)
        baseline_arm = self.base.score_arm(experiment_id, "HOLDOUT_DEEPSEEK_32B", (baseline,), baseline.result, 1)
        if prepare_small_models is not None:
            prepare_small_models()

        proposals = tuple(
            self.base.execute_role(
                role_id=f"holdout-independent-{index + 1}",
                adapter=adapter,
                task_kind="pilot_solo_answer",
                objective=self.base._answer_objective("Solve the holdout independently without peer outputs."),
                round_context={"role": "holdout_independent", "peer_outputs": "withheld"},
                itemwise=True,
            )
            for index, adapter in enumerate(self.base.small_adapters.values())
        )
        solo_arms = tuple(
            self.base.score_arm(experiment_id, f"HOLDOUT_SOLO_{run.model_id}", (run,), run.result, 1)
            for run in proposals
        )
        majority_result, disagreement_ids = self.base.majority_result(proposals)
        majority_arm = self.base.score_arm(
            experiment_id, "HOLDOUT_MAJORITY", proposals, majority_result, 1
        )

        selected_runs = []
        final_answers = []
        route_decisions = []
        proposal_by_model = {run.model_id: run for run in proposals}
        for item_id in self.base.item_ids:
            domain = HOLDOUT_ITEM_DOMAINS[item_id]
            signals = tuple(
                self._signal(run, item_id, domain)
                for run in proposals
            )
            decision = self.policy.route(signals)
            primary_signal = next(item for item in signals if item.model_id == decision.primary_model_id)
            selected_runs.append(self.base.slice_item_run(proposal_by_model[primary_signal.model_id], item_id))
            if decision.action == "REVIEW":
                review_run = self.base.execute_item(
                    role_id="selective-review-" + decision.reviewer_model_id,
                    adapter=self.base.small_adapters[decision.reviewer_model_id],
                    task_kind="pilot_disagreement_review",
                    role_instruction="Independently review the primary candidate and return your answer for the target item.",
                    round_context={
                        "role": "selective_reviewer",
                        "primary_candidate": dict(primary_signal.__dict__),
                        "domain": domain,
                        "reliability_receipt_refs": [item.receipt_hash for item in self.receipts],
                    },
                    item_id=item_id,
                )
                reviewer_signal = self._signal(review_run, item_id, domain)
                decision = self.policy.resolve(decision, primary_signal, reviewer_signal)
                selected_runs.append(review_run)
            final_answers.append({"item_id": item_id, "answer": decision.final_answer})
            route_decisions.append(decision)

        selective_result = {
            "answers": final_answers,
            "evidence_refs": list(self.base.harness.evidence_refs),
        }
        selective_arm = self.base.score_arm(
            experiment_id,
            "HOLDOUT_SELECTIVE_REVIEW",
            tuple(selected_runs),
            selective_result,
            2 if any(item.action == "REVIEW_RESOLVED" for item in route_decisions) else 1,
        )
        best = max(solo_arms, key=lambda item: (item.harness_receipt.exact_accuracy, -item.total_tokens))
        union_ceiling = self.base.harness.candidate_union_ceiling(tuple(item.result for item in proposals))
        return {
            "experiment_id": experiment_id,
            "protocol": {
                "protocol_version": SELECTIVE_PROTOCOL_VERSION,
                "calibration_benchmark": "local-reasoning-pilot-v0-1",
                "holdout_benchmark": "local-reasoning-holdout-v0-1",
                "calibration_holdout_separated": True,
                "counterfactual_shared_proposals": True,
                "provider_truth_exposure_detected": False,
                "claim_boundary": "single_holdout_pilot_not_production_route_authority",
            },
            "reliability_receipts": [item.as_dict() for item in self.receipts],
            "reliability_profiles": [item.as_dict() for item in self.profiles.values()],
            "solo_arms": [item.as_dict() for item in solo_arms],
            "best_small_model": best.as_dict(),
            "majority_arm": majority_arm.as_dict(),
            "selective_arm": selective_arm.as_dict(),
            "deepseek_32b_arm": baseline_arm.as_dict(),
            "route_decisions": [item.as_dict() for item in route_decisions],
            "comparisons": {
                "independent_disagreement_items": len(disagreement_ids),
                "candidate_union_ceiling": union_ceiling,
                "reviewed_items": sum(item.action == "REVIEW_RESOLVED" for item in route_decisions),
                "stopped_confident_items": sum(item.action == "STOP_CONFIDENT" for item in route_decisions),
                "stopped_low_marginal_items": sum(item.action == "STOP_LOW_MARGINAL" for item in route_decisions),
                "score_delta_vs_best": round(selective_arm.harness_receipt.exact_accuracy - best.harness_receipt.exact_accuracy, 12),
                "score_delta_vs_majority": round(selective_arm.harness_receipt.exact_accuracy - majority_arm.harness_receipt.exact_accuracy, 12),
                "score_delta_vs_32b": round(selective_arm.harness_receipt.exact_accuracy - baseline_arm.harness_receipt.exact_accuracy, 12),
                "call_ratio_vs_majority": round(len(selective_arm.telemetry) / len(majority_arm.telemetry), 6),
                "token_ratio_vs_majority": round(selective_arm.total_tokens / majority_arm.total_tokens, 6),
                "selective_improvement_status": self._status(selective_arm, best, majority_arm),
            },
        }

    def _signal(self, run: RoleRun, item_id: str, domain: str) -> CandidateSignal:
        answer = next(item for item in run.result["answers"] if item["item_id"] == item_id)
        item_run = self.base.slice_item_run(run, item_id)
        return CandidateSignal(
            model_id=run.model_id,
            item_id=item_id,
            answer=answer["answer"].strip().upper(),
            confidence=float(answer["confidence"]),
            reliability=self.profiles[run.model_id].score(domain),
            had_structured_retry=any(item.status == "FAILED" for item in item_run.telemetry),
        )

    @staticmethod
    def _status(selective, best, majority) -> str:
        score = selective.harness_receipt.exact_accuracy
        if score > best.harness_receipt.exact_accuracy and len(selective.telemetry) < len(majority.telemetry):
            return "SELECTIVE_COGNITIVE_GAIN_WITH_LOWER_GROUP_WORK"
        if score >= best.harness_receipt.exact_accuracy and len(selective.telemetry) < len(majority.telemetry):
            return "BEST_MEMBER_PRESERVED_WITH_LOWER_GROUP_WORK"
        return "SELECTIVE_POLICY_NOT_YET_EFFECTIVE"
