"""Local Provider adapter for hierarchical enum-scored actions and judgment."""

from __future__ import annotations

import json
import time

from .candidate_revision_contracts import CHOICE_LABELS
from .constrained_tool_contract import canonical_tool_call
from .enum_scoring import score_enum
from .hierarchical_score_receipt import build_score_receipt, bind_score_receipt
from .hierarchical_tool_channel import (
    action_options, operand_options, validate_hierarchical_channel,
)
from .local_constrained_tool_provider import (
    ConstrainedTransformersResidentPool, LocalConstrainedToolAdapter,
)
from .provider_telemetry import ProviderInvocationTelemetry, hash_payload
from .typed_derivation_contracts import BINARY_OPERATORS


HIERARCHICAL_TOOL_TASK_KIND = "pilot_hierarchical_tool_action"


class HierarchicalTransformersResidentPool(ConstrainedTransformersResidentPool):
    def score_enum(self, *, model_id, messages, options):
        if not self.all_resident:
            raise RuntimeError("local_transformers_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"local_transformers_model_not_registered:{model_id}")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            prompt = self._render_prompt(tokenizer, messages)
            return score_enum(tokenizer=tokenizer, model=model, prompt=prompt,
                              options=options, device=self.device)


class LocalHierarchicalToolAdapter(LocalConstrainedToolAdapter):
    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if task.task_kind == HIERARCHICAL_TOOL_TASK_KIND:
            return self._invoke_action(task, context)
        if (task.task_kind == "pilot_disagreement_adjudication"
                and context.get("role") == "blinded_verified_case_judge"):
            return self._invoke_judge(task, context)
        return super().invoke(task)

    def _invoke_action(self, task, context):
        channel = context.get("hierarchical_tool_channel")
        validate_hierarchical_channel(channel)
        started, decisions = time.perf_counter(), []
        try:
            action = self._select(task, channel, "ACTION", action_options(channel), decisions)
            if action == "APPLY":
                result = self._select_apply(task, channel, decisions)
            elif action == "FINALIZE":
                step = self._select(task, channel, "RESULT_STEP", tuple(channel["step_symbols"]), decisions)
                label = self._select(task, channel, "CANDIDATE", CHOICE_LABELS, decisions)
                result = _action_result(task, action, "NONE", [step], label)
            else:
                result = _action_result(task, action, "NONE", [], "ABSTAIN")
            selected_call = canonical_tool_call(result)
            receipt = self._receipt(task, channel["channel_hash"], decisions, selected_call)
            output = {**result, "decision_receipt": receipt}
            failures = self._result_failures(task, output)
            if failures:
                raise ValueError("hierarchical_tool_result_invalid:" + ";".join(failures))
            telemetry = self._record_scored(task, decisions, output, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, output, telemetry)

    def _select_apply(self, task, channel, decisions):
        operator = self._select(task, channel, "OPERATOR", tuple(channel["operators"]), decisions)
        first_options = operand_options(channel, operator)
        first = self._select(task, channel, "OPERAND_1", first_options, decisions)
        inputs = [first]
        if operator in BINARY_OPERATORS:
            second = self._select(
                task, channel, "OPERAND_2", operand_options(channel, operator, left=first), decisions,
            )
            inputs.append(second)
        return _action_result(task, "APPLY", operator, inputs, "PENDING")

    def _invoke_judge(self, task, context):
        started, decisions = time.perf_counter(), []
        channel_hash = hash_payload({"role": context["role"],
                                     "candidate_records": context["candidate_records"]})
        try:
            selected = self._select(
                task, {"channel_hash": channel_hash}, "JUDGMENT",
                ("CANDIDATE_1", "CANDIDATE_2", "ABSTAIN"), decisions,
                context_override=context,
            )
            confidence = decisions[-1]["selected_probability"]
            receipt = self._receipt(task, channel_hash, decisions, selected)
            output = {
                "item_id": task.inputs["benchmark_item_ids"][0],
                "selected_candidate": selected,
                "adjudicability": "AMBIGUOUS" if selected == "ABSTAIN" else "ADJUDICABLE",
                "confidence": confidence,
                "decisive_reason": (
                    f"bounded_enum_score margin={decisions[-1]['margin']:.6f}; "
                    f"receipt={receipt['receipt_hash']}"
                ),
                "evidence_refs": list(task.allowed_evidence), "decision_receipt": receipt,
            }
            failures = self._result_failures(task, output)
            if failures:
                raise ValueError("hierarchical_judgment_invalid:" + ";".join(failures))
            telemetry = self._record_scored(task, decisions, output, started)
        except Exception as exc:
            self._record_failure(task, started, exc)
            raise
        return _envelope(task, output, telemetry)

    def _select(self, task, channel, stage, options, decisions, context_override=None):
        if not options:
            raise ValueError(f"hierarchical_enum_empty:{stage}")
        generated = self.pool.score_enum(
            model_id=self.profile.model_id,
            messages=_enum_messages(
                task, channel, stage, options, context_override, decisions,
            ),
            options=tuple(options),
        )
        decisions.append({
            "stage": stage, "selected": generated.selected,
            "selected_probability": generated.selected_probability,
            "margin": generated.margin, "entropy": generated.entropy,
            "scores": [dict(item) for item in generated.scores],
            "input_tokens": generated.input_tokens, "latency_ms": generated.latency_ms,
        })
        return generated.selected

    def _receipt(self, task, channel_hash, decisions, selected):
        receipt = build_score_receipt(
            task=task, channel_hash=channel_hash, decisions=decisions, selected_value=selected,
        )
        return bind_score_receipt(
            receipt, provider_id=self.profile.provider_id, model_id=self.profile.model_id,
        )

    def _record_scored(self, task, decisions, result, started):
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"local-hierarchical-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            backend="transformers-cuda-hierarchical-enum", task_id=task.task_id,
            task_kind=task.task_kind, task_contract_hash=task.contract_hash(), status="COMPLETED",
            input_tokens=sum(item["input_tokens"] for item in decisions),
            output_tokens=len(decisions), cached_tokens=0,
            latency_ms=max(sum(item["latency_ms"] for item in decisions),
                           max(1, round((time.perf_counter() - started) * 1000))),
            api_cost=0.0, tool_calls=len(decisions), tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence), output_hash=hash_payload(result),
            thinking_present=False, thinking_char_count=0, thinking_hash="", error_type="",
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry


