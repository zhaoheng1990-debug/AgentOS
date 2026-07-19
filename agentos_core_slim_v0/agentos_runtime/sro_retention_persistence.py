"""Filesystem adapters for SRO runtime ledgers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class JsonlDelayedRetrievalEventStore:
    """Append-only JSONL adapter implementing the Kernel event-store port."""

    def __init__(self, events_path: str | Path) -> None:
        self.events_path = Path(events_path).resolve()
        self.events_path.parent.mkdir(parents=True, exist_ok=True)

    def load_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        try:
            return [
                json.loads(line)
                for line in self.events_path.read_text(encoding="utf-8").splitlines()
                if line
            ]
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("delayed_retrieval_ledger_unreadable") from exc

    def append_event(self, event: dict[str, Any]) -> None:
        with self.events_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def current_head(self) -> str:
        if not self.events_path.exists():
            return ""
        try:
            lines = [line for line in self.events_path.read_text(encoding="utf-8").splitlines() if line]
            return json.loads(lines[-1])["event_hash"] if lines else ""
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            raise RuntimeError("delayed_retrieval_ledger_persistent_head_unreadable") from exc
