"""Protocol v0.22: hierarchical enum scoring with constrained judgment."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .hierarchical_tool_case_runtime import HierarchicalToolCaseRuntime
from .hierarchical_tool_metrics import hierarchical_tool_metrics
from .holdout_v20_benchmark import (
    HOLDOUT_V20_BENCHMARK_ID, HOLDOUT_V20_ITEM_DOMAINS, HOLDOUT_V20_ITEM_FINGERPRINTS,
    HOLDOUT_V20_ROUTING_FINGERPRINTS,
)


HIERARCHICAL_TOOL_PROTOCOL_VERSION = "hierarchical_enum_derivation_protocol_v0_22"


class HierarchicalToolProtocol(CandidateRevisionProtocol):
    def __init__(self, *, base, profiles, operator_credit_snapshot, operator_schedule,
                 resolution_credit_snapshot, resolution_exploration_schedule,
                 context_credit_snapshot, **values):
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V20_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=HierarchicalToolCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V20_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V20_BENCHMARK_ID,
            case_protocol_version=HIERARCHICAL_TOOL_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V20_ITEM_DOMAINS, item_contexts=HOLDOUT_V20_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V20_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V20", **values,
        )

    def run(self, experiment_id, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": HIERARCHICAL_TOOL_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V20_BENCHMARK_ID,
            "v21_outcomes_used_as_diagnostic_prior": True,
            "v21_experimental_fingerprints_written_to_stable_history": False,
            "v22_outcomes_used_for_current_route": False,
            "hierarchical_small_enum_scoring": True,
            "action_and_judge_score_receipts": True,
            "judge_free_json_generation": False,
            "provider_semantic_choice_preserved": True,
            "kernel_confidence_and_replay_gates_preserved": True,
        })
        report["hierarchical_tool_arm"] = report.pop("candidate_revision_arm")
        report["comparisons"].update(hierarchical_tool_metrics(
            report["case_adjudication_events"], report["case_adjudication_failures"],
            report["comparisons"]["case_adjudication_items"],
        ))
        report["comparisons"]["hierarchical_tool_improvement_status"] = report[
            "comparisons"
        ].pop("candidate_revision_improvement_status")
        return report
