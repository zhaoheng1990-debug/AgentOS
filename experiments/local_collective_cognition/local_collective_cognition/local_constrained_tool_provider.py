"""Local Provider adapter backed by finite token-constrained tool calls."""

from __future__ import annotations

import json
import time

from .constrained_generation import generate_constrained_call
from .constrained_tool_registry import registry_prompt_view, validate_tool_registry
from .local_transformers_provider import (
    LocalTransformersJsonAdapter, LocalTransformersResidentPool,
)
from .provider_telemetry import ProviderInvocationTelemetry, hash_payload


CONSTRAINED_TOOL_TASK_KIND = "pilot_constrained_tool_action"


class ConstrainedTransformersResidentPool(LocalTransformersResidentPool):
    def generate_tool_call(self, *, model_id, messages, calls):
        if not self.all_resident:
            raise RuntimeError("local_transformers_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"local_transformers_model_not_registered:{model_id}")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            prompt = self._render_prompt(tokenizer, messages)
            return generate_constrained_call(
                tokenizer=tokenizer, model=model, prompt=prompt, calls=calls, device=self.device,
            )


class LocalConstrainedToolAdapter(LocalTransformersJsonAdapter):
    def invoke(self, task):
        if task.task_kind != CONSTRAINED_TOOL_TASK_KIND:
            return super().invoke(task)
        registry = task.inputs.get("round_context", {}).get("constrained_tool_channel")
        validate_tool_registry(registry)
        options = registry["options"]
        by_call = {item["call"]: item["result"] for item in options}
        started = time.perf_counter()
        try:
            generated = self.pool.generate_tool_call(
                model_id=self.profile.model_id,
                messages=constrained_tool_messages(task, registry),
                calls=tuple(by_call),
            )
            result = by_call[generated.selected_call]
            failures = self._result_failures(task, result)
            if failures:
                raise ValueError("constrained_tool_result_invalid:" + ";".join(failures))
            telemetry = self._record_tool(task, generated, result)
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

    def _record_tool(self, task, generated, result):
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"local-tool-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id, model_id=self.profile.model_id,
            backend="transformers-cuda-constrained-tool", task_id=task.task_id,
            task_kind=task.task_kind, task_contract_hash=task.contract_hash(),
            status="COMPLETED", input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens, cached_tokens=0,
            latency_ms=generated.latency_ms, api_cost=0.0, tool_calls=1, tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence), output_hash=hash_payload(result),
            thinking_present=False, thinking_char_count=0, thinking_hash="", error_type="",
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry


def constrained_tool_messages(task, registry):
    context = dict(task.inputs["round_context"])
    context["constrained_tool_channel"] = registry_prompt_view(registry)
    public_inputs = {**task.inputs, "round_context": context}
    return [
        {"role": "system", "content": (
            "You are one bounded AgentOS cognitive role. Select exactly one registered tool call. "
            "The decoding channel guarantees syntax; choose the semantically correct action and arguments."
        )},
        {"role": "user", "content": (
            f"Objective:\n{task.objective}\n\n"
            "Tool grammar:\nAPPLY(OPERATOR,SYMBOL[,SYMBOL]) | FINALIZE(STEP,LABEL) | ABSTAIN()\n\n"
            f"Inputs:\n{json.dumps(public_inputs, sort_keys=True, default=str)}"
        )},
    ]
