"""Context-calibrated Provider adapter for global plan-intent construction."""

from __future__ import annotations

import json
import time

from .calibrated_enum_scoring import build_calibration_prior, score_calibrated_enum
from .calibrated_score_receipt import build_calibrated_score_receipt
from .candidate_revision_contracts import CHOICE_LABELS
from .constrained_tool_contract import canonical_tool_call
from .hierarchical_tool_channel import (
    action_options, operand_options, validate_hierarchical_channel,
)
from .local_hierarchical_tool_provider import (
    HierarchicalTransformersResidentPool, LocalHierarchicalToolAdapter,
)
from .plan_intent_contracts import PLAN_INTENT_MODES
from .provider_telemetry import ProviderInvocationTelemetry, hash_payload
from .typed_derivation_contracts import BINARY_OPERATORS, UNARY_OPERATORS


PLAN_INTENT_TASK_KIND = "pilot_plan_intent_action"
PLAN_INTENT_JUDGE_ROLE = "blinded_plan_intent_judge"


class PlanIntentTransformersResidentPool(HierarchicalTransformersResidentPool):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._enum_prior_cache = {}

    def unload_all(self):
        super().unload_all()
        self._enum_prior_cache.clear()

    def reset_enum_calibration(self, model_id=None):
        """Reset cached label priors so paired arms pay identical calibration work."""
        if model_id is None:
            self._enum_prior_cache.clear()
            return
        for key in [key for key in self._enum_prior_cache if key[0] == model_id]:
            del self._enum_prior_cache[key]

    def score_calibrated_enum(self, *, model_id, messages, options):
        if not self.all_resident or model_id not in self._resident:
            raise RuntimeError("plan_intent_resident_model_unavailable")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            key = (model_id, len(options))
            cached = key in self._enum_prior_cache
            if not cached:
                prompt = self._render_prompt(tokenizer, _calibration_messages(len(options)))
                prior = build_calibration_prior(
                    tokenizer=tokenizer, model=model, prompt=prompt,
                    count=len(options), device=self.device,
                )
                rounded = [round(float(value), 12) for value in prior.probabilities]
                ref = hash_payload({"model_id": model_id, "menu_size": len(options),
                                    "probabilities": rounded})
                self._enum_prior_cache[key] = (prior, ref)
            prior, ref = self._enum_prior_cache[key]
            prompt = self._render_prompt(tokenizer, messages)
            return score_calibrated_enum(
                tokenizer=tokenizer, model=model, prompt=prompt, options=options,
                device=self.device, prior=prior, calibration_ref=ref,
                calibration_cached=cached,
            )


