"""Resident CUDA Transformers pool and structured AgentOS Provider adapter."""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentos_kernel import ProviderCapabilityProfile, ProviderCognitiveTask

from .provider_telemetry import ProviderInvocationTelemetry, ProviderTelemetryLedger, hash_payload
from .structured_provider_json import parse_json_object, schema_failures, structured_json_messages


LOCAL_TRANSFORMERS_ADAPTER_VERSION = "local_transformers_json_adapter_v0_1"


@dataclass(frozen=True)
class LocalTransformersModelSpec:
    model_id: str
    model_path: str

    def __post_init__(self) -> None:
        if not self.model_id or not self.model_path:
            raise ValueError("local_transformers_model_spec_incomplete")


@dataclass(frozen=True)
class LocalStructuredGeneration:
    result: dict[str, Any] | None
    raw_text: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    parse_error: str = ""


class LocalTransformersResidentPool:
    """Keep all configured models resident and serialize generation on one GPU."""

    def __init__(
        self,
        specs: tuple[LocalTransformersModelSpec, ...],
        *,
        device: str = "cuda",
        dtype: str = "float16",
    ) -> None:
        if not specs or len({item.model_id for item in specs}) != len(specs):
            raise ValueError("local_transformers_model_specs_invalid")
        self.specs = specs
        self.device = device
        self.dtype = dtype
        self._resident: dict[str, tuple[Any, Any]] = {}
        self._generation_lock = threading.Lock()
        self._load_lock = threading.Lock()

    @property
    def resident_model_ids(self) -> tuple[str, ...]:
        return tuple(self._resident)

    @property
    def all_resident(self) -> bool:
        return set(self._resident) == {item.model_id for item in self.specs}

    def load_all(self) -> tuple[str, ...]:
        with self._load_lock:
            if self.all_resident:
                return self.resident_model_ids
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer

            if self.device.startswith("cuda") and not torch.cuda.is_available():
                raise RuntimeError("local_transformers_cuda_unavailable")
            torch_dtype = getattr(torch, self.dtype)
            for spec in self.specs:
                if spec.model_id in self._resident:
                    continue
                path = Path(spec.model_path).resolve()
                if not path.is_dir():
                    raise FileNotFoundError(f"local_transformers_model_path_missing:{path}")
                tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True)
                model = AutoModelForCausalLM.from_pretrained(
                    path,
                    dtype=torch_dtype,
                    device_map=self.device,
                    local_files_only=True,
                )
                model.eval()
                self._resident[spec.model_id] = (tokenizer, model)
        return self.resident_model_ids

    def unload_all(self) -> None:
        with self._load_lock, self._generation_lock:
            self._resident.clear()
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass

    def generate_json(
        self,
        *,
        model_id: str,
        messages: list[dict[str, str]],
        max_new_tokens: int,
    ) -> LocalStructuredGeneration:
        if not self.all_resident:
            raise RuntimeError("local_transformers_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"local_transformers_model_not_registered:{model_id}")
        if not isinstance(max_new_tokens, int) or max_new_tokens < 1:
            raise ValueError("local_transformers_max_new_tokens_invalid")
        with self._generation_lock:
            return self._generate_unlocked(model_id, messages, max_new_tokens)

    def _generate_unlocked(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        max_new_tokens: int,
    ) -> LocalStructuredGeneration:
        tokenizer, model = self._resident[model_id]
        prompt = self._render_prompt(tokenizer, messages)
        started = time.perf_counter()
        inputs = tokenizer(prompt, return_tensors="pt").to(self.device)
        input_tokens = int(inputs.input_ids.shape[1])
        import torch

        with torch.inference_mode():
            generated = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id,
            )
        output = generated[0][input_tokens:]
        raw_text = tokenizer.decode(output, skip_special_tokens=True)
        try:
            result = parse_json_object(raw_text)
            parse_error = ""
        except ValueError as exc:
            result = None
            parse_error = str(exc)
        return LocalStructuredGeneration(
            result=result,
            raw_text=raw_text,
            input_tokens=input_tokens,
            output_tokens=int(output.shape[0]),
            latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
            parse_error=parse_error,
        )

    @staticmethod
    def _render_prompt(tokenizer: Any, messages: list[dict[str, str]]) -> str:
        try:
            return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        except Exception as exc:
            if type(exc).__name__ != "TemplateError":
                raise
            merged = "\n\n".join(item["content"] for item in messages)
            return tokenizer.apply_chat_template(
                [{"role": "user", "content": merged}],
                tokenize=False,
                add_generation_prompt=True,
            )


