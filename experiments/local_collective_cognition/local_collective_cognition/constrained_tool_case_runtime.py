"""Candidate revision through one finite constrained tool call per turn."""

from __future__ import annotations

from .constrained_tool_registry import build_tool_registry
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .iterative_derivation_case_runtime import IterativeDerivationCaseRuntime
from .iterative_derivation_contracts import iterative_action_schema, validate_iterative_action
from .local_constrained_tool_provider import CONSTRAINED_TOOL_TASK_KIND


class ConstrainedToolCaseRuntime(IterativeDerivationCaseRuntime):
    def __init__(self, base, *, max_steps=8, max_turns=10, max_invalid_actions=1):
        super().__init__(base, max_steps=max_steps, max_turns=max_turns,
                         max_invalid_actions=max_invalid_actions)

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        symbols = dict(self.base.harness.derivation_scaffold(item_id))
        steps, runs, actions = [], [], []
        invalid_actions = registry_options = 0
        for turn in range(1, self.max_turns + 1):
            registry = build_tool_registry(
                item_id=item_id, candidate_id=candidate_id,
                evidence_refs=self.base.harness.evidence_refs, symbol_values=symbols,
                prior_actions=actions, allow_apply=len(steps) < self.max_steps,
            )
            registry_options += len(registry["options"])
            try:
                run = self._execute(
                    role_id=f"constrained-tool-{model_id}-{item_id}-turn-{turn}",
                    model_id=model_id, task_kind=CONSTRAINED_TOOL_TASK_KIND,
                    objective=(
                        "Choose one registered tool call that advances an independent derivation. "
                        "Finalize only when an existing STEP supports one public option; otherwise apply "
                        "a useful operator or abstain."
                    ), item_id=item_id,
                    round_context={"role": "constrained_derivation_tool_user",
                                   "candidate_id": candidate_id,
                                   "original_candidate": candidate_label, "turn": turn,
                                   "available_symbols": symbols,
                                   "completed_steps": [item.as_dict() for item in steps],
                                   "constrained_tool_channel": registry,
                                   "peer_output": "withheld"},
                    schema=iterative_action_schema(item_id, candidate_id, tuple(symbols)),
                    stage="TOOL_CHANNEL",
                )
            except DisagreementCaseProviderFailure as exc:
                self._raise_failure(
                    (*runs, *exc.runs), item_id, candidate_id, candidate_label,
                    actions, steps, ";".join(exc.failures), invalid_actions,
                    registry_options, "TOOL_CHANNEL",
                )
            runs.append(run)
            action = run.result
            try:
                validate_iterative_action(
                    action, item_id=item_id, candidate_id=candidate_id,
                    evidence_refs=list(self.base.harness.evidence_refs),
                    available_symbols=tuple(symbols),
                )
                actions.append(action)
                if action["action"] == "APPLY":
                    receipt = self.base.harness.execute_derivation_step(
                        item_id=item_id, candidate_id=candidate_id,
                        step_id=f"STEP_{len(steps) + 1}", action=action,
                        symbol_values=symbols,
                    )
                    steps.append(receipt)
                    symbols[receipt.step_id] = receipt.result
                    continue
                final = self.base.harness.finalize_derivation_session(
                    item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, action=action,
                    step_receipts=tuple(steps), provider_turns=len(runs),
                    invalid_actions=invalid_actions,
                )
                return self._aggregate(
                    runs, item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, actions=actions,
                    step_receipts=steps, final_receipt=final,
                    invalid_actions=invalid_actions,
                    session_metrics=self._metrics(len(runs), registry_options, invalid_actions),
                )
            except (ValueError, ZeroDivisionError) as exc:
                invalid_actions += 1
                if invalid_actions > self.max_invalid_actions:
                    self._raise_failure(
                        runs, item_id, candidate_id, candidate_label, actions, steps,
                        type(exc).__name__ + ":" + str(exc), invalid_actions,
                        registry_options, "TOOL_EXECUTION",
                    )
        self._raise_failure(
            runs, item_id, candidate_id, candidate_label, actions, steps,
            "constrained_tool_turn_limit", invalid_actions, registry_options, "SESSION_LIMIT",
        )

    def _raise_failure(self, runs, item_id, candidate_id, candidate_label,
                       actions, steps, failure, invalid_actions, registry_options, stage):
        aggregate = self._aggregate(
            runs, item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, actions=actions,
            step_receipts=steps, failure=failure, invalid_actions=invalid_actions,
            session_metrics=self._metrics(len(runs), registry_options, invalid_actions),
        )
        raise DisagreementCaseProviderFailure(stage=stage, run=aggregate, failures=(failure,))

    @staticmethod
    def _metrics(turns, registry_options, invalid_actions):
        return {"session_provider_turns": turns, "session_tool_turns": turns,
                "session_registry_options": registry_options,
                "session_invalid_actions": invalid_actions}
