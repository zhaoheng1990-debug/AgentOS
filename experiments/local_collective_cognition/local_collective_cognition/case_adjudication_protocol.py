"""Protocol v0.14: current-case arguments and blinded third-party adjudication."""

from __future__ import annotations

from typing import Any

from .case_adjudication_policy import CaseAdjudicationPolicy
from .case_failure_policy import resolve_case_provider_failure
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .disagreement_case_runtime import DisagreementCaseRuntime
from .holdout_v12_benchmark import (
    HOLDOUT_V12_BENCHMARK_ID,
    HOLDOUT_V12_ITEM_DOMAINS,
    HOLDOUT_V12_ITEM_FINGERPRINTS,
)
from .iterated_context_protocol import IteratedContextResolutionProtocol


CASE_ADJUDICATION_PROTOCOL_VERSION = "current_case_argument_adjudication_protocol_v0_14"


class CaseAdjudicationProtocol(IteratedContextResolutionProtocol):
    def __init__(
        self, *, context_evidence_receipts, profiles, operator_credit_snapshot,
        operator_schedule, resolution_credit_snapshot, resolution_exploration_schedule,
        context_credit_snapshot, case_runtime=None, case_item_fingerprints=None,
        case_benchmark_id=HOLDOUT_V12_BENCHMARK_ID,
        case_protocol_version=CASE_ADJUDICATION_PROTOCOL_VERSION,
        case_source_actions=("PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"),
        **values: Any,
    ) -> None:
        if len(context_evidence_receipts) < 5:
            raise ValueError("case_adjudication_cycle_coverage_invalid")
        fingerprints = case_item_fingerprints or HOLDOUT_V12_ITEM_FINGERPRINTS
        if "policy" not in values:
            values["policy"] = CaseAdjudicationPolicy(
                operator_credit=operator_credit_snapshot, operator_schedule=operator_schedule,
                item_fingerprints=fingerprints,
                resolution_credit=resolution_credit_snapshot,
                exploration_items=tuple(resolution_exploration_schedule),
                context_credit=context_credit_snapshot, model_ids=tuple(profiles),
            )
        values.setdefault("item_domains", HOLDOUT_V12_ITEM_DOMAINS)
        values.setdefault("item_contexts", fingerprints)
        values.setdefault("arm_namespace", "HOLDOUT_V12")
        super().__init__(
            context_evidence_receipts=context_evidence_receipts, profiles=profiles,
            operator_credit_snapshot=operator_credit_snapshot, operator_schedule=operator_schedule,
            resolution_credit_snapshot=resolution_credit_snapshot,
            resolution_exploration_schedule=resolution_exploration_schedule,
            context_credit_snapshot=context_credit_snapshot, **values,
        )
        self.case_runtime = case_runtime or DisagreementCaseRuntime(self.base)
        self.case_item_fingerprints = dict(fingerprints)
        self.case_benchmark_id = case_benchmark_id
        self.case_protocol_version = case_protocol_version
        self.case_source_actions = tuple(case_source_actions)
        self._case_events = []
        self._case_failures = []

    def _resolve_post_disagreement(
        self, *, decision, primary_signal, peer_signal, proposal_by_model,
        item_id: str, domain: str, context: str,
    ):
        del domain
        if decision.action != "REQUEST_CASE_ADJUDICATION":
            return super()._resolve_post_disagreement(
                decision=decision, primary_signal=primary_signal, peer_signal=peer_signal,
                proposal_by_model=proposal_by_model, item_id=item_id,
                domain=self.item_domains[item_id], context=context,
            )
        witness_run = self.base.slice_item_run(proposal_by_model[decision.context_model_id], item_id)
        witness_signal = self._signal(witness_run, item_id, self.item_domains[item_id], context)
        try:
            bundle = self.case_runtime.adjudicate(
                primary=primary_signal, peer=peer_signal, witness=witness_signal,
            )
        except DisagreementCaseProviderFailure as exc:
            failure = {"item_id": item_id, **exc.as_dict()}
            self._case_failures.append(failure)
            resolved = resolve_case_provider_failure(
                decision=decision, primary=primary_signal, peer=peer_signal,
                witness=witness_signal, item_context=self.item_contexts[item_id],
                context_credit=self.context_credit_snapshot, failure=exc,
            )
            return resolved, (witness_run, *exc.runs)
        self._case_events.append(bundle)
        resolved = self.policy.resolve_case(
            decision, primary_signal, peer_signal, witness_signal, bundle,
        )
        return resolved, (
            witness_run, bundle.primary_argument_run, bundle.peer_argument_run, bundle.judge_run,
        )

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        self._case_events = []
        self._case_failures = []
        report = super().run(experiment_id, **values)
        report["protocol"].pop("v09_v10_v11_v12_context_outcomes_used_for_v13_route", None)
        report["protocol"].pop("v13_outcomes_used_for_current_route", None)
        report["protocol"].update({
            "protocol_version": self.case_protocol_version,
            "holdout_benchmark": self.case_benchmark_id,
            "v09_through_v13_context_outcomes_used_as_diagnostic_prior": True,
            "v14_outcomes_used_for_current_route": False,
            "historical_pair_credit_has_decision_authority": False,
            "current_case_arguments_provider_backed": True,
            "case_judge_truth_access": False,
            "candidate_argument_cross_exposure": False,
        })
        report["case_adjudication_events"] = [item.as_dict() for item in self._case_events]
        report["case_adjudication_failures"] = list(self._case_failures)
        solo = {item["model_ids"][0]: item["answer_vector"] for item in report["solo_arms"]}
        receipt = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-case-outcome",
            calibration_receipt_hash=self.context_credit_snapshot.snapshot_hash,
            route_decisions=tuple(report["route_decisions"]), solo_answer_vectors=solo,
            item_fingerprints=self.case_item_fingerprints,
            case_adjudication_source_actions=self.case_source_actions,
        )
        report["case_adjudication_outcome_receipt"] = receipt.as_dict()
        report["case_adjudication_arm"] = report.pop("iterated_context_resolution_arm")
        status = report["comparisons"].pop("iterated_context_resolution_improvement_status")
        decisions = tuple(report["route_decisions"])
        report["comparisons"].update({
            "case_adjudication_items": len(self._case_events) + len(self._case_failures),
            "case_adjudication_provider_failures": len(self._case_failures),
            "case_peer_overrides": sum(item["resolution_policy"] == "CASE_PEER_OVERRIDE" for item in decisions),
            "case_primary_keeps": sum(
                item["resolution_policy"] in {"CASE_KEEP_PRIMARY", "CASE_PROVIDER_FAILED_KEEP"}
                for item in decisions
            ),
            "case_corrections": receipt.corrections, "case_harms": receipt.harms,
            "case_observed_net_cbit": receipt.observed_net_cbit,
            "case_positive_heldout_net_cbit": receipt.observed_net_cbit > 0.0,
            "case_adjudication_improvement_status": status,
        })
        return report
