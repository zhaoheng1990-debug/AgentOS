"""Bounded DeepSeek JSON adapter with local attempt receipts."""

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
    prompt_sha256: str
    status: str
    error: str | None
    model: str
    usage: dict[str, int]


class DeepSeekAdapter:
    def __init__(self, checkpoint_path: Path | None = None) -> None:
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
        self.checkpoint_path = checkpoint_path
        self.attempt_receipts: list[AttemptReceipt] = []

    @staticmethod
    def _usage(response: Any) -> dict[str, int]:
        usage_object = response.usage
        return {
            "prompt_tokens": int(getattr(usage_object, "prompt_tokens", 0) or 0),
            "completion_tokens": int(
                getattr(usage_object, "completion_tokens", 0) or 0
            ),
            "total_tokens": int(getattr(usage_object, "total_tokens", 0) or 0),
            "cache_hit_tokens": int(
                getattr(
                    getattr(usage_object, "prompt_tokens_details", None),
                    "cached_tokens",
                    0,
                )
                or 0
            ),
        }

    def _record(self, receipt: AttemptReceipt) -> None:
        self.attempt_receipts.append(receipt)
        if self.checkpoint_path is not None:
            self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            self.checkpoint_path.write_text(
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
        prompt_hash = hashlib.sha256(
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
            response_model = self.model
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.0,
                    max_tokens=6000,
                    extra_body={"thinking": {"type": "disabled"}},
                )
                usage = self._usage(response)
                response_model = str(response.model)
                content = response.choices[0].message.content or ""
                parsed = validator(content)
                self._record(
                    AttemptReceipt(
                        logical_call_id=logical_call_id,
                        attempt=attempt,
                        prompt_sha256=prompt_hash,
                        status="VALID",
                        error=None,
                        model=response_model,
                        usage=usage,
                    )
                )
                return content, parsed
            except Exception as error:
                last_error = f"{type(error).__name__}:{error}"
                self._record(
                    AttemptReceipt(
                        logical_call_id=logical_call_id,
                        attempt=attempt,
                        prompt_sha256=prompt_hash,
                        status="INVALID",
                        error=last_error,
                        model=response_model,
                        usage=usage,
                    )
                )
        raise RuntimeError(f"{logical_call_id} failed after two attempts: {last_error}")

    def ledger(self) -> list[dict[str, Any]]:
        return [asdict(receipt) for receipt in self.attempt_receipts]
