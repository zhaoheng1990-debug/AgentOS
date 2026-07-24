"""Native Ollama structured-output adapter with separated thinking telemetry."""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

from agentos_kernel import ProviderCapabilityProfile, ProviderCognitiveTask

from .provider_telemetry import ProviderInvocationTelemetry, ProviderTelemetryLedger, hash_payload
from .structured_provider_json import parse_json_object, schema_failures, structured_json_messages


OLLAMA_JSON_ADAPTER_VERSION = "ollama_json_adapter_v0_1"


class OllamaJsonAdapter:
    """Use Ollama JSON Schema output without mixing private thinking into results."""

    def __init__(
        self,
        *,
        provider_id: str,
        model_id: str,
        task_kinds: tuple[str, ...],
        telemetry_ledger: ProviderTelemetryLedger,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: int = 600,
        max_new_tokens: int = 2048,
        max_attempts: int = 2,
        thinking_enabled: bool = False,
        keep_alive: str | int = "5m",
    ) -> None:
        if not task_kinds or timeout_seconds < 1 or max_new_tokens < 1 or max_attempts < 1:
            raise ValueError("ollama_adapter_configuration_invalid")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_new_tokens = max_new_tokens
        self.max_attempts = max_attempts
        self.thinking_enabled = thinking_enabled
        self.keep_alive = keep_alive
        self.telemetry_ledger = telemetry_ledger
        self._thinking: dict[str, str] = {}
        self._thinking_lock = threading.Lock()
        self.profile = ProviderCapabilityProfile(
            provider_id=provider_id,
            model_id=model_id,
            task_kinds=task_kinds,
            supports_thinking_mode=thinking_enabled,
            local_model=True,
            custom_endpoint=self.base_url,
            max_timeout_seconds=timeout_seconds,
        )

    def invoke(self, task: ProviderCognitiveTask) -> dict[str, Any]:
        attempts: list[ProviderInvocationTelemetry] = []
        messages = self._messages(task)
        last_error = ""
        for _ in range(self.max_attempts):
            started = time.perf_counter()
            try:
                response = self._post({
                    "model": self.profile.model_id,
                    "messages": messages,
                    "format": task.expected_schema,
                    "think": self.thinking_enabled,
                    "stream": False,
                    "keep_alive": self.keep_alive,
                    "options": {"temperature": 0, "num_predict": self.max_new_tokens},
                })
                message = response.get("message") or {}
                content = message.get("content") or ""
                thinking = message.get("thinking") or ""
            except Exception as exc:
                attempts.append(self._record_failure(task, started, exc))
                last_error = type(exc).__name__
                continue
            try:
                result = parse_json_object(content)
                parse_error = ""
            except ValueError as exc:
                result = None
                parse_error = str(exc)
            failures = (
                (parse_error or "provider_response_json_invalid",)
                if result is None
                else self._result_failures(task, result)
            )
            telemetry = self._record_response(
                task, response, result, content, thinking, started,
                "FAILED" if failures else "COMPLETED", ";".join(failures),
            )
            attempts.append(telemetry)
            if thinking:
                with self._thinking_lock:
                    prior = self._thinking.get(task.task_id, "")
                    self._thinking[task.task_id] = f"{prior}\n\n{thinking}".strip()
            if not failures and result is not None:
                return {
                    "result": result,
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
                    f"The previous JSON was rejected for: {last_error}. Return corrected JSON only. "
                    f"Use evidence_refs exactly: {json.dumps(task.allowed_evidence)}"
                ),
            }]
        raise ValueError(f"ollama_structured_output_invalid:{last_error}")

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

    def _record_response(
        self,
        task: ProviderCognitiveTask,
        response: dict[str, Any],
        result: dict[str, Any] | None,
        content: str,
        thinking: str,
        started: float,
        status: str,
        error_type: str,
    ) -> ProviderInvocationTelemetry:
        latency_ms = max(1, round((time.perf_counter() - started) * 1000))
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"ollama-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="ollama-native-json",
            task_id=task.task_id,
            task_kind=task.task_kind,
            task_contract_hash=task.contract_hash(),
            status=status,
            input_tokens=int(response.get("prompt_eval_count") or 0),
            output_tokens=int(response.get("eval_count") or 0),
            cached_tokens=0,
            latency_ms=latency_ms,
            api_cost=0.0,
            tool_calls=0,
            tool_cost=0.0,
            evidence_refs=tuple(task.allowed_evidence),
            output_hash=hash_payload(result if result is not None else content),
            thinking_present=bool(thinking),
            thinking_char_count=len(thinking),
            thinking_hash=hash_payload(thinking) if thinking else "",
            error_type=error_type,
        )
        self.telemetry_ledger.record(telemetry)
        return telemetry

    def thinking_text(self, task_id: str) -> str:
        with self._thinking_lock:
            return self._thinking.get(task_id, "")

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            value = json.loads(response.read().decode("utf-8"))
        if not isinstance(value, dict) or not value.get("done"):
            raise ValueError("ollama_response_incomplete")
        return value

    def _record_failure(
        self, task: ProviderCognitiveTask, started: float, exc: Exception
    ) -> ProviderInvocationTelemetry:
        telemetry = ProviderInvocationTelemetry.create(
            telemetry_id=f"ollama-failed-{task.task_id}-{time.time_ns()}",
            provider_id=self.profile.provider_id,
            model_id=self.profile.model_id,
            backend="ollama-native-json",
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
