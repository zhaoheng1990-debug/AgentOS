"""Protocol v0.19: bounded single-action derivation sessions."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .holdout_v17_benchmark import (
    HOLDOUT_V17_BENCHMARK_ID, HOLDOUT_V17_ITEM_DOMAINS, HOLDOUT_V17_ITEM_FINGERPRINTS,
    HOLDOUT_V17_ROUTING_FINGERPRINTS,
)
from .iterative_derivation_case_runtime import IterativeDerivationCaseRuntime


ITERATIVE_DERIVATION_PROTOCOL_VERSION = "iterative_candidate_derivation_protocol_v0_19"


class IterativeDerivationProtocol(CandidateRevisionProtocol):
    def __init__(self, *, base, profiles, operator_credit_snapshot, operator_schedule,
                 resolution_credit_snapshot, resolution_exploration_schedule,
                 context_credit_snapshot, **values) -> None:
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V17_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=IterativeDerivationCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V17_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V17_BENCHMARK_ID,
            case_protocol_version=ITERATIVE_DERIVATION_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V17_ITEM_DOMAINS, item_contexts=HOLDOUT_V17_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V17_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V17", **values,
        )

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": ITERATIVE_DERIVATION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V17_BENCHMARK_ID,
            "v18_outcomes_used_as_diagnostic_prior": True,
            "v18_experimental_fingerprints_written_to_stable_history": False,
            "v19_outcomes_used_for_current_route": False,
            "single_action_provider_turns": True,
            "harness_immediate_step_execution": True,
            "invalid_action_feedback_bounded": True,
            "session_limits_kernel_owned": True,
        })
        report["iterative_derivation_arm"] = report.pop("candidate_revision_arm")
        receipts = [receipt for event in report["case_adjudication_events"]
                    for receipt in event["verification_receipts"]]
        failures = report["case_adjudication_failures"]
        completed_turns = sum(item["provider_turns"] for item in receipts)
        completed_steps = sum(item["applied_steps"] for item in receipts)
        completed_invalid = sum(item["invalid_actions"] for item in receipts)
        failed_turns = sum(item.get("session_provider_turns", 0) for item in failures)
        failed_steps = sum(item.get("session_applied_steps", 0) for item in failures)
        failed_invalid = sum(item.get("session_invalid_actions", 0) for item in failures)
        report["comparisons"].update({
            "iterative_derivation_receipts": len(receipts),
            "iterative_derivation_verified": sum(item["status"] == "VERIFIED" for item in receipts),
            "iterative_completed_provider_turns": completed_turns,
            "iterative_failed_provider_turns": failed_turns,
            "iterative_provider_turns": completed_turns + failed_turns,
            "iterative_completed_applied_steps": completed_steps,
            "iterative_failed_applied_steps": failed_steps,
            "iterative_applied_steps": completed_steps + failed_steps,
            "iterative_completed_invalid_actions": completed_invalid,
            "iterative_failed_invalid_actions": failed_invalid,
            "iterative_invalid_actions": completed_invalid + failed_invalid,
        })
        report["comparisons"]["iterative_derivation_improvement_status"] = report[
            "comparisons"
        ].pop("candidate_revision_improvement_status")
        return report
