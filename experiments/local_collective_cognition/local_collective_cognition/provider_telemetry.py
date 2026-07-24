"""Hash-bound invocation telemetry shared by local Provider adapters."""

from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import dataclass
from hashlib import sha256
from typing import Any


PROVIDER_TELEMETRY_VERSION = "provider_invocation_telemetry_v0_1"
TELEMETRY_STATUSES = {"COMPLETED", "FAILED"}


def hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return sha256(encoded).hexdigest()


@dataclass(frozen=True)
class ProviderInvocationTelemetry:
    telemetry_id: str
    provider_id: str
    model_id: str
    backend: str
    task_id: str
    task_kind: str
    task_contract_hash: str
    status: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    latency_ms: int
    api_cost: float
    tool_calls: int
    tool_cost: float
    evidence_refs: tuple[str, ...]
    output_hash: str
    thinking_present: bool
    thinking_char_count: int
    thinking_hash: str
    error_type: str
    telemetry_hash: str

    def __post_init__(self) -> None:
        for name in ("telemetry_id", "provider_id", "model_id", "backend", "task_id", "task_kind"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"provider_telemetry_{name}_required")
        if self.status not in TELEMETRY_STATUSES:
            raise ValueError("provider_telemetry_status_invalid")
        for name in ("task_contract_hash", "output_hash"):
            value = getattr(self, name)
            if value and not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"provider_telemetry_{name}_invalid")
        for name in (
            "input_tokens", "output_tokens", "cached_tokens", "latency_ms",
            "tool_calls", "thinking_char_count",
        ):
            value = getattr(self, name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"provider_telemetry_{name}_invalid")
        for name in ("api_cost", "tool_cost"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) or value < 0:
                raise ValueError(f"provider_telemetry_{name}_invalid")
        if not self.evidence_refs or len(self.evidence_refs) != len(set(self.evidence_refs)):
            raise ValueError("provider_telemetry_evidence_refs_invalid")
        if self.thinking_present != bool(self.thinking_char_count or self.thinking_hash):
            raise ValueError("provider_telemetry_thinking_binding_invalid")
        if self.thinking_hash and not re.fullmatch(r"[0-9a-f]{64}", self.thinking_hash):
            raise ValueError("provider_telemetry_thinking_hash_invalid")
        if (self.status == "FAILED") != bool(self.error_type):
            raise ValueError("provider_telemetry_error_state_invalid")
        if self.telemetry_hash != hash_payload(self._committed_dict()):
            raise ValueError("provider_telemetry_hash_mismatch")

    @classmethod
    def create(cls, **values: Any) -> "ProviderInvocationTelemetry":
        committed = {
            **values,
            "evidence_refs": list(values["evidence_refs"]),
        }
        return cls(**values, telemetry_hash=hash_payload(committed))

    def _committed_dict(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "telemetry_hash"},
            "evidence_refs": list(self.evidence_refs),
        }

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed_dict(), "telemetry_hash": self.telemetry_hash}

    @property
    def evidence_ref(self) -> str:
        return f"provider-telemetry://{self.telemetry_hash}"


class ProviderTelemetryLedger:
    """Thread-safe in-memory source for one experiment window."""

    def __init__(self) -> None:
        self._items: list[ProviderInvocationTelemetry] = []
        self._hashes: set[str] = set()
        self._lock = threading.Lock()

    def record(self, telemetry: ProviderInvocationTelemetry) -> None:
        with self._lock:
            if telemetry.telemetry_hash in self._hashes:
                raise ValueError("duplicate_provider_telemetry")
            self._items.append(telemetry)
            self._hashes.add(telemetry.telemetry_hash)

    def items(self, *, task_ids: tuple[str, ...] = ()) -> tuple[ProviderInvocationTelemetry, ...]:
        with self._lock:
            items = tuple(self._items)
        if not task_ids:
            return items
        allowed = set(task_ids)
        return tuple(item for item in items if item.task_id in allowed)

    def clear(self) -> None:
        with self._lock:
            self._items.clear()
            self._hashes.clear()
