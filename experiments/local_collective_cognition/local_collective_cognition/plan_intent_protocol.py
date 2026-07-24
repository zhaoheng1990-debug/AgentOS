"""Protocol v0.23: calibrated global plan intent with Kernel consistency gate."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .holdout_v21_benchmark import (
    HOLDOUT_V21_BENCHMARK_ID, HOLDOUT_V21_ITEM_DOMAINS, HOLDOUT_V21_ITEM_FINGERPRINTS,
    HOLDOUT_V21_ROUTING_FINGERPRINTS,
)
from .plan_intent_case_runtime import PlanIntentCaseRuntime
from .plan_intent_metrics import plan_intent_metrics


PLAN_INTENT_PROTOCOL_VERSION = "calibrated_global_plan_intent_protocol_v0_23"


class PlanIntentProtocol(CandidateRevisionProtocol):
    def __init__(self, *, base, profiles, operator_credit_snapshot, operator_schedule,
                 resolution_credit_snapshot, resolution_exploration_schedule,
                 context_credit_snapshot, **values):
        routing_fingerprints = values.pop("routing_fingerprints", HOLDOUT_V21_ROUTING_FINGERPRINTS)
        case_runtime = values.pop("case_runtime", PlanIntentCaseRuntime(base))
        case_fingerprints = values.pop("case_item_fingerprints", HOLDOUT_V21_ITEM_FINGERPRINTS)
        case_benchmark = values.pop("case_benchmark_id", HOLDOUT_V21_BENCHMARK_ID)
        case_version = values.pop("case_protocol_version", PLAN_INTENT_PROTOCOL_VERSION)
        item_domains = values.pop("item_domains", HOLDOUT_V21_ITEM_DOMAINS)
        item_contexts = values.pop("item_contexts", case_fingerprints)
        arm_namespace = values.pop("arm_namespace", "HOLDOUT_V21")
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
            case_runtime=case_runtime, case_item_fingerprints=case_fingerprints,
            case_benchmark_id=case_benchmark, case_protocol_version=case_version,
            item_domains=item_domains, item_contexts=item_contexts,
            routing_fingerprints=routing_fingerprints, arm_namespace=arm_namespace, **values,
        )

    def run(self, experiment_id, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": PLAN_INTENT_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V21_BENCHMARK_ID,
            "v22_outcomes_used_as_diagnostic_prior": True,
            "v22_experimental_fingerprints_written_to_stable_history": False,
            "v23_outcomes_used_for_current_route": False,
            "context_calibrated_label_scoring": True,
            "calibration_prior_cache_scope": "MODEL_X_MENU_SIZE",
            "global_plan_intent_required": True,
            "local_action_plan_consistency_kernel_gate": True,
            "plan_budget_kernel_enforced": True,
            "provider_plan_or_judge_has_final_authority": False,
        })
        report["plan_intent_arm"] = report.pop("candidate_revision_arm")
        report["comparisons"].update(plan_intent_metrics(
            report["case_adjudication_events"], report["case_adjudication_failures"],
            report["comparisons"],
        ))
        report["comparisons"].pop("candidate_revision_improvement_status", None)
        return report
