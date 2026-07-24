"""Protocol v0.21: finite token-constrained derivation tool calls."""

from __future__ import annotations

from .candidate_revision_policy import CandidateRevisionPolicy
from .candidate_revision_protocol import CandidateRevisionProtocol
from .constrained_tool_case_runtime import ConstrainedToolCaseRuntime
from .constrained_tool_metrics import constrained_tool_metrics
from .holdout_v19_benchmark import (
    HOLDOUT_V19_BENCHMARK_ID, HOLDOUT_V19_ITEM_DOMAINS, HOLDOUT_V19_ITEM_FINGERPRINTS,
    HOLDOUT_V19_ROUTING_FINGERPRINTS,
)


CONSTRAINED_TOOL_PROTOCOL_VERSION = "constrained_tool_derivation_protocol_v0_21"


class ConstrainedToolProtocol(CandidateRevisionProtocol):
    def __init__(self, *, base, profiles, operator_credit_snapshot, operator_schedule,
                 resolution_credit_snapshot, resolution_exploration_schedule,
                 context_credit_snapshot, **values) -> None:
        values["policy"] = values.get("policy") or CandidateRevisionPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V19_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=ConstrainedToolCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V19_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V19_BENCHMARK_ID,
            case_protocol_version=CONSTRAINED_TOOL_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V19_ITEM_DOMAINS, item_contexts=HOLDOUT_V19_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V19_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V19", **values,
        )

    def run(self, experiment_id: str, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": CONSTRAINED_TOOL_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V19_BENCHMARK_ID,
            "v20_outcomes_used_as_diagnostic_prior": True,
            "v20_experimental_fingerprints_written_to_stable_history": False,
            "v21_outcomes_used_for_current_route": False,
            "finite_registered_tool_calls": True,
            "token_trie_constrained_decoding": True,
            "provider_semantic_choice_preserved": True,
            "adapter_shape_authority_only": True,
            "session_limits_kernel_owned": True,
        })
        report["constrained_tool_arm"] = report.pop("candidate_revision_arm")
        events, failures = report["case_adjudication_events"], report["case_adjudication_failures"]
        report["comparisons"].update(constrained_tool_metrics(
            events, failures, report["comparisons"]["case_adjudication_items"],
        ))
        report["comparisons"]["constrained_tool_improvement_status"] = report[
            "comparisons"
        ].pop("candidate_revision_improvement_status")
        return report
