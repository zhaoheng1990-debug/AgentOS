"""Build a global plan intent, then admit its local actions through a Kernel gate."""

from __future__ import annotations

from .calibrated_score_receipt import validate_calibrated_score_receipt
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .hierarchical_tool_channel import build_hierarchical_channel
from .iterative_derivation_case_runtime import IterativeDerivationCaseRuntime
from .local_plan_intent_provider import PLAN_INTENT_JUDGE_ROLE, PLAN_INTENT_TASK_KIND
from .plan_consistency_gate import PlanConsistencyKernelGate, PlanIntentBudget
from .plan_intent_contracts import (
    build_plan_intent_receipt, plan_action_schema, validate_plan_action,
)
from .typed_derivation_contracts import BINARY_OPERATORS, UNARY_OPERATORS


class PlanIntentCaseRuntime(IterativeDerivationCaseRuntime):
    judge_role = PLAN_INTENT_JUDGE_ROLE

    def __init__(self, base, *, budget=None):
        self.budget = budget or PlanIntentBudget()
        super().__init__(base, max_steps=self.budget.max_turns - 1,
                         max_turns=self.budget.max_turns, max_invalid_actions=0)
        self.gate = PlanConsistencyKernelGate(base.harness, budget=self.budget)

    def _evidence_run(self, item_id, model_id, candidate_id, candidate_label,
                      problem_admission=None):
        initial = dict(self.base.harness.derivation_scaffold(item_id))
        symbols = dict(initial)
        previews, runs, actions, score_receipts = [], [], [], []
        admitted_problem = (problem_admission or {}).get("selected_problem", {})
        intent_mode = admitted_problem.get("intent_mode", "")
        for turn in range(1, self.max_turns + 1):
            channel = build_hierarchical_channel(
                symbol_values=symbols, prior_actions=actions,
                allow_apply=len(previews) < self.max_steps,
            )
            try:
                run = self._execute(
                    role_id=f"plan-intent-{model_id}-{item_id}-turn-{turn}",
                    model_id=model_id, task_kind=PLAN_INTENT_TASK_KIND,
                    objective=(
                        "Construct one globally coherent derivation plan. Commit a numeric or string "
                        "mode, add only steps needed by the public question, and finalize the last "
                        "planned step only when it exactly supports a public answer."
                    ), item_id=item_id,
                    round_context={"role": "global_plan_intent_builder",
                                   "candidate_id": candidate_id,
                                   "original_candidate": candidate_label, "turn": turn,
                                   "plan_intent_mode": intent_mode,
                                   "problem_admission_hash": (problem_admission or {}).get(
                                       "receipt_hash", ""),
                                   "admitted_problem_definition": admitted_problem,
                                   "available_symbols": symbols,
                                   "planned_steps": [item.as_dict() for item in previews],
                                   "hierarchical_tool_channel": channel,
                                   "peer_output": "withheld"},
                    schema=plan_action_schema(item_id, candidate_id, tuple(symbols)),
                    stage="PLAN_INTENT",
                )
            except DisagreementCaseProviderFailure as exc:
                self._raise_failure((*runs, *exc.runs), item_id, candidate_id,
                                    candidate_label, actions, previews, score_receipts,
                                    ";".join(exc.failures), intent_mode)
            runs.append(run)
            try:
                score = run.result["decision_receipt"]
                validate_calibrated_score_receipt(score, task=run.tasks[-1])
                score_receipts.append(score)
                action = validate_plan_action(
                    run.result, item_id=item_id, candidate_id=candidate_id,
                    evidence_refs=list(self.base.harness.evidence_refs),
                    available_symbols=tuple(symbols),
                )
                current_mode = run.result["intent_mode"]
                if intent_mode and current_mode != intent_mode:
                    raise ValueError("plan_intent_mode_drift")
                intent_mode = current_mode
                self._check_local_mode(intent_mode, action)
                work = self._work(runs, score_receipts)
                if work["session_plan_input_tokens"] > self.budget.max_input_tokens:
                    reason = "plan_input_token_budget_exceeded"
                    budget_receipt = self.gate.budget_stop_receipt(
                        item_id=item_id, candidate_id=candidate_id, turns=len(runs),
                        inference_passes=work["session_plan_inference_passes"],
                        input_tokens=work["session_plan_input_tokens"], reason=reason,
                    )
                    self._raise_failure(
                        runs, item_id, candidate_id, candidate_label, actions, previews,
                        score_receipts, reason, intent_mode,
                        extras={"decision_receipts": list(score_receipts),
                                "plan_budget_receipt": budget_receipt},
                    )
                if action["action"] == "APPLY":
                    preview = self.base.harness.execute_derivation_step(
                        item_id=item_id, candidate_id=candidate_id,
                        step_id=f"STEP_{len(previews) + 1}", action=action,
                        symbol_values=symbols,
                    )
                    actions.append(action)
                    previews.append(preview)
                    symbols[preview.step_id] = preview.result
                    continue
                return self._close_plan(
                    runs, item_id, candidate_id, candidate_label, intent_mode,
                    actions, action, previews, score_receipts, initial,
                )
            except (KeyError, ValueError, ZeroDivisionError) as exc:
                self._raise_failure(
                    runs, item_id, candidate_id, candidate_label, actions, previews,
                    score_receipts, type(exc).__name__ + ":" + str(exc), intent_mode,
                )
        self._raise_failure(runs, item_id, candidate_id, candidate_label, actions,
                            previews, score_receipts, "plan_intent_turn_budget_exhausted",
                            intent_mode)

    def _close_plan(self, runs, item_id, candidate_id, candidate_label, mode,
                    actions, terminal, previews, scores, initial):
        tasks = [task for run in runs for task in run.tasks]
        work = self._work(runs, scores)
        plan = build_plan_intent_receipt(
            item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, intent_mode=mode,
            planned_actions=actions, terminal_action=terminal,
            score_receipts=scores, tasks=tasks, preview_receipts=previews,
            evidence_refs=self.base.harness.evidence_refs, initial_state=initial,
            provider_id=scores[0]["provider_id"], model_id=scores[0]["model_id"],
            input_tokens=work["session_plan_input_tokens"],
        )
        outcome = self.gate.evaluate(receipt=plan, preview_receipts=tuple(previews))
        extras = {"decision_receipts": list(scores), "plan_intent_receipt": plan,
                  "plan_gate_receipt": outcome.gate_receipt,
                  "planning_preview_receipts": [item.as_dict() for item in previews]}
        if outcome.status != "ALLOW":
            aggregate = self._aggregate_run(
                runs, item_id, candidate_id, candidate_label, actions, previews,
                scores, mode, failure=";".join(outcome.reasons), extras=extras,
            )
            raise DisagreementCaseProviderFailure(
                stage="PLAN_CONSISTENCY_GATE", run=aggregate,
                failures=outcome.reasons,
            )
        return self._aggregate_run(
            runs, item_id, candidate_id, candidate_label, actions, previews,
            scores, mode, final=outcome.final_receipt, extras=extras,
        )

    def _aggregate_run(self, runs, item_id, candidate_id, candidate_label, actions,
                       previews, scores, mode, final=None, failure="", extras=None):
        work = self._work(runs, scores)
        return self._aggregate(
            runs, item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, actions=actions,
            step_receipts=previews, final_receipt=final, failure=failure,
            session_metrics={**work, "session_plan_mode": mode,
                             "session_plan_steps": len(actions)},
            result_extras=extras,
        )

    def _raise_failure(self, runs, item_id, candidate_id, candidate_label,
                       actions, previews, scores, failure, mode, extras=None):
        aggregate = self._aggregate_run(
            runs, item_id, candidate_id, candidate_label, actions, previews,
            scores, mode, failure=failure,
            extras=extras or {"decision_receipts": list(scores)},
        )
        raise DisagreementCaseProviderFailure(
            stage="PLAN_INTENT", run=aggregate, failures=(failure,),
        )

    @staticmethod
    def _check_local_mode(mode, action):
        if action["action"] != "APPLY":
            return
        allowed = BINARY_OPERATORS if mode == "NUMERIC_DERIVATION" else UNARY_OPERATORS
        if mode == "ABSTAIN" or action["operator"] not in allowed:
            raise ValueError("plan_local_action_mode_mismatch")

    @staticmethod
    def _work(runs, scores):
        return {"session_plan_score_receipts": len(scores),
                "session_plan_menu_options": sum(item["menu_option_total"] for item in scores),
                "session_plan_inference_passes": sum(item["inference_passes"] for item in scores),
                "session_plan_input_tokens": sum(
                    item.input_tokens for run in runs for item in run.telemetry
                )}
