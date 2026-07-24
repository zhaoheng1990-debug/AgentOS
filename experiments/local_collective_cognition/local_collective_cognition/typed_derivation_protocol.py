"""Protocol v0.18: typed derivation plans for Provider-backed candidate revision."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .holdout_v16_benchmark import (
    HOLDOUT_V16_BENCHMARK_ID, HOLDOUT_V16_ITEM_DOMAINS, HOLDOUT_V16_ITEM_FINGERPRINTS,
    HOLDOUT_V16_ROUTING_FINGERPRINTS,
)
from .typed_derivation_case_runtime import TypedDerivationCaseRuntime


TYPED_DERIVATION_PROTOCOL_VERSION = "typed_candidate_derivation_protocol_v0_18"


class TypedDerivationProtocol(CandidateRevisionProtocol):
    def __init__(
        self, *, base, profiles, operator_credit_snapshot, operator_schedule,
        resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, **values,
    ) -> None:
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V16_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=TypedDerivationCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V16_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V16_BENCHMARK_ID,
            case_protocol_version=TYPED_DERIVATION_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V16_ITEM_DOMAINS, item_contexts=HOLDOUT_V16_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V16_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V16", **values,
        )

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": TYPED_DERIVATION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V16_BENCHMARK_ID,
            "v17_outcomes_used_as_diagnostic_prior": True,
            "v17_experimental_fingerprints_written_to_stable_history": False,
            "v18_outcomes_used_for_current_route": False,
            "typed_derivation_scaffold_answer_independent": True,
            "provider_selects_operators_and_candidate": True,
            "harness_executes_plan_mechanically": True,
        })
        report["typed_derivation_arm"] = report.pop("candidate_revision_arm")
        receipts = [receipt for event in report["case_adjudication_events"]
                    for receipt in event["verification_receipts"]]
        report["comparisons"].update({
            "typed_derivation_receipts": len(receipts),
            "typed_derivation_verified": sum(item["status"] == "VERIFIED" for item in receipts),
            "typed_derivation_executed_steps": sum(item["executed_steps"] for item in receipts),
        })
        report["comparisons"]["typed_derivation_improvement_status"] = report[
            "comparisons"
        ].pop("candidate_revision_improvement_status")
        return report
