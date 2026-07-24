"""Coordinate a problem object before constructing and judging candidate plans."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .collective_protocol import RoleRun
from .disagreement_case_contracts import judgment_schema, validate_judgment
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .local_plan_intent_provider import PLAN_INTENT_JUDGE_ROLE
from .local_problem_formulation_provider import (
    PROBLEM_COORDINATOR_ROLE, PROBLEM_FORMULATION_TASK_KIND,
)
from .plan_intent_case_runtime import PlanIntentCaseRuntime
from .problem_admission_gate import ProblemAdmissionKernelGate
from .problem_formulation_contracts import (
    coordination_schema, problem_definition_schema, validate_coordination_receipt,
    validate_problem_definition_receipt,
)
from .provider_telemetry import hash_payload
from .verified_case_runtime import VerifiedCaseBundle


class ProblemFormulationCaseRuntime(PlanIntentCaseRuntime):
    judge_role = PLAN_INTENT_JUDGE_ROLE

    def __init__(self, base, *, problem_budget=None, plan_budget=None):
        super().__init__(base, budget=plan_budget)
        self.problem_gate = ProblemAdmissionKernelGate(budget=problem_budget)

    def adjudicate(self, *, primary, peer, witness):
        if len({primary.model_id, peer.model_id, witness.model_id}) != 3 or not (
            primary.item_id == peer.item_id == witness.item_id
        ):
            raise ValueError("problem_formulation_case_identity_invalid")
        item_id = primary.item_id
        primary_id, peer_id = self._candidate_ids(item_id)
        problem_runs = []
        try:
            problem_runs.append(self._problem_run(item_id, primary.model_id, "PROBLEM_1"))
            problem_runs.append(self._problem_run(item_id, peer.model_id, "PROBLEM_2"))
            coordination = self._coordination_run(item_id, witness.model_id, problem_runs)
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend(tuple(problem_runs)) from exc
        candidate_receipts = [item.result["problem_receipt"] for item in problem_runs]
        problem_work = self._problem_work((*problem_runs, coordination))
        admission = self.problem_gate.evaluate(
            candidate_receipts=candidate_receipts,
            coordination_receipt=coordination.result["coordination_receipt"], **problem_work,
        )
        if admission["status"] != "ALLOW":
            blocked = _extend_run(coordination, {"problem_admission_receipt": admission})
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_ADMISSION", run=blocked, failures=tuple(admission["reasons"]),
            ).prepend(tuple(problem_runs))
        try:
            primary_plan = self._bound_plan(
                problem_runs[0], admission, item_id, primary.model_id, primary_id, primary.answer,
            )
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend((*problem_runs, coordination)) from exc
        try:
            peer_plan = self._bound_plan(
                problem_runs[1], admission, item_id, peer.model_id, peer_id, peer.answer,
            )
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend((primary_plan, problem_runs[1], coordination)) from exc
        receipts = (
            self.verifier.verify(item_id=item_id, candidate_id=primary_id,
                                 candidate_label=primary.answer, argument=primary_plan.result),
            self.verifier.verify(item_id=item_id, candidate_id=peer_id,
                                 candidate_label=peer.answer, argument=peer_plan.result),
        )
        records = sorted((
            self._problem_record(primary_id, primary.answer, primary_plan.result, receipts[0]),
            self._problem_record(peer_id, peer.answer, peer_plan.result, receipts[1]),
        ), key=lambda item: item["candidate_id"])
        try:
            judge = self._execute(
                role_id=f"problem-plan-judge-{witness.model_id}-{item_id}",
                model_id=witness.model_id, task_kind="pilot_disagreement_adjudication",
                objective=("Judge anonymous candidates only after checking admitted problem, "
                           "problem-plan binding, and Harness replay. Otherwise abstain."),
                item_id=item_id,
                round_context={"role": self.judge_role, "candidate_records": records,
                               "independent_witness_label": witness.answer,
                               "problem_admission_receipt": admission},
                schema=judgment_schema(item_id), stage="JUDGE",
            )
            validate_judgment(judge.result, item_id, list(self.base.harness.evidence_refs))
            validate_calibrated_score_receipt(judge.result["decision_receipt"], task=judge.tasks[-1])
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend((primary_plan, peer_plan, coordination)) from exc
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="JUDGE", run=judge, failures=(str(exc),),
            ).prepend((primary_plan, peer_plan, coordination)) from exc
        judge = _merge_runs(
            coordination, judge,
            {"problem_admission_receipt": admission,
             "problem_coordination_decision_receipt": coordination.result["decision_receipt"],
             "problem_coordination_receipt": coordination.result["coordination_receipt"]},
        )
        return VerifiedCaseBundle(
            item_id=item_id, primary_model_id=primary.model_id, peer_model_id=peer.model_id,
            judge_model_id=witness.model_id, primary_candidate_id=primary_id,
            peer_candidate_id=peer_id, primary_argument_run=primary_plan,
            peer_argument_run=peer_plan, judge_run=judge, verification_receipts=receipts,
            argument_hashes=(hash_payload(primary_plan.result), hash_payload(peer_plan.result)),
            judgment_hash=hash_payload(judge.result),
        )

    def _problem_run(self, item_id, model_id, problem_candidate_id):
        run = self._execute(
            role_id=f"problem-definition-{model_id}-{item_id}", model_id=model_id,
            task_kind=PROBLEM_FORMULATION_TASK_KIND,
            objective=("Define the cognitive object before planning: mode, problem family, "
                       "target quantity, and most important public constraint."),
            item_id=item_id,
            round_context={"role": "isolated_problem_definer",
                           "problem_candidate_id": problem_candidate_id,
                           "peer_problem": "withheld"},
            schema=problem_definition_schema(item_id, problem_candidate_id),
            stage="PROBLEM_DEFINITION",
        )
        try:
            validate_problem_definition_receipt(
                run.result["problem_receipt"], task=run.tasks[-1],
                decision_receipt=run.result["decision_receipt"],
            )
        except (KeyError, ValueError) as exc:
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_DEFINITION", run=run, failures=(str(exc),),
            ) from exc
        return run

    def _coordination_run(self, item_id, model_id, problem_runs):
        candidates = [_problem_record(item.result) for item in problem_runs]
        run = self._execute(
            role_id=f"problem-coordinator-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_adjudication",
            objective=("Compare two anonymous problem definitions against the public task. "
                       "Select the better cognitive object or abstain."), item_id=item_id,
            round_context={"role": PROBLEM_COORDINATOR_ROLE,
                           "problem_candidates": candidates},
            schema=coordination_schema(item_id), stage="PROBLEM_COORDINATION",
        )
        try:
            validate_coordination_receipt(
                run.result["coordination_receipt"], task=run.tasks[-1],
                decision_receipt=run.result["decision_receipt"],
                candidate_receipts=[item["problem_receipt"] for item in candidates],
            )
        except (KeyError, ValueError) as exc:
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_COORDINATION", run=run, failures=(str(exc),),
            ) from exc
        return run

    def _bound_plan(self, problem_run, admission, item_id, model_id, candidate_id, label):
        plan = self._evidence_run(
            item_id, model_id, candidate_id, label, problem_admission=admission,
        )
        binding = self.problem_gate.bind_plan(
            admission_receipt=admission, plan_receipt=plan.result["plan_intent_receipt"],
        )
        plan = _merge_runs(problem_run, plan, {
            "problem_decision_receipt": problem_run.result["decision_receipt"],
            "problem_definition_receipt": problem_run.result["problem_receipt"],
            "problem_admission_receipt": admission, "problem_plan_binding_receipt": binding,
        })
        if binding["status"] != "ALLOW":
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_PLAN_BINDING", run=plan, failures=tuple(binding["reasons"]),
            )
        return plan

    @staticmethod
    def _problem_record(candidate_id, candidate_label, argument, receipt):
        record = PlanIntentCaseRuntime._record(candidate_id, candidate_label, argument, receipt)
        return {**record, "problem_definition_receipt": argument["problem_definition_receipt"],
                "problem_plan_binding_receipt": argument["problem_plan_binding_receipt"]}

    @staticmethod
    def _problem_work(runs):
        decisions = [run.result["decision_receipt"] for run in runs]
        return {"inference_passes": sum(item["inference_passes"] for item in decisions),
                "input_tokens": sum(item.input_tokens for run in runs for item in run.telemetry)}


def _problem_record(result):
    return {key: result[key] for key in (
        "problem_candidate_id", "intent_mode", "problem_family", "target_kind",
        "critical_constraint", "problem_receipt",
    )}


def _extend_run(run, extras):
    return RoleRun(role_id=run.role_id, model_id=run.model_id,
                   result={**run.result, **extras}, tasks=run.tasks,
                   audits=run.audits, telemetry=run.telemetry)


def _merge_runs(prefix, run, extras):
    return RoleRun(role_id=run.role_id, model_id=run.model_id,
                   result={**run.result, **extras}, tasks=(*prefix.tasks, *run.tasks),
                   audits=(*prefix.audits, *run.audits),
                   telemetry=(*prefix.telemetry, *run.telemetry))
