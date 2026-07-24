"""Protocol v0.13: transfer promoted pair credit to a fresh holdout."""

from __future__ import annotations

from typing import Any

from .context_resolution_policy import ContextAwareResolutionPolicy
from .context_resolution_protocol import ContextResolutionProtocol
from .holdout_v11_benchmark import (
    HOLDOUT_V11_BENCHMARK_ID,
    HOLDOUT_V11_ITEM_DOMAINS,
    HOLDOUT_V11_ITEM_FINGERPRINTS,
)


ITERATED_CONTEXT_PROTOCOL_VERSION = "iterated_pair_credit_transfer_protocol_v0_13"


class IteratedContextResolutionProtocol(ContextResolutionProtocol):
    def __init__(
        self, *, context_evidence_receipts, profiles, operator_credit_snapshot,
        operator_schedule, resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, **values: Any,
    ) -> None:
        if len(context_evidence_receipts) < 4:
            raise ValueError("iterated_context_cycle_coverage_invalid")
        if "policy" not in values:
            values["policy"] = ContextAwareResolutionPolicy(
                operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
                item_fingerprints=HOLDOUT_V11_ITEM_FINGERPRINTS,
                resolution_credit=resolution_credit_snapshot,
                exploration_items=tuple(resolution_exploration_schedule),
                context_credit=context_credit_snapshot, model_ids=tuple(profiles),
            )
        values.setdefault("item_domains", HOLDOUT_V11_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V11_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V11")
        super().__init__(
            context_evidence_receipts=context_evidence_receipts, profiles=profiles,
            operator_credit_snapshot=operator_credit_snapshot, operator_schedule=operator_schedule,
            resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot, **values,
        )

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        report["protocol"].pop("v09_v10_v11_context_outcomes_used_for_v12_route", None)
        report["protocol"].pop("v12_outcomes_used_for_current_route", None)
        report["protocol"].update({
            "protocol_version": ITERATED_CONTEXT_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V11_BENCHMARK_ID,
            "v09_v10_v11_v12_context_outcomes_used_for_v13_route": True,
            "v13_outcomes_used_for_current_route": False,
            "pair_credit_transfer_target": "fresh_holdout",
        })
        report["iterated_context_resolution_arm"] = report.pop("context_resolution_arm")
        status = report["comparisons"].pop("context_resolution_improvement_status")
        report["comparisons"]["iterated_context_resolution_improvement_status"] = status
        return report