def _action_result(task, action, operator, inputs, proposed):
    context = task.inputs["round_context"]
    return {"item_id": task.inputs["benchmark_item_ids"][0],
            "candidate_id": context["candidate_id"], "action": action,
            "operator": operator, "inputs": inputs, "proposed_candidate": proposed,
            "evidence_refs": list(task.allowed_evidence)}


def _enum_messages(task, channel, stage, options, context_override, decisions):
    context = context_override or task.inputs["round_context"]
    public = {**task.inputs, "round_context": {
        key: value for key, value in context.items()
        if key not in {"hierarchical_tool_channel"}
    }}
    menu = {chr(65 + index): option for index, option in enumerate(options)}
    partial = [{"stage": item["stage"], "selected": item["selected"]}
               for item in decisions]
    return [{"role": "system", "content": (
        "You are a bounded AgentOS cognitive role. Choose the semantically best menu option. "
        "The Harness owns execution and truth remains hidden. Reply with one menu label only."
    )}, {"role": "user", "content": (
        f"Objective:\n{task.objective}\n\nDecision stage: {stage}\n"
        f"Stage instruction: {_stage_instruction(stage)}\n"
        f"Selections already committed in this action: {json.dumps(partial)}\n"
        f"State hash: {channel['channel_hash']}\nMenu: {json.dumps(menu, sort_keys=True)}\n\n"
        f"Public inputs:\n{json.dumps(public, sort_keys=True, default=str)}\n\nSelection:"
    )}]


def _stage_instruction(stage):
    return {
        "ACTION": (
            "Choose APPLY when another calculation is needed. Choose FINALIZE only when an existing "
            "STEP value exactly matches a public answer. Choose ABSTAIN only when no valid progress exists."
        ),
        "OPERATOR": "Choose the operator needed by the public question and committed action.",
        "OPERAND_1": "Choose the first input for the committed operator.",
        "OPERAND_2": "Choose the second input given the committed operator and first input.",
        "RESULT_STEP": "Choose the completed step that contains the final answer value.",
        "CANDIDATE": "Choose the public answer label whose value exactly equals the committed result step.",
        "JUDGMENT": "Select the stronger replay-backed candidate, or ABSTAIN when neither is decisive.",
    }[stage]


def _envelope(task, result, telemetry):
    return {"result": result, "usage": {
        "input_tokens": telemetry.input_tokens, "output_tokens": telemetry.output_tokens,
        "cached_tokens": 0, "provider_calls": 1, "latency_ms": telemetry.latency_ms,
    }, "provenance_refs": list(task.allowed_evidence)}
