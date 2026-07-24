"""Calibrated local Provider adapter for contrastive-packet quality judgment."""

from __future__ import annotations

import json
import time

from .calibrated_score_receipt import build_calibrated_score_receipt
from .contrastive_quality_contracts import (
    QUALITY_CRITERIA, QUALITY_TASK_KIND, QUALITY_VALUES, build_quality_receipt,
)
from .local_problem_formulation_provider import LocalProblemFormulationAdapter
from .problem_semantic_channel import quality_semantic_channel_hash


QUALITY_JUDGE_ROLE = "independent_contrastive_packet_quality_judge"


class LocalContrastiveQualityAdapter(LocalProblemFormulationAdapter):
    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == QUALITY_TASK_KIND and context.get("role") == QUALITY_JUDGE_ROLE:
            return self._invoke_quality(task, context)
        return super().invoke(task)

    def _invoke_quality(self, task, context):
        started, decisions, criteria = time.perf_counter(), [], {}
        channel = {"channel_hash": quality_semantic_channel_hash(task, context)}
        try:
            for criterion in QUALITY_CRITERIA:
                criteria[criterion] = self._select_calibrated(
                    task, channel, criterion, QUALITY_VALUES, decisions, context,
                )
            decision = build_calibrated_score_receipt(
                task=task, channel_hash=channel["channel_hash"], decisions=decisions,
                selected_value="|".join(criteria[item] for item in QUALITY_CRITERIA),
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            receipt = build_quality_receipt(
                task=task, packet=context["contrastive_structure_packet"],
                batch_receipt_hash=context["contrastive_batch_receipt_hash"],
                criteria=criteria, decision_receipt=decision,
                provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            )
            result = {
                "item_id": task.inputs["benchmark_item_ids"][0],
                "criteria": criteria, "evidence_refs": list(task.allowed_evidence),
                "decision_receipt": decision, "quality_receipt": receipt,
            }
            failures = self._result_failures(task, result)
            if failures:
                raise ValueError("contrastive_quality_result_invalid:" + ";".join(failures))
            telemetry = self._record_calibrated(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return {
            "result": result,
            "usage": {"input_tokens": telemetry.input_tokens,
                      "output_tokens": telemetry.output_tokens, "cached_tokens": 0,
                      "provider_calls": 1, "latency_ms": telemetry.latency_ms},
            "provenance_refs": list(task.allowed_evidence),
        }

    @staticmethod
    def _selection_messages(task, channel, stage, options, context, decisions):
        if task.task_kind != QUALITY_TASK_KIND:
            return LocalProblemFormulationAdapter._selection_messages(
                task, channel, stage, options, context, decisions,
            )
        menu = {chr(65 + index): option for index, option in enumerate(options)}
        prior = [{"criterion": item["stage"], "selected": item["selected"]}
                 for item in decisions]
        public = {
            "benchmark_public_input": task.inputs["benchmark_public_input"],
            "benchmark_item_ids": task.inputs["benchmark_item_ids"],
            "contrastive_structure_packet": context["contrastive_structure_packet"],
        }
        return [{"role": "system", "content": (
            "Audit one contrastive object-structure packet. Judge semantic content against "
            "the public task. Select one menu label only; hidden truth is unavailable."
        )}, {"role": "user", "content": (
            f"Objective:\n{task.objective}\nQuality criterion: {stage}\n"
            f"Prior judgments: {json.dumps(prior)}\n"
            f"Menu: {json.dumps(menu, sort_keys=True)}\n"
            f"Public inputs: {json.dumps(public, sort_keys=True)}\nSelection:"
        )}]
