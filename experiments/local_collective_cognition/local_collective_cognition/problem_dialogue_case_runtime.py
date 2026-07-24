"""Run two isolated proposal-critique-revision threads before coordination."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .collective_protocol import RoleRun
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .local_problem_dialogue_provider import (
    PROBLEM_CRITIQUE_TASK_KIND, PROBLEM_REVISION_TASK_KIND,
)
from .problem_admission_gate import ProblemFormulationBudget
from .problem_dialogue_contracts import (
    critique_schema, revision_schema, validate_critique_receipt,
    validate_revision_receipt,
)
from .problem_dialogue_lineage_gate import ProblemDialogueLineageKernelGate
from .problem_formulation_case_runtime import ProblemFormulationCaseRuntime


class ProblemDialogueCaseRuntime(ProblemFormulationCaseRuntime):
    def __init__(self, base, *, problem_budget=None, plan_budget=None):
        budget = problem_budget or ProblemFormulationBudget(
            max_inference_passes=40, max_input_tokens=24000,
            coordinator_confidence_floor=0.65,
        )
        super().__init__(base, problem_budget=budget, plan_budget=plan_budget)
        self.lineage_gate = ProblemDialogueLineageKernelGate()
        self._critics = {}

    def adjudicate(self, *, primary, peer, witness):
        self._critics = {primary.model_id: peer.model_id, peer.model_id: primary.model_id}
        try:
            return super().adjudicate(primary=primary, peer=peer, witness=witness)
        finally:
            self._critics = {}

    def _problem_run(self, item_id, model_id, problem_candidate_id):
        proposal = super()._problem_run(item_id, model_id, problem_candidate_id)
        thread_id = "THREAD_1" if problem_candidate_id == "PROBLEM_1" else "THREAD_2"
        critic_id = self._critics[model_id]
        try:
            critique = self._execute(
                role_id=f"problem-critic-{critic_id}-{item_id}-{thread_id}",
                model_id=critic_id, task_kind=PROBLEM_CRITIQUE_TASK_KIND,
                objective=("Challenge the proposed cognitive object against the public task. "
                           "Name the decisive flaw dimension and provide one complete replacement object."),
                item_id=item_id,
                round_context={
                    "role": "isolated_problem_critic", "thread_id": thread_id,
                    "source_problem_receipt": proposal.result["problem_receipt"],
                    "suggested_problem_candidate_id": problem_candidate_id + "_CRITIC",
                },
                schema=critique_schema(item_id, thread_id), stage="PROBLEM_CRITIQUE",
            )
            self._validate_critique(critique, proposal)
            revision = self._execute(
                role_id=f"problem-reviser-{model_id}-{item_id}-{thread_id}",
                model_id=model_id, task_kind=PROBLEM_REVISION_TASK_KIND,
                objective=("Reconsider the original cognitive object after the independent critique. "
                           "Keep it, accept the complete critic replacement, or abstain."),
                item_id=item_id,
                round_context={
                    "role": "problem_proposer_revision", "thread_id": thread_id,
                    "source_problem_receipt": proposal.result["problem_receipt"],
                    "critique_receipt": critique.result["critique_receipt"],
                    "suggested_problem_receipt": critique.result["suggested_problem_receipt"],
                    "final_problem_candidate_id": problem_candidate_id + "_ABSTAIN",
                },
                schema=revision_schema(item_id, thread_id), stage="PROBLEM_REVISION",
            )
            self._validate_revision(revision, proposal, critique)
        except DisagreementCaseProviderFailure as exc:
            raise exc.prepend((proposal,)) from exc
        except (KeyError, ValueError) as exc:
            failed = critique if "critique" in locals() else proposal
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_DIALOGUE_VALIDATION", run=failed,
                failures=(type(exc).__name__ + ":" + str(exc),),
            ).prepend((proposal,) if failed is not proposal else ()) from exc
        source = proposal.result["problem_receipt"]
        suggested = critique.result["suggested_problem_receipt"]
        final = revision.result["final_problem_receipt"]
        lineage = self.lineage_gate.evaluate(
            thread_id=thread_id, source_problem=source, suggested_problem=suggested,
            critique_receipt=critique.result["critique_receipt"],
            revision_receipt=revision.result["revision_receipt"], final_problem=final,
        )
        aggregate = _merge_dialogue_runs(proposal, critique, revision, {
            "problem_candidate_id": problem_candidate_id,
            "problem_receipt": final, "problem_definition_receipt": final,
            "decision_receipt": revision.result["decision_receipt"],
            "problem_decision_receipt": revision.result["decision_receipt"],
            "problem_proposal_receipt": source,
            "problem_critique_receipt": critique.result["critique_receipt"],
            "problem_critic_suggestion_receipt": suggested,
            "problem_revision_receipt": revision.result["revision_receipt"],
            "problem_dialogue_lineage_receipt": lineage,
            "problem_dialogue_final_receipt": final,
            "problem_dialogue_decision_receipts": [
                proposal.result["decision_receipt"], critique.result["decision_receipt"],
                revision.result["decision_receipt"],
            ],
            **{key: final[key] for key in (
                "intent_mode", "problem_family", "target_kind", "critical_constraint",
            )},
        })
        if lineage["status"] != "ALLOW":
            raise DisagreementCaseProviderFailure(
                stage="PROBLEM_DIALOGUE_LINEAGE", run=aggregate,
                failures=tuple(lineage["reasons"]),
            )
        return aggregate

    def _bound_plan(self, problem_run, admission, item_id, model_id, candidate_id, label):
        plan = super()._bound_plan(
            problem_run, admission, item_id, model_id, candidate_id, label,
        )
        keys = (
            "problem_proposal_receipt", "problem_critique_receipt",
            "problem_critic_suggestion_receipt", "problem_revision_receipt",
            "problem_dialogue_lineage_receipt", "problem_dialogue_final_receipt",
            "problem_dialogue_decision_receipts",
        )
        return RoleRun(
            role_id=plan.role_id, model_id=plan.model_id,
            result={**plan.result, **{key: problem_run.result[key] for key in keys}},
            tasks=plan.tasks, audits=plan.audits, telemetry=plan.telemetry,
        )

    @staticmethod
    def _problem_work(runs):
        decisions, seen = [], set()
        for run in runs:
            values = run.result.get("problem_dialogue_decision_receipts", ())
            if not values and run.result.get("decision_receipt"):
                values = (run.result["decision_receipt"],)
            for receipt in values:
                if receipt["receipt_hash"] not in seen:
                    seen.add(receipt["receipt_hash"]); decisions.append(receipt)
        return {
            "inference_passes": sum(item["inference_passes"] for item in decisions),
            "input_tokens": sum(item.input_tokens for run in runs for item in run.telemetry),
        }

    @staticmethod
    def _validate_critique(critique, proposal):
        validate_critique_receipt(
            critique.result["critique_receipt"], task=critique.tasks[-1],
            decision_receipt=critique.result["decision_receipt"],
            source_problem=proposal.result["problem_receipt"],
            suggested_problem=critique.result["suggested_problem_receipt"],
        )

    @staticmethod
    def _validate_revision(revision, proposal, critique):
        validate_calibrated_score_receipt(
            revision.result["decision_receipt"], task=revision.tasks[-1],
        )
        validate_revision_receipt(
            revision.result["revision_receipt"], task=revision.tasks[-1],
            decision_receipt=revision.result["decision_receipt"],
            source_problem=proposal.result["problem_receipt"],
            critique_receipt=critique.result["critique_receipt"],
            suggested_problem=critique.result["suggested_problem_receipt"],
            final_problem=revision.result["final_problem_receipt"],
        )


def _merge_dialogue_runs(proposal, critique, revision, result):
    return RoleRun(
        role_id=revision.role_id, model_id=revision.model_id, result=result,
        tasks=(*proposal.tasks, *critique.tasks, *revision.tasks),
        audits=(*proposal.audits, *critique.audits, *revision.audits),
        telemetry=(*proposal.telemetry, *critique.telemetry, *revision.telemetry),
    )
