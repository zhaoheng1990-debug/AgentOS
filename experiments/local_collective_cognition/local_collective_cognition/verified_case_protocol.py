"""Protocol v0.15: replay-verified argument evidence before case override."""

from __future__ import annotations

from typing import Any

from .case_adjudication_protocol import CaseAdjudicationProtocol
from .holdout_v13_benchmark import (
    HOLDOUT_V13_BENCHMARK_ID, HOLDOUT_V13_ITEM_DOMAINS, HOLDOUT_V13_ITEM_FINGERPRINTS,
    HOLDOUT_V13_ROUTING_FINGERPRINTS,
)
from .verified_case_policy import VerifiedCaseAdjudicationPolicy
from .verified_case_runtime import VerifiedDisagreementCaseRuntime


VERIFIED_CASE_PROTOCOL_VERSION = "verified_argument_adjudication_protocol_v0_15"


class VerifiedCaseAdjudicationProtocol(CaseAdjudicationProtocol):
    def __init__(
        self, *, base, profiles, operator_credit_snapshot, operator_schedule,
        resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, case_runtime=None, **values: Any,
    ) -> None:
        case_item_fingerprints = values.pop("case_item_fingerprints", HOLDOUT_V13_ITEM_FINGERPRINTS)
        case_benchmark_id = values.pop("case_benchmark_id", HOLDOUT_V13_BENCHMARK_ID)
        case_protocol_version = values.pop("case_protocol_version", VERIFIED_CASE_PROTOCOL_VERSION)
        item_domains = values.pop("item_domains", HOLDOUT_V13_ITEM_DOMAINS)
        item_contexts = values.pop("item_contexts", HOLDOUT_V13_ITEM_FINGERPRINTS)
        arm_namespace = values.pop("arm_namespace", "HOLDOUT_V13")
        values["policy"] = values.get("policy") or VerifiedCaseAdjudicationPolicy(
            operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
            item_fingerprints=HOLDOUT_V13_ROUTING_FINGERPRINTS,
            resolution_credit=resolution_credit_snapshot,
            exploration_items=tuple(resolution_exploration_schedule),
            context_credit=context_credit_snapshot, model_ids=tuple(profiles),
        )
        super().__init__(
            base=base, profiles=profiles, operator_credit_snapshot=operator_credit_snapshot,
            operator_schedule=operator_schedule, resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot,
            case_runtime=case_runtime or VerifiedDisagreementCaseRuntime(base),
            case_item_fingerprints=case_item_fingerprints,
            case_benchmark_id=case_benchmark_id,
            case_protocol_version=case_protocol_version,
            item_domains=item_domains, item_contexts=item_contexts,
            arm_namespace=arm_namespace, **values,
        )

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": VERIFIED_CASE_PROTOCOL_VERSION,
            "v14_outcomes_used_as_diagnostic_prior": True,
            "v15_outcomes_used_for_current_route": False,
            "argument_fact_replay_harness_owned": True,
            "argument_fact_replay_hidden_truth_access": False,
            "override_requires_provider_judgment_and_replay": True,
            "new_fingerprint_routing_uses_diagnostic_proxy": True,
        })
        events = report["case_adjudication_events"]
        receipts = [receipt for event in events for receipt in event["verification_receipts"]]
        decisions = report["route_decisions"]
        report["verified_case_adjudication_arm"] = report.pop("case_adjudication_arm")
        report["comparisons"].update({
            "verified_argument_receipts": len(receipts),
            "verified_arguments": sum(item["status"] == "VERIFIED" for item in receipts),
            "failed_argument_replays": sum(item["status"] == "FAILED" for item in receipts),
            "verified_case_peer_overrides": sum(
                item["resolution_policy"] == "VERIFIED_CASE_PEER_OVERRIDE" for item in decisions
            ),
            "verified_case_primary_keeps": sum(
                item["resolution_policy"] in {"VERIFIED_CASE_KEEP_PRIMARY", "CASE_PROVIDER_FAILED_KEEP"}
                for item in decisions
            ),
        })
        report["comparisons"]["verified_case_improvement_status"] = report["comparisons"].pop(
            "case_adjudication_improvement_status"
        )
        return report