class LocalPlanIntentAdapter(LocalHierarchicalToolAdapter):
    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == PLAN_INTENT_TASK_KIND:
            return self._invoke_plan_action(task, context)
        if (task.task_kind == "pilot_disagreement_adjudication"
                and context.get("role") == PLAN_INTENT_JUDGE_ROLE):
            return self._invoke_plan_judge(task, context)
        return super().invoke(task)

    def _invoke_plan_action(self, task, context):
        channel = context.get("hierarchical_tool_channel")
        validate_hierarchical_channel(channel)
        started, decisions = time.perf_counter(), []
        try:
            mode = context.get("plan_intent_mode") or self._select_calibrated(
                task, channel, "INTENT_MODE", PLAN_INTENT_MODES, decisions, context,
            )
            scoped = _mode_channel(channel, mode)
            action = "ABSTAIN" if mode == "ABSTAIN" else self._select_calibrated(
                task, scoped, "ACTION", action_options(scoped), decisions, context,
            )
            if action == "APPLY":
                result = self._apply_result(task, scoped, mode, decisions, context)
            elif action == "FINALIZE":
                step = self._select_calibrated(task, scoped, "RESULT_STEP",
                                    tuple(scoped["step_symbols"]), decisions, context)
                label = self._select_calibrated(task, scoped, "CANDIDATE", CHOICE_LABELS,
                                     decisions, context)
                result = _result(task, mode, action, "NONE", [step], label)
            else:
                result = _result(task, mode, "ABSTAIN", "NONE", [], "ABSTAIN")
            call = canonical_tool_call(_base_action(result))
            result["decision_receipt"] = build_calibrated_score_receipt(
                task=task, channel_hash=channel["channel_hash"], decisions=decisions,
                selected_value=call, provider_id=self.profile.provider_id,
                model_id=self.profile.model_id,
            )
            failures = self._result_failures(task, result)
            if failures:
                raise ValueError("plan_intent_result_invalid:" + ";".join(failures))
            telemetry = self._record_calibrated(task, decisions, result, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, result, telemetry)

    def _apply_result(self, task, channel, mode, decisions, context):
        operator = self._select_calibrated(task, channel, "OPERATOR", tuple(channel["operators"]),
                                decisions, context)
        first = self._select_calibrated(task, channel, "OPERAND_1", operand_options(channel, operator),
                             decisions, context)
        inputs = [first]
        if operator in BINARY_OPERATORS:
            inputs.append(self._select_calibrated(
                task, channel, "OPERAND_2",
                operand_options(channel, operator, left=first), decisions, context,
            ))
        return _result(task, mode, "APPLY", operator, inputs, "PENDING")

    def _invoke_plan_judge(self, task, context):
        started, decisions = time.perf_counter(), []
        channel_hash = hash_payload({"role": context["role"],
                                     "candidate_records": context["candidate_records"]})
        channel = {"channel_hash": channel_hash}
        try:
            selected = self._select_calibrated(
                task, channel, "JUDGMENT",
                ("CANDIDATE_1", "CANDIDATE_2", "ABSTAIN"), decisions, context,
            )
            receipt = build_calibrated_score_receipt(
                task=task, channel_hash=channel_hash, decisions=decisions,
                selected_value=selected, provider_id=self.profile.provider_id,
                model_id=self.profile.model_id,
            )
            output = {"item_id": task.inputs["benchmark_item_ids"][0],
                      "selected_candidate": selected,
                      "adjudicability": "AMBIGUOUS" if selected == "ABSTAIN" else "ADJUDICABLE",
                      "confidence": decisions[-1]["selected_probability"],
                      "decisive_reason": f"calibrated_bounded_judge:{receipt['receipt_hash']}",
                      "evidence_refs": list(task.allowed_evidence),
                      "decision_receipt": receipt}
            failures = self._result_failures(task, output)
            if failures:
                raise ValueError("plan_intent_judge_invalid:" + ";".join(failures))
            telemetry = self._record_calibrated(task, decisions, output, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, output, telemetry)

    def _select_calibrated(self, task, channel, stage, options, decisions, context):
        ordered = tuple(sorted(options, key=lambda option: hash_payload(
            [task.task_id, stage, channel["channel_hash"], option]
        )))
        generated = self.pool.score_calibrated_enum(
            model_id=self.profile.model_id,
            messages=self._selection_messages(task, channel, stage, ordered, context, decisions),
            options=ordered,
        )
        decisions.append({"stage": stage, "selected": generated.selected,
                          "selected_probability": generated.selected_probability,
                          "margin": generated.margin, "entropy": generated.entropy,
                          "scores": [dict(item) for item in generated.scores],
                          "input_tokens": generated.input_tokens,
                          "latency_ms": generated.latency_ms,
                          "inference_passes": generated.inference_passes,
                          "calibration_ref": generated.calibration_ref,
                          "calibration_cached": generated.calibration_cached})
        return generated.selected

    @staticmethod
    def _selection_messages(task, channel, stage, options, context, decisions):
        return _semantic_messages(task, channel, stage, options, context, decisions)

    def _record_calibrated(self, task, decisions, result, started):
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"local-plan-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            backend="transformers-cuda-context-calibrated-plan", task_id=task.task_id,
            task_kind=task.task_kind, task_contract_hash=task.contract_hash(), status="COMPLETED",
            input_tokens=sum(item["input_tokens"] for item in decisions),
            output_tokens=len(decisions), cached_tokens=0,
            latency_ms=max(sum(item["latency_ms"] for item in decisions),
                           max(1, round((time.perf_counter() - started) * 1000))),
            api_cost=0.0, tool_calls=sum(item["inference_passes"] for item in decisions),
            tool_cost=0.0, evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(result), thinking_present=False,
            thinking_char_count=0, thinking_hash="", error_type="",
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry


def _mode_channel(channel, mode):
    allowed = BINARY_OPERATORS if mode == "NUMERIC_DERIVATION" else UNARY_OPERATORS
    return {**channel, "operators": [item for item in channel["operators"] if item in allowed]}


def _result(task, mode, action, operator, inputs, proposed):
    context = task.inputs["round_context"]
    return {"item_id": task.inputs["benchmark_item_ids"][0],
            "candidate_id": context["candidate_id"], "action": action,
            "operator": operator, "inputs": inputs, "proposed_candidate": proposed,
            "evidence_refs": list(task.allowed_evidence), "intent_mode": mode}


def _base_action(result):
    return {key: value for key, value in result.items() if key != "intent_mode"}


def _semantic_messages(task, channel, stage, options, context, decisions):
    public = {**task.inputs, "round_context": {key: value for key, value in context.items()
                                               if key != "hierarchical_tool_channel"}}
    menu = {chr(65 + index): option for index, option in enumerate(options)}
    partial = [{"stage": item["stage"], "selected": item["selected"]} for item in decisions]
    return [{"role": "system", "content": (
        "Construct one globally coherent AgentOS plan intent. Select one menu label only. "
        "The Harness owns arithmetic and truth remains hidden."
    )}, {"role": "user", "content": (
        f"Objective:\n{task.objective}\nDecision stage: {stage}\n"
        f"Committed plan choices: {json.dumps(partial)}\nState hash: {channel['channel_hash']}\n"
        f"Menu: {json.dumps(menu, sort_keys=True)}\nPublic inputs:\n"
        f"{json.dumps(public, sort_keys=True, default=str)}\nSelection:"
    )}]


def _calibration_messages(count):
    menu = {chr(65 + index): f"OPTION_{index + 1}" for index in range(count)}
    return [{"role": "system", "content": "Content-free label calibration."},
            {"role": "user", "content": (
                f"No task evidence is available. Menu: {json.dumps(menu, sort_keys=True)}\n"
                "Select any label. Selection:"
            )}]


def _envelope(task, result, telemetry):
    return {"result": result, "usage": {"input_tokens": telemetry.input_tokens,
            "output_tokens": telemetry.output_tokens, "cached_tokens": 0,
            "provider_calls": 1, "latency_ms": telemetry.latency_ms},
            "provenance_refs": list(task.allowed_evidence)}
