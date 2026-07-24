"""Candidate revision through hierarchical enum-scored semantic decisions."""

from __future__ import annotations

from .disagreement_case_failure import DisagreementCaseProviderFailure
from .hierarchical_score_receipt import validate_score_receipt
from .hierarchical_tool_channel import build_hierarchical_channel
from .iterative_derivation_case_runtime import IterativeDerivationCaseRuntime
from .iterative_derivation_contracts import iterative_action_schema, validate_iterative_action
from .local_hierarchical_tool_provider import HIERARCHICAL_TOOL_TASK_KIND


class HierarchicalToolCaseRuntime(IterativeDerivationCaseRuntime):
    def __init__(self, base, *, max_steps=8, max_turns=10, max_invalid_actions=1):
        super().__init__(base, max_steps=max_steps, max_turns=max_turns,
                         max_invalid_actions=max_invalid_actions)

    def _evidence_run(self, item_id, model_id, candidate_id, candidate_label):
        symbols = dict(self.base.harness.derivation_scaffold(item_id))
        steps, runs, actions, score_receipts = [], [], [], []
        invalid_actions = menu_options = inference_passes = 0
        for turn in range(1, self.max_turns + 1):
            channel = build_hierarchical_channel(
                symbol_values=symbols, prior_actions=actions,
                allow_apply=len(steps) < self.max_steps,
            )
            try:
                run = self._execute(
                    role_id=f"hierarchical-tool-{model_id}-{item_id}-turn-{turn}",
                    model_id=model_id, task_kind=HIERARCHICAL_TOOL_TASK_KIND,
                    objective=(
                        "Advance an independent derivation through bounded semantic choices. "
                        "Finalize only when an existing step supports one public option; otherwise "
                        "apply a useful operator or abstain."
                    ), item_id=item_id,
                    round_context={"role": "hierarchical_derivation_tool_user",
                                   "candidate_id": candidate_id,
                                   "original_candidate": candidate_label, "turn": turn,
                                   "available_symbols": symbols,
                                   "completed_steps": [item.as_dict() for item in steps],
                                   "hierarchical_tool_channel": channel,
                                   "peer_output": "withheld"},
                    schema=iterative_action_schema(item_id, candidate_id, tuple(symbols)),
                    stage="HIERARCHICAL_TOOL_CHANNEL",
                )
            except DisagreementCaseProviderFailure as exc:
                self._raise_failure(
                    (*runs, *exc.runs), item_id, candidate_id, candidate_label, actions,
                    steps, score_receipts, ";".join(exc.failures), invalid_actions,
                    menu_options, inference_passes, "HIERARCHICAL_TOOL_CHANNEL",
                )
            runs.append(run)
            try:
                receipt = run.result["decision_receipt"]
                validate_score_receipt(receipt, task=run.tasks[-1])
                score_receipts.append(receipt)
                menu_options += int(receipt["menu_option_total"])
                inference_passes += int(receipt["inference_passes"])
                action = {key: value for key, value in run.result.items()
                          if key != "decision_receipt"}
                validate_iterative_action(
                    action, item_id=item_id, candidate_id=candidate_id,
                    evidence_refs=list(self.base.harness.evidence_refs),
                    available_symbols=tuple(symbols),
                )
                actions.append(action)
                if action["action"] == "APPLY":
                    step = self.base.harness.execute_derivation_step(
                        item_id=item_id, candidate_id=candidate_id,
                        step_id=f"STEP_{len(steps) + 1}", action=action,
                        symbol_values=symbols,
                    )
                    steps.append(step)
                    symbols[step.step_id] = step.result
                    continue
                final = self.base.harness.finalize_derivation_session(
                    item_id=item_id, candidate_id=candidate_id,
                    original_candidate=candidate_label, action=action,
                    step_receipts=tuple(steps), provider_turns=len(runs),
                    invalid_actions=invalid_actions,
                )
                return self._aggregate_run(
                    runs, item_id, candidate_id, candidate_label, actions, steps,
                    score_receipts, invalid_actions, menu_options, inference_passes, final,
                )
            except (KeyError, ValueError, ZeroDivisionError) as exc:
                invalid_actions += 1
                if invalid_actions > self.max_invalid_actions:
                    self._raise_failure(
                        runs, item_id, candidate_id, candidate_label, actions, steps,
                        score_receipts, type(exc).__name__ + ":" + str(exc), invalid_actions,
                        menu_options, inference_passes, "HIERARCHICAL_TOOL_EXECUTION",
                    )
        self._raise_failure(
            runs, item_id, candidate_id, candidate_label, actions, steps, score_receipts,
            "hierarchical_tool_turn_limit", invalid_actions, menu_options,
            inference_passes, "SESSION_LIMIT",
        )

    def _aggregate_run(self, runs, item_id, candidate_id, candidate_label, actions,
                       steps, receipts, invalid, options, passes, final=None, failure=""):
        return self._aggregate(
            runs, item_id=item_id, candidate_id=candidate_id,
            original_candidate=candidate_label, actions=actions, step_receipts=steps,
            final_receipt=final, failure=failure, invalid_actions=invalid,
            session_metrics={"session_tool_turns": len(runs),
                             "session_score_receipts": len(receipts),
                             "session_menu_options": options,
                             "session_inference_passes": passes},
            result_extras={"decision_receipts": list(receipts)},
        )

    def _raise_failure(self, runs, item_id, candidate_id, candidate_label, actions,
                       steps, receipts, failure, invalid, options, passes, stage):
        aggregate = self._aggregate_run(
            runs, item_id, candidate_id, candidate_label, actions, steps, receipts,
            invalid, options, passes, failure=failure,
        )
        raise DisagreementCaseProviderFailure(stage=stage, run=aggregate, failures=(failure,))
