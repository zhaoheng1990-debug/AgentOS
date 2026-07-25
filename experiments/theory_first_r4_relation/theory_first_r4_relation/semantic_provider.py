"""Bounded DeepSeek adapter for fresh semantic relation receipts."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI


@dataclass(frozen=True)
class AttemptReceipt:
    logical_call_id: str
    attempt: int
    status: str
    error: str | None
    prompt_sha256: str
    response_sha256: str | None
    response_path: str | None
    model: str
    usage: dict[str, int]


class DeepSeekSemanticAdapter:
    def __init__(
        self, output_dir: Path, max_completion_tokens: int = 5000
    ) -> None:
        api_key = os.environ.get("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com",
            timeout=180.0,
            max_retries=0,
        )
        self.model = "deepseek-v4-flash"
        self.max_completion_tokens = max_completion_tokens
        self.output_dir = output_dir
        self.attempts: list[AttemptReceipt] = []

    @staticmethod
    def _usage(response: Any) -> dict[str, int]:
        usage = response.usage
        return {
            "prompt_tokens": int(getattr(usage, "prompt_tokens", 0) or 0),
            "completion_tokens": int(getattr(usage, "completion_tokens", 0) or 0),
            "total_tokens": int(getattr(usage, "total_tokens", 0) or 0),
            "cache_hit_tokens": int(
                getattr(
                    getattr(usage, "prompt_tokens_details", None),
                    "cached_tokens",
                    0,
                )
                or 0
            ),
        }

    def _record(self, receipt: AttemptReceipt) -> None:
        self.attempts.append(receipt)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (self.output_dir / "attempt_ledger_checkpoint.json").write_text(
            json.dumps(self.ledger(), ensure_ascii=True, indent=2, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    def call_json(
        self,
        logical_call_id: str,
        system_prompt: str,
        user_prompt: str,
        validator: Callable[[str], Any],
    ) -> tuple[str, Any]:
        prompt_sha256 = hashlib.sha256(
            json.dumps(
                {"system": system_prompt, "user": user_prompt},
                ensure_ascii=True,
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()
        last_error = "unknown"
        for attempt in (1, 2):
            usage = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
                "cache_hit_tokens": 0,
            }
            model = self.model
            response_sha256 = None
            response_path = None
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=self.max_completion_tokens,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                usage = self._usage(response)
                model = str(response.model)
                content = response.choices[0].message.content or ""
                response_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
                raw_dir = self.output_dir / "raw_attempts"
                raw_dir.mkdir(parents=True, exist_ok=True)
                raw_path = raw_dir / f"{logical_call_id}_attempt_{attempt}.json.txt"
                raw_path.write_text(content, encoding="utf-8")
                response_path = str(raw_path)
                parsed = validator(content)
                self._record(
                    AttemptReceipt(
                        logical_call_id,
                        attempt,
                        "VALID",
                        None,
                        prompt_sha256,
                        response_sha256,
                        response_path,
                        model,
                        usage,
                    )
                )
                return content, parsed
            except Exception as error:
                last_error = f"{type(error).__name__}:{error}"
                self._record(
                    AttemptReceipt(
                        logical_call_id,
                        attempt,
                        "INVALID",
                        last_error,
                        prompt_sha256,
                        response_sha256,
                        response_path,
                        model,
                        usage,
                    )
                )
        raise RuntimeError(
            f"{logical_call_id} failed after two attempts: {last_error}"
        )

    def ledger(self) -> list[dict[str, Any]]:
        return [asdict(receipt) for receipt in self.attempts]
