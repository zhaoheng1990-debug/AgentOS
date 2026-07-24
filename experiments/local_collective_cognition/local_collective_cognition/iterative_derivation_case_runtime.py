"""Bounded multi-turn candidate revision with immediate Harness step execution."""

from __future__ import annotations

from .candidate_revision_case_runtime import CandidateRevisionCaseRuntime
from .collective_protocol import RoleRun
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .iterative_derivation_contracts import iterative_action_schema, validate_iterative_action
from .iterative_derivation_receipt import IterativeDerivationVerifier


class IterativeDerivationCaseRuntime(CandidateRevisionCaseRuntime):
    def __init__(self, base, *, max_steps: int = 8, max_turns: int = 11,
                 max_invalid_actions: int = 1) -> None:
        super().__init__(base)
        if not 1 <= max_steps < max_turns or max_invalid_actions < 0:
            raise ValueError("iterative_derivation_limits_invalid")
        self.max_steps = max_steps
        self.max_turns = max_turns
        self.max_invalid_actions = max_invalid_actions
        self.verifier = IterativeDerivationVerifier()

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        scaffold = self.base.harness.derivation_scaffold(item_id)
        symbol_values = dict(scaffold)
        step_receipts, runs, actions = [], [], []
        invalid_actions, last_error = 0, ""
        for turn in range(1, self.max_turns + 1):
            available = tuple(symbol_values)
            try:
                run = self._execute(
                    role_id=f"iterative-derivation-{model_id}-{item_id}-turn-{turn}",
                    model_id=model_id, task_kind="pilot_disagreement_argument",
                    objective=(
                        "Take exactly one derivation action. APPLY one operator to available symbols, "
                        "FINALIZE one existing STEP with A/B/C/D, or ABSTAIN. For APPLY use PENDING. "
                        "Return no formula, prose, additional step, or unavailable symbol."
                    ), item_id=item_id,
                    round_context={"role": "iterative_candidate_revision", "candidate_id": candidate_id,
                                   "original_candidate": candidate_label, "turn": turn,
                                   "available_symbols": symbol_values,
                                   "completed_steps": [item.as_dict() for item in step_receipts],
                                   "last_action_error": last_error, "peer_output": "withheld"},
                    schema=iterative_action_schema(item_id, candidate_id, available), stage="ACTION",
                )
            except DisagreementCaseProviderFailure as exc:
                raise exc.prepend(tuple(runs)) from exc
            runs.append(run)
            actions.append(run.result)
            try:
                validate_iterative_action(
                    run.result, item_id=item_id, candidate_id=candidate_id,
                    evidence_refs=list(self.base.harness.evidence_refs),
                    available_symbols=available,
                )
                if run.result["action"] == "APPLY":
                    if len(step_receipts) >= self.max_steps:
                        raise ValueError("iterative_derivation_step_limit")
                    receipt = self.base.harness.execute_derivation_step(
                        item_id=item_id, candidate_id=candidate_id,
                        step_id=f"STEP_{len(step_receipts) + 1}", action=run.result,
                        symbol_values=symbol_values,
                    )
                    step_receipts.append(receipt)
                    symbol_values[receipt.step_id] = receipt.result
                    last_error = ""
                    continue
                final = self.base.harness.finalize_derivation_session(
                    item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, action=run.result,
                    step_receipts=tuple(step_receipts), provider_turns=turn,
                    invalid_actions=invalid_actions,
                )
                return self._aggregate(
                    runs, item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, actions=actions,
                    step_receipts=step_receipts, final_receipt=final,
                    invalid_actions=invalid_actions,
                )
            except (ValueError, ZeroDivisionError) as exc:
                invalid_actions += 1
                last_error = type(exc).__name__ + ":" + str(exc)
                if invalid_actions > self.max_invalid_actions:
                    failed = self._aggregate(
                        runs, item_id=item_id, candidate_id=candidate_id,
                        original_candidate=candidate_label, actions=actions,
                        step_receipts=step_receipts, failure=last_error,
                        invalid_actions=invalid_actions,
                    )
                    raise DisagreementCaseProviderFailure(
                        stage="ACTION", run=failed, failures=(last_error,),
                    ) from exc
        failed = self._aggregate(
            runs, item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, actions=actions,
            step_receipts=step_receipts, failure="iterative_derivation_turn_limit",
            invalid_actions=invalid_actions,
        )
        raise DisagreementCaseProviderFailure(
            stage="SESSION_LIMIT", run=failed, failures=("iterative_derivation_turn_limit",),
        )

    @staticmethod
    def _aggregate(runs, *, item_id, candidate_id, original_candidate, actions,
                   step_receipts, final_receipt=None, failure="", invalid_actions=0,
                   session_metrics=None, result_extras=None):
        metrics = {"session_provider_turns": len(runs),
                   "session_applied_steps": len(step_receipts),
                   "session_invalid_actions": invalid_actions,
                   **(session_metrics or {})}
        return RoleRun(
            role_id=f"iterative-session-{candidate_id}-{item_id}", model_id=runs[0].model_id,
            result={"item_id": item_id, "candidate_id": candidate_id,
                    "original_candidate": original_candidate, "actions": list(actions),
                    "step_receipts": [item.as_dict() for item in step_receipts],
                    "final_receipt": final_receipt.as_dict() if final_receipt else {},
                    "failure": failure, **metrics, **(result_extras or {})},
            tasks=tuple(task for run in runs for task in run.tasks),
            audits=tuple(audit for run in runs for audit in run.audits),
            telemetry=tuple(item for run in runs for item in run.telemetry),
        )

    @staticmethod
    def _record(candidate_id, candidate_label, argument, receipt):
        return {"candidate_id": candidate_id, "candidate_label": receipt.proposed_candidate,
                "original_candidate": candidate_label, "proposed_candidate": receipt.proposed_candidate,
                "action_trace": argument["actions"], "step_receipts": argument["step_receipts"],
                "verification_receipt": receipt.as_dict()}
