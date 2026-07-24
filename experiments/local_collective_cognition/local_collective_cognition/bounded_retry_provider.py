"""Bounded same-contract transport retry for local experiments."""

from __future__ import annotations

import time


class BoundedRetryProviderAdapter:
    def __init__(self, adapter, *, max_attempts=2, delay_seconds=1.0):
        if max_attempts < 1 or delay_seconds < 0:
            raise ValueError("bounded_retry_configuration_invalid")
        self.adapter = adapter
        self.profile = adapter.profile
        self.max_attempts = max_attempts
        self.delay_seconds = delay_seconds

    def invoke(self, task):
        errors = []
        for attempt in range(1, self.max_attempts + 1):
            try:
                result = self.adapter.invoke(task)
            except Exception as exc:
                errors.append(type(exc).__name__)
                if attempt < self.max_attempts and self.delay_seconds:
                    time.sleep(self.delay_seconds)
                continue
            usage = dict(result.get("usage") or {})
            usage["provider_calls"] = (
                int(usage.get("provider_calls") or 1) + attempt - 1
            )
            return {**result, "usage": usage}
        raise RuntimeError(
            "bounded_retry_exhausted:" + ",".join(errors)
        )