class LocalTransformersJsonAdapter:
    """Expose one resident model through the bounded ProviderAdapter contract."""

    def __init__(
        self,
        *,
        provider_id: str,
        model_id: str,
        task_kinds: tuple[str, ...],
        pool: LocalTransformersResidentPool,
        telemetry_ledger: ProviderTelemetryLedger,
        max_new_tokens: int = 512,
        max_attempts: int = 2,
        max_timeout_seconds: int = 600,
    ) -> None:
        if not task_kinds or max_new_tokens < 1 or max_attempts < 1 or max_timeout_seconds < 1:
            raise ValueError("local_transformers_adapter_configuration_invalid")
        self.pool = pool
        self.telemetry_ledger = telemetry_ledger
        self.max_new_tokens = max_new_tokens
        self.max_attempts = max_attempts
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=task_kinds,
            local_model=True,
            max_timeout_seconds=max_timeout_seconds,
        )

    def invoke(self, task: ProviderCognitiveTask) -> dict[str, Any]:
        attempts: list[ProviderInvocationTelemetry] = []
        messages = self._messages(task)
        last_error = ""
        for _ in range(self.max_attempts):
            started = time.perf_counter()
            try:
                generated = self.pool.generate_json(
                    model_id=self.profile.model_id,
                    messages=messages,
                    max_new_tokens=self.max_new_tokens,
                )
            except Exception as exc:
                attempts.append(self._record_failure(task, started, exc))
                last_error = type(exc).__name__
                continue
            failures = (
                (generated.parse_error or "provider_response_json_invalid",)
                if generated.result is None
                else self._result_failures(task, generated.result)
            )
            telemetry = self._record_generation(
                task, generated, "FAILED" if failures else "COMPLETED", ";".join(failures)
            )
            attempts.append(telemetry)
            if not failures and generated.result is not None:
                return {
                    "result": generated.result,
                    "usage": {
                        "input_tokens": sum(item.input_tokens for item in attempts),
                        "output_tokens": sum(item.output_tokens for item in attempts),
                        "cached_tokens": 0,
                        "provider_calls": len(attempts),
                        "latency_ms": sum(item.latency_ms for item in attempts),
                    },
                    "provenance_refs": list(task.allowed_evidence),
                }
            last_error = ";".join(failures)
            messages = [*messages, {
                "role": "user",
                "content": (
                    f"The previous JSON was rejected for: {last_error}. Return a corrected JSON object only. "
                    f"When evidence_refs is present, use exactly: {json.dumps(task.allowed_evidence)}"
                ),
            }]
        raise ValueError(f"local_transformers_structured_output_invalid:{last_error}")

    def _messages(self, task: ProviderCognitiveTask) -> list[dict[str, str]]:
        return structured_json_messages(task)

    @staticmethod
    def _result_failures(task: ProviderCognitiveTask, result: dict[str, Any]) -> tuple[str, ...]:
        failures = list(schema_failures(task.expected_schema, result))
        refs = result.get("evidence_refs")
        if refs is not None and (
            not isinstance(refs, list)
            or not refs
            or len(refs) != len(set(refs))
            or not set(refs).issubset(task.allowed_evidence)
        ):
            failures.append("evidence_refs_outside_admitted_scope")
        return tuple(failures)

    def _record_generation(
        self,
        task: ProviderCognitiveTask,
        generated: LocalStructuredGeneration,
        status: str,
        error_type: str,
    ) -> ProviderInvocationTelemetry:
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"local-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="transformers-cuda",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(),
            status=status,
            input_tokens=generated.input_tokens,
            output_tokens=generated.output_tokens,
            cached_tokens=0,
            latency_ms=generated.latency_ms,
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(
                generated.result if generated.result is not None else generated.raw_text
            ),
            thinking_present=False,
            thinking_char_count=0,
            thinking_hash="",
            error_type=error_type,
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry

    def _record_failure(
        self, task: ProviderCognitiveTask, started: float, exc: Exception
    ) -> ProviderInvocationTelemetry:
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"local-failed-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="transformers-cuda",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(),
            status="FAILED",
            input_tokens=0,
            output_tokens=0,
            cached_tokens=0,
            latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash="",
            thinking_present=False,
            thinking_char_count=0,
            thinking_hash="",
            error_type=type(exc).__name__,
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry
