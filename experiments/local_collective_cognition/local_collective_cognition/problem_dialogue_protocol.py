"""Protocol v0.25: dialogical problem discovery before admission and planning."""

from __future__ import annotations

from .holdout_v23_benchmark import (
    HOLDOUT_V23_BENCHMARK_ID, HOLDOUT_V23_ITEM_DOMAINS,
    HOLDOUT_V23_ITEM_FINGERPRINTS, HOLDOUT_V23_ROUTING_FINGERPRINTS,
)
from .plan_intent_protocol import PlanIntentProtocol
from .problem_dialogue_case_runtime import ProblemDialogueCaseRuntime
from .problem_dialogue_metrics import problem_dialogue_metrics


PROBLEM_DIALOGUE_PROTOCOL_VERSION = "provider_backed_problem_dialogue_protocol_v0_25"


class ProblemDialogueProtocol(PlanIntentProtocol):
    def __init__(self, *, base, **values):
        super().__init__(
            base=base, case_runtime=ProblemDialogueCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V23_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V23_BENCHMARK_ID,
            case_protocol_version=PROBLEM_DIALOGUE_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V23_ITEM_DOMAINS,
            item_contexts=HOLDOUT_V23_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V23_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V23", **values,
        )

    def run(self, experiment_id, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": PROBLEM_DIALOGUE_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V23_BENCHMARK_ID,
            "v24_outcomes_used_as_diagnostic_prior": True,
            "v25_outcomes_used_for_current_route": False,
            "problem_dialogue_threads_per_case": 2,
            "problem_dialogue_stages": ["PROPOSAL", "CRITIQUE", "REVISION"],
            "cross_thread_problem_coordinator": True,
            "problem_dialogue_lineage_kernel_owned": True,
            "problem_admission_kernel_owned": True,
            "problem_plan_action_lineage_required": True,
            "dialogue_roles_context_isolated": True,
            "dialogue_truth_access": False,
            "provider_problem_or_plan_has_final_authority": False,
        })
        report["problem_dialogue_arm"] = report.pop("plan_intent_arm")
        events, failures = (
            report["case_adjudication_events"], report["case_adjudication_failures"],
        )
        audit = self.base.harness.audit_problem_dialogue(
            experiment_id=experiment_id + "-problem-dialogue",
            admission_receipts=_unique_admissions(events, failures),
            proposal_receipts=_receipts(events, failures, "problem_proposal_receipt",
                                        "failed_problem_proposal_receipts"),
            suggestion_receipts=_receipts(
                events, failures, "problem_critic_suggestion_receipt",
                "failed_problem_critic_suggestion_receipts",
            ),
            final_receipts=_receipts(events, failures, "problem_dialogue_final_receipt",
                                     "failed_problem_dialogue_final_receipts"),
        )
        report["problem_dialogue_outcome_receipt"] = audit
        report["comparisons"].update(problem_dialogue_metrics(
            events, failures, audit, report["comparisons"],
        ))
        return report


def _sessions(events):
    return [record for event in events
            for record in (event["primary_argument"], event["peer_argument"])]


def _receipts(events, failures, event_key, failure_key):
    values = [item[event_key] for item in _sessions(events) if item.get(event_key)]
    values += [receipt for failure in failures for receipt in failure.get(failure_key, ())]
    return _unique(values)


def _unique_admissions(events, failures):
    values = [event["judgment"]["problem_admission_receipt"] for event in events]
    values += [receipt for failure in failures
               for receipt in failure.get("failed_problem_admission_receipts", ())
               if receipt.get("status") == "ALLOW"]
    return _unique(values)


def _unique(values):
    result, seen = [], set()
    for item in values:
        if item["receipt_hash"] not in seen:
            seen.add(item["receipt_hash"]); result.append(item)
    return tuple(result)
