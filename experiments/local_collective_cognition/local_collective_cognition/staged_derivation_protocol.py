"""Protocol v0.20: action choice followed by action-specific arguments."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .holdout_v18_benchmark import (
    HOLDOUT_V18_BENCHMARK_ID, HOLDOUT_V18_ITEM_DOMAINS, HOLDOUT_V18_ITEM_FINGERPRINTS,
    HOLDOUT_V18_ROUTING_FINGERPRINTS,
)
from .staged_derivation_case_runtime import StagedDerivationCaseRuntime


STAGED_DERIVATION_PROTOCOL_VERSION = "staged_candidate_derivation_protocol_v0_20"


class StagedDerivationProtocol(CandidateRevisionProtocol):
    def __init__(self, *, base, profiles, operator_credit_snapshot, operator_schedule,
                 resolution_credit_snapshot, resolution_exploration_schedule,
                 context_credit_snapshot, **values) -> None:
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V18_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=StagedDerivationCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V18_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V18_BENCHMARK_ID,
            case_protocol_version=STAGED_DERIVATION_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V18_ITEM_DOMAINS, item_contexts=HOLDOUT_V18_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V18_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V18", **values,
        )

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": STAGED_DERIVATION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V18_BENCHMARK_ID,
            "v19_outcomes_used_as_diagnostic_prior": True,
            "v19_experimental_fingerprints_written_to_stable_history": False,
            "v20_outcomes_used_for_current_route": False,
            "provider_action_selection_separate": True,
            "provider_action_specific_arguments": True,
            "control_cost_explicit": True,
            "session_limits_kernel_owned": True,
        })
        report["staged_derivation_arm"] = report.pop("candidate_revision_arm")
        events, failures = report["case_adjudication_events"], report["case_adjudication_failures"]
        receipts = [receipt for event in events for receipt in event["verification_receipts"]]
        sessions = [record for event in events
                    for record in (event["primary_argument"], event["peer_argument"])]
        totals = self._work_totals(sessions, failures)
        report["comparisons"].update({
            "staged_derivation_receipts": len(receipts),
            "staged_derivation_verified": sum(item["status"] == "VERIFIED" for item in receipts),
            **totals,
        })
        report["comparisons"]["staged_derivation_improvement_status"] = report[
            "comparisons"
        ].pop("candidate_revision_improvement_status")
        return report

    @staticmethod
    def _work_totals(sessions, failures):
        fields = ("provider_turns", "control_turns", "argument_turns", "applied_steps",
                  "invalid_controls", "invalid_arguments", "invalid_actions")
        result = {}
        for field in fields:
            session_key = "session_" + field
            completed = sum(int(item.get(session_key, 0)) for item in sessions)
            failed = sum(int(item.get(session_key, 0)) for item in failures)
            result["staged_completed_" + field] = completed
            result["staged_failed_" + field] = failed
            result["staged_" + field] = completed + failed
        return result
