"""Calibrated local Provider for problem candidates and coordination."""

from __future__ import annotations

import json
import time

from .calibrated_score_receipt import build_calibrated_score_receipt
from .local_plan_intent_provider import LocalPlanIntentAdapter
from .plan_intent_contracts import PLAN_INTENT_MODES
from .problem_formulation_contracts import (
    CRITICAL_CONSTRAINTS, NUMERIC_FAMILIES, STRING_FAMILIES, TARGET_KINDS,
    build_coordination_receipt, build_problem_definition_receipt,
)
from .problem_semantic_channel import problem_semantic_channel_hash
from .provider_telemetry import hash_payload


PROBLEM_FORMULATION_TASK_KIND = "pilot_problem_formulation"
PROBLEM_COORDINATOR_ROLE = "blinded_problem_definition_coordinator"


class LocalProblemFormulationAdapter(LocalPlanIntentAdapter):
    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == PROBLEM_FORMULATION_TASK_KIND:
            return self._invoke_problem_candidate(task, context)
        if (task.task_kind == "pilot_disagreement_adjudication"
                and context.get("role") == PROBLEM_COORDINATOR_ROLE):
            return self._invoke_problem_coordinator(task, context)
        return super().invoke(task)

    def _invoke_problem_candidate(self, task, context):
        started, decisions = time.perf_counter(), []
        channel = {"channel_hash": problem_semantic_channel_hash(task, context)}
        try:
            mode = self._select_calibrated(
                task, channel, "PROBLEM_MODE", PLAN_INTENT_MODES, decisions, context,
            )
            if mode == "ABSTAIN":
                family = target = constraint = "ABSTAIN"
            else:
                families = STRING_FAMILIES if mode == "STRING_TRANSFORMATION" else NUMERIC_FAMILIES
                family = self._select_calibrated(
                    task, channel, "PROBLEM_FAMILY", families, decisions, context,
                )
                target = self._select_calibrated(
                    task, channel, "TARGET_KIND", TARGET_KINDS, decisions, context,
                )
                constraint = self._select_calibrated(
                    task, channel, "CRITICAL_CONSTRAINT", CRITICAL_CONSTRAINTS,
                    decisions, context,
                )
            decision = build_calibrated_score_receipt(
                task=task, channel_hash=channel["channel_hash"], decisions=decisions,
                selected_value="|".join((mode, family, target, constraint)),
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            receipt = build_problem_definition_receipt(
                task=task, problem_candidate_id=context["problem_candidate_id"],
                intent_mode=mode, problem_family=family, target_kind=target,
                critical_constraint=constraint, decision_receipt=decision,
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            result = {"item_id": task.inputs["benchmark_item_ids"][0],
                      "problem_candidate_id": context["problem_candidate_id"],
                      "intent_mode": mode, "problem_family": family,
                      "target_kind": target, "critical_constraint": constraint,
                      "evidence_refs": list(task.allowed_evidence),
                      "decision_receipt": decision, "problem_receipt": receipt}
            telemetry = self._complete(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, result, telemetry)

    def _invoke_problem_coordinator(self, task, context):
        started, decisions = time.perf_counter(), []
        candidates = context["problem_candidates"]
        channel = {"channel_hash": hash_payload({"task": task.contract_hash(),
                                                  "candidates": candidates})}
        try:
            selected = self._select_calibrated(
                task, channel, "PROBLEM_COORDINATION",
                ("PROBLEM_1", "PROBLEM_2", "ABSTAIN"), decisions, context,
            )
            decision = build_calibrated_score_receipt(
                task=task, channel_hash=channel["channel_hash"], decisions=decisions,
                selected_value=selected, provider_id=self.profile.provider_id,
                model_id=self.profile.model_id,
            )
            receipt = build_coordination_receipt(
                task=task, candidate_receipts=[item["problem_receipt"] for item in candidates],
                selected_candidate=selected, confidence=decisions[-1]["selected_probability"],
                decision_receipt=decision, provider_id=self.profile.provider_id,
                model_id=self.profile.model_id,
            )
            result = {"item_id": task.inputs["benchmark_item_ids"][0],
                      "selected_problem_candidate": selected,
                      "confidence": decisions[-1]["selected_probability"],
                      "evidence_refs": list(task.allowed_evidence),
                      "decision_receipt": decision, "coordination_receipt": receipt}
            telemetry = self._complete(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, result, telemetry)

    def _complete(self, task, decisions, result, started):
        failures = self._result_failures(task, result)
        if failures:
            raise ValueError("problem_formulation_result_invalid:" + ";".join(failures))
        return self._record_calibrated(task, decisions, result, started)

    @staticmethod
    def _selection_messages(task, channel, stage, options, context, decisions):
        menu = {chr(65 + index): option for index, option in enumerate(options)}
        partial = [{"stage": item["stage"], "selected": item["selected"]}
                   for item in decisions]
        public = {**task.inputs, "round_context": {
            key: value for key, value in context.items()
            if key not in {"problem_candidates", "contrastive_batch_receipt_hash"}
        }}
        candidates = context.get("problem_candidates", [])
        return [{"role": "system", "content": (
            "Identify or coordinate the cognitive object before planning. Select one menu label "
            "only. Use public task constraints; hidden truth is unavailable."
        )}, {"role": "user", "content": (
            f"Objective:\n{task.objective}\nDecision stage: {stage}\n"
            f"Committed object choices: {json.dumps(partial)}\n"
            f"Problem candidates: {json.dumps(candidates, sort_keys=True)}\n"
            f"Menu: {json.dumps(menu, sort_keys=True)}\n"
            f"Public inputs: {json.dumps(public, sort_keys=True, default=str)}\nSelection:"
        )}]


def _envelope(task, result, telemetry):
    return {"result": result, "usage": {"input_tokens": telemetry.input_tokens,
            "output_tokens": telemetry.output_tokens, "cached_tokens": 0,
            "provider_calls": 1, "latency_ms": telemetry.latency_ms},
            "provenance_refs": list(task.allowed_evidence)}
