"""Bounded two-stage derivation with action-specific Provider contracts."""

from __future__ import annotations

from .disagreement_case_failure import DisagreementCaseProviderFailure
from .iterative_derivation_case_runtime import IterativeDerivationCaseRuntime
from .staged_derivation_contracts import (
    arguments_schema, normalized_action, selection_schema,
    validate_arguments, validate_selection,
)


class StagedDerivationCaseRuntime(IterativeDerivationCaseRuntime):
    def __init__(self, base, *, max_steps=8, max_control_turns=11,
                 max_invalid_actions=1) -> None:
        super().__init__(base, max_steps=max_steps, max_turns=max_control_turns,
                         max_invalid_actions=max_invalid_actions)

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        symbol_values = dict(self.base.harness.derivation_scaffold(item_id))
        steps, runs, actions = [], [], []
        controls = arguments = invalid_controls = invalid_arguments = 0
        last_error = ""
        for cycle in range(1, self.max_turns + 1):
            available = tuple(symbol_values)
            controls += 1
            selection = self._call_or_fail(
                runs=runs, stage="CONTROL", item_id=item_id, model_id=model_id,
                candidate_id=candidate_id, candidate_label=candidate_label,
                role_id=f"staged-control-{model_id}-{item_id}-turn-{cycle}",
                objective="Select exactly one next action: APPLY, FINALIZE, or ABSTAIN.",
                context={"role": "staged_action_selection", "control_turn": cycle,
                         "available_symbols": symbol_values,
                         "completed_steps": [item.as_dict() for item in steps],
                         "last_action_error": last_error},
                schema=selection_schema(item_id, candidate_id), actions=actions, steps=steps,
                metrics=lambda: self._metrics(controls, arguments, invalid_controls, invalid_arguments),
            )
            try:
                validate_selection(selection.result, item_id=item_id, candidate_id=candidate_id,
                                   evidence_refs=list(self.base.harness.evidence_refs))
            except ValueError as exc:
                invalid_controls += 1
                last_error = self._error(exc)
                if invalid_controls + invalid_arguments > self.max_invalid_actions:
                    self._raise_session_failure(runs, item_id, candidate_id, candidate_label,
                                                actions, steps, last_error,
                                                self._metrics(controls, arguments, invalid_controls,
                                                              invalid_arguments))
                continue
            action_name = selection.result["action"]
            if action_name == "ABSTAIN":
                action = normalized_action(selection=selection.result, arguments={},
                                           evidence_refs=list(self.base.harness.evidence_refs))
            else:
                arguments += 1
                argument = self._call_or_fail(
                    runs=runs, stage="ARGUMENTS", item_id=item_id, model_id=model_id,
                    candidate_id=candidate_id, candidate_label=candidate_label,
                    role_id=f"staged-arguments-{model_id}-{item_id}-turn-{cycle}",
                    objective=("Return only the arguments required by the selected " + action_name + " action."),
                    context={"role": "staged_action_arguments", "control_turn": cycle,
                             "selected_action": action_name, "available_symbols": symbol_values,
                             "completed_steps": [item.as_dict() for item in steps]},
                    schema=arguments_schema(action_name, item_id, candidate_id, available),
                    actions=actions, steps=steps,
                    metrics=lambda: self._metrics(controls, arguments, invalid_controls,
                                                  invalid_arguments),
                )
                try:
                    validate_arguments(
                        argument.result, action=action_name, item_id=item_id,
                        candidate_id=candidate_id,
                        evidence_refs=list(self.base.harness.evidence_refs),
                        available_symbols=available,
                    )
                    action = normalized_action(
                        selection=selection.result, arguments=argument.result,
                        evidence_refs=list(self.base.harness.evidence_refs),
                    )
                except ValueError as exc:
                    invalid_arguments += 1
                    last_error = self._error(exc)
                    if invalid_controls + invalid_arguments > self.max_invalid_actions:
                        self._raise_session_failure(
                            runs, item_id, candidate_id, candidate_label, actions, steps, last_error,
                            self._metrics(controls, arguments, invalid_controls, invalid_arguments),
                        )
                    continue
            actions.append(action)
            try:
                if action_name == "APPLY":
                    if len(steps) >= self.max_steps:
                        raise ValueError("staged_derivation_step_limit")
                    receipt = self.base.harness.execute_derivation_step(
                        item_id=item_id, candidate_id=candidate_id,
                        step_id=f"STEP_{len(steps) + 1}", action=action,
                        symbol_values=symbol_values,
                    )
                    steps.append(receipt)
                    symbol_values[receipt.step_id] = receipt.result
                    last_error = ""
                    continue
                final = self.base.harness.finalize_derivation_session(
                    item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, action=action,
                    step_receipts=tuple(steps), provider_turns=controls + arguments,
                    invalid_actions=invalid_controls + invalid_arguments,
                )
                return self._aggregate(
                    runs, item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, actions=actions,
                    step_receipts=steps, final_receipt=final,
                    invalid_actions=invalid_controls + invalid_arguments,
                    session_metrics=self._metrics(controls, arguments, invalid_controls,
                                                  invalid_arguments),
                )
            except (ValueError, ZeroDivisionError) as exc:
                invalid_arguments += 1
                last_error = self._error(exc)
                if invalid_controls + invalid_arguments > self.max_invalid_actions:
                    self._raise_session_failure(
                        runs, item_id, candidate_id, candidate_label, actions, steps, last_error,
                        self._metrics(controls, arguments, invalid_controls, invalid_arguments),
                    )
        self._raise_session_failure(
            runs, item_id, candidate_id, candidate_label, actions, steps,
            "staged_derivation_control_limit",
            self._metrics(controls, arguments, invalid_controls, invalid_arguments),
            stage="SESSION_LIMIT",
        )

    def _call_or_fail(self, *, runs, stage, item_id, model_id, candidate_id,
                      candidate_label, role_id, objective, context, schema,
                      actions, steps, metrics):
        try:
            run = self._execute(
                role_id=role_id, model_id=model_id,
                task_kind="pilot_disagreement_argument", objective=objective,
                item_id=item_id,
                round_context={"candidate_id": candidate_id,
                               "original_candidate": candidate_label,
                               "peer_output": "withheld", **context},
                schema=schema, stage=stage,
            )
        except DisagreementCaseProviderFailure as exc:
            aggregate = self._aggregate(
                (*runs, *exc.runs), item_id=item_id, candidate_id=candidate_id,
                original_candidate=candidate_label, actions=actions,
                step_receipts=steps, failure=";".join(exc.failures),
                session_metrics=metrics(),
            )
            raise DisagreementCaseProviderFailure(
                stage=stage, run=aggregate, failures=exc.failures,
            ) from exc
        runs.append(run)
        return run

    def _raise_session_failure(self, runs, item_id, candidate_id, candidate_label,
                               actions, steps, failure, metrics, stage="ACTION"):
        aggregate = self._aggregate(
            runs, item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, actions=actions,
            step_receipts=steps, failure=failure,
            invalid_actions=metrics["session_invalid_actions"],
            session_metrics=metrics,
        )
        raise DisagreementCaseProviderFailure(
            stage=stage, run=aggregate, failures=(failure,),
        )

    @staticmethod
    def _metrics(controls, arguments, invalid_controls, invalid_arguments):
        return {"session_provider_turns": controls + arguments,
                "session_control_turns": controls, "session_argument_turns": arguments,
                "session_invalid_controls": invalid_controls,
                "session_invalid_arguments": invalid_arguments,
                "session_invalid_actions": invalid_controls + invalid_arguments}

    @staticmethod
    def _error(exc):
        return type(exc).__name__ + ":" + str(exc)
