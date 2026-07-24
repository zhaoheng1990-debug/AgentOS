"""Local Provider adapter for problem critique and proposer revision."""

from __future__ import annotations

import time

from .calibrated_score_receipt import build_calibrated_score_receipt
from .local_problem_formulation_provider import LocalProblemFormulationAdapter, _envelope
from .plan_intent_contracts import PLAN_INTENT_MODES
from .problem_dialogue_contracts import (
    CRITIQUE_DIMENSIONS, REVISION_SELECTIONS, build_critique_receipt,
    build_revision_receipt,
)
from .problem_formulation_contracts import (
    CRITICAL_CONSTRAINTS, NUMERIC_FAMILIES, STRING_FAMILIES, TARGET_KINDS,
    build_problem_definition_receipt,
)
from .provider_telemetry import hash_payload


PROBLEM_CRITIQUE_TASK_KIND = "pilot_problem_critique"
PROBLEM_REVISION_TASK_KIND = "pilot_problem_revision"


class LocalProblemDialogueAdapter(LocalProblemFormulationAdapter):
    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == PROBLEM_CRITIQUE_TASK_KIND:
            return self._invoke_critique(task, context)
        if task.task_kind == PROBLEM_REVISION_TASK_KIND:
            return self._invoke_revision(task, context)
        return super().invoke(task)

    def _invoke_critique(self, task, context):
        started, decisions = time.perf_counter(), []
        source = context["source_problem_receipt"]
        channel = {"channel_hash": hash_payload({"task": task.contract_hash(),
                                                  "source": source["receipt_hash"]})}
        try:
            dimension = self._select_calibrated(
                task, channel, "CRITIQUE_DIMENSION", CRITIQUE_DIMENSIONS,
                decisions, context,
            )
            mode, family, target, constraint = self._problem_object(
                task, channel, decisions, context, prefix="SUGGESTED_",
            )
            decision = self._decision(
                task, channel, decisions,
                "|".join((dimension, mode, family, target, constraint)),
            )
            suggested = build_problem_definition_receipt(
                task=task,
                problem_candidate_id=context["suggested_problem_candidate_id"],
                intent_mode=mode, problem_family=family, target_kind=target,
                critical_constraint=constraint, decision_receipt=decision,
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            critique = build_critique_receipt(
                task=task, thread_id=context["thread_id"], source_problem=source,
                suggested_problem=suggested, critique_dimension=dimension,
                decision_receipt=decision, provider_id=self.profile.provider_id,
                model_id=self.profile.model_id,
            )
            result = {
                "item_id": task.inputs["benchmark_item_ids"][0],
                "thread_id": context["thread_id"], "critique_dimension": dimension,
                "evidence_refs": list(task.allowed_evidence),
                "decision_receipt": decision,
                "suggested_problem_receipt": suggested,
                "critique_receipt": critique,
            }
            telemetry = self._complete(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, result, telemetry)

    def _invoke_revision(self, task, context):
        started, decisions = time.perf_counter(), []
        source = context["source_problem_receipt"]
        suggested = context["suggested_problem_receipt"]
        critique = context["critique_receipt"]
        channel = {"channel_hash": hash_payload({
            "task": task.contract_hash(), "source": source["receipt_hash"],
            "critique": critique["receipt_hash"],
        })}
        try:
            selection = self._select_calibrated(
                task, channel, "REVISION_SELECTION", REVISION_SELECTIONS,
                decisions, context,
            )
            decision = self._decision(task, channel, decisions, selection)
            if selection == "ORIGINAL":
                final = source
            elif selection == "CRITIC_REVISION":
                final = suggested
            else:
                final = build_problem_definition_receipt(
                    task=task, problem_candidate_id=context["final_problem_candidate_id"],
                    intent_mode="ABSTAIN", problem_family="ABSTAIN",
                    target_kind="ABSTAIN", critical_constraint="ABSTAIN",
                    decision_receipt=decision, provider_id=self.profile.provider_id,
                    model_id=self.profile.model_id,
                )
            revision = build_revision_receipt(
                task=task, thread_id=context["thread_id"], source_problem=source,
                critique_receipt=critique, suggested_problem=suggested,
                selection=selection, final_problem=final, decision_receipt=decision,
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            result = {
                "item_id": task.inputs["benchmark_item_ids"][0],
                "thread_id": context["thread_id"], "selection": selection,
                "evidence_refs": list(task.allowed_evidence),
                "decision_receipt": decision, "final_problem_receipt": final,
                "revision_receipt": revision,
            }
            telemetry = self._complete(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, result, telemetry)

    def _problem_object(self, task, channel, decisions, context, *, prefix):
        mode = self._select_calibrated(
            task, channel, prefix + "PROBLEM_MODE", PLAN_INTENT_MODES,
            decisions, context,
        )
        if mode == "ABSTAIN":
            return ("ABSTAIN",) * 4
        families = STRING_FAMILIES if mode == "STRING_TRANSFORMATION" else NUMERIC_FAMILIES
        family = self._select_calibrated(
            task, channel, prefix + "PROBLEM_FAMILY", families, decisions, context,
        )
        target = self._select_calibrated(
            task, channel, prefix + "TARGET_KIND", TARGET_KINDS, decisions, context,
        )
        constraint = self._select_calibrated(
            task, channel, prefix + "CRITICAL_CONSTRAINT", CRITICAL_CONSTRAINTS,
            decisions, context,
        )
        return mode, family, target, constraint

    def _decision(self, task, channel, decisions, selected):
        return build_calibrated_score_receipt(
            task=task, channel_hash=channel["channel_hash"], decisions=decisions,
            selected_value=selected, provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
        )
