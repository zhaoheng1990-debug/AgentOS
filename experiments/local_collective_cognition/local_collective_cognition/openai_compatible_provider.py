"""Small OpenAI-compatible JSON transport for workstation-local experiments."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from agentos_kernel import ProviderCapabilityProfile, ProviderCognitiveTask

from .structured_provider_json import parse_json_object


@dataclass(frozen=True)
class OpenAICompatibleProviderSpec:
    provider_id: str
    model_id: str
    endpoint: str
    api_key_env: str
    task_kinds: tuple[str, ...]
    max_tokens: int = 4096
    timeout_seconds: int = 180
    extra_body: dict[str, Any] | None = None


class OpenAICompatibleJsonAdapter:
    def __init__(self, spec: OpenAICompatibleProviderSpec):
        if not spec.task_kinds or spec.max_tokens < 1 or spec.timeout_seconds < 1:
            raise ValueError("openai_compatible_provider_spec_invalid")
        self.spec = spec
        self.profile = ProviderCapabilityProfile(
            provider_id=spec.provider_id, model_id=spec.model_id,
            task_kinds=spec.task_kinds,
            supports_thinking_mode=bool((spec.extra_body or {}).get("thinking")),
            custom_endpoint=spec.endpoint, max_timeout_seconds=spec.timeout_seconds,
        )

    def invoke(self, task: ProviderCognitiveTask):
        api_key = os.environ.get(self.spec.api_key_env, "")
        if not api_key:
            raise RuntimeError(f"provider_api_key_missing:{self.spec.api_key_env}")
        payload = {
            "model": self.spec.model_id,
            "messages": [
                {"role": "system", "content": (
                    "You are a bounded anonymous semantic assessor. Use only supplied public input, "
                    "preserve uncertainty, do not infer candidate identity, and return JSON only."
                )},
                {"role": "user", "content": (
                    f"Objective:\n{task.objective}\n\n"
                    "Return one JSON object matching this contract exactly:\n"
                    f"{json.dumps(task.expected_schema, indent=2)}\n\n"
                    f"Inputs:\n{json.dumps(task.inputs, indent=2, sort_keys=True)}\n\n"
                    f"Use exactly these evidence_refs: {json.dumps(task.allowed_evidence)}"
                )},
            ],
            "stream": False,
            "max_tokens": self.spec.max_tokens,
            "response_format": {"type": "json_object"},
            **(self.spec.extra_body or {}),
        }
        response = self._post(payload, api_key)
        result = parse_json_object(response["choices"][0]["message"].get("content") or "")
        return {
            "result": result,
            "usage": response.get("usage") or {},
            "provenance_refs": list(task.allowed_evidence),
        }

    def _post(self, payload, api_key):
        try:
            return self._post_once(payload, api_key)
        except urllib.error.HTTPError as exc:
            if exc.code != 400 or "response_format" not in payload:
                raise
            fallback = dict(payload)
            fallback.pop("response_format", None)
            return self._post_once(fallback, api_key)

    def _post_once(self, payload, api_key):
        request = urllib.request.Request(
            self.spec.endpoint, data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.spec.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
