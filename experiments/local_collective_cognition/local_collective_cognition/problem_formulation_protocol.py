"""Protocol v0.24: admitted problem objects precede global plan intent."""

from __future__ import annotations

from .holdout_v22_benchmark import (
    HOLDOUT_V22_BENCHMARK_ID, HOLDOUT_V22_ITEM_DOMAINS, HOLDOUT_V22_ITEM_FINGERPRINTS,
    HOLDOUT_V22_ROUTING_FINGERPRINTS,
)
from .plan_intent_protocol import PlanIntentProtocol
from .problem_formulation_case_runtime import ProblemFormulationCaseRuntime
from .problem_formulation_metrics import problem_formulation_metrics


PROBLEM_FORMULATION_PROTOCOL_VERSION = "problem_formulation_admission_protocol_v0_24"


class ProblemFormulationProtocol(PlanIntentProtocol):
    def __init__(self, *, base, **values):
        super().__init__(
            base=base, case_runtime=ProblemFormulationCaseRuntime(base),
            case_item_fingerprints=HOLDOUT_V22_ITEM_FINGERPRINTS,
            case_benchmark_id=HOLDOUT_V22_BENCHMARK_ID,
            case_protocol_version=PROBLEM_FORMULATION_PROTOCOL_VERSION,
            item_domains=HOLDOUT_V22_ITEM_DOMAINS,
            item_contexts=HOLDOUT_V22_ITEM_FINGERPRINTS,
            routing_fingerprints=HOLDOUT_V22_ROUTING_FINGERPRINTS,
            arm_namespace="HOLDOUT_V22", **values,
        )

    def run(self, experiment_id, **values):
        report = super().run(experiment_id, **values)
        report["protocol"].update({
            "protocol_version": PROBLEM_FORMULATION_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V22_BENCHMARK_ID,
            "v23_outcomes_used_as_diagnostic_prior": True,
            "v24_outcomes_used_for_current_route": False,
            "isolated_problem_definers": 2, "provider_backed_problem_coordinator": True,
            "problem_admission_kernel_owned": True,
            "problem_plan_action_lineage_required": True,
            "problem_definition_truth_access": False,
            "problem_coordinator_truth_access": False,
            "problem_or_provider_has_final_candidate_authority": False,
        })
        report["problem_formulation_arm"] = report.pop("plan_intent_arm")
        admissions = _unique_admissions(
            report["case_adjudication_events"], report["case_adjudication_failures"],
        )
        audit = self.base.harness.audit_problem_definitions(
            experiment_id=experiment_id + "-problem-definition", admission_receipts=admissions,
            candidate_receipts=_problem_candidates(
                report["case_adjudication_events"], report["case_adjudication_failures"],
            ),
        )
        report["problem_definition_outcome_receipt"] = audit
        report["comparisons"].update(problem_formulation_metrics(
            report["case_adjudication_events"], report["case_adjudication_failures"],
            audit, report["comparisons"],
        ))
        return report


def _unique_admissions(events, failures):
    values = [event["judgment"]["problem_admission_receipt"] for event in events]
    values += [item for failure in failures
               for item in failure.get("failed_problem_admission_receipts", ())
               if item.get("status") == "ALLOW"]
    result, seen = [], set()
    for item in values:
        if item["receipt_hash"] not in seen:
            seen.add(item["receipt_hash"]); result.append(item)
    return tuple(result)


def _problem_candidates(events, failures):
    values = [session["problem_definition_receipt"] for event in events
              for session in (event["primary_argument"], event["peer_argument"])]
    values += [item for failure in failures
               for item in failure.get("failed_problem_definition_receipts", ())]
    return tuple(values)
