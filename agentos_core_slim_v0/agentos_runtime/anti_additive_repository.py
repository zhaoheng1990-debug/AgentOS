"""Append-only persistence for Anti-Additive Methodology receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentos_kernel import AntiAdditiveMethodologyReceipt
from agentos_kernel.contextual_policy_models import hash_payload

from .anti_additive_codec import anti_additive_receipt_from_dict


class AntiAdditiveMethodologyRepository:
    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.public_store_path = (
            Path(workspace_root).resolve() / "anti-additive-public" / runtime_id
        )
        self.public_store_path.mkdir(parents=True, exist_ok=True)
        self.events_path = self.public_store_path / "events.jsonl"
        self.snapshot_path = self.public_store_path / "snapshot.json"

    def persist_receipt(self, receipt: AntiAdditiveMethodologyReceipt) -> None:
        self.persist_event("ANTI_ADDITIVE_METHODOLOGY_REVIEWED", {"receipt": receipt.as_dict()})

    def receipts(self) -> tuple[AntiAdditiveMethodologyReceipt, ...]:
        return tuple(
            anti_additive_receipt_from_dict(event["payload"]["receipt"])
            for event in self._events()
            if isinstance(event.get("payload", {}).get("receipt"), dict)
        )

    def methodology_receipt(
        self, *, audit_id: str, project_scope: str
    ) -> AntiAdditiveMethodologyReceipt:
        if project_scope != self.project_scope:
            raise ValueError("anti_additive_methodology_source_scope_mismatch")
        matches = [item for item in self.receipts() if item.candidate.audit_id == audit_id]
        if not matches:
            raise KeyError(f"anti_additive_methodology_receipt_not_found:{audit_id}")
        return matches[-1]

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        events = self._events()
        committed = {
            "sequence": len(events) + 1,
            "previous_event_hash": events[-1]["event_hash"] if events else "",
            "event_type": event_type,
            "project_scope": self.project_scope,
            "runtime_id": self.runtime_id,
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "payload": payload,
        }
        event = {**committed, "event_hash": hash_payload(committed)}
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        self._write_snapshot(self._events())

    def verify_replay(self) -> dict[str, Any]:
        try:
            events = self._events()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {"valid": False, "failures": [f"event_parse_failed:{exc}"]}
        failures: list[str] = []
        previous = ""
        receipt_hashes = []
        latest_receipt_hashes: dict[str, str] = {}
        for index, event in enumerate(events, start=1):
            event_hash = event.get("event_hash", "")
            committed = {key: value for key, value in event.items() if key != "event_hash"}
            if event.get("sequence") != index:
                failures.append(f"event_sequence_invalid:{index}")
            if event.get("previous_event_hash") != previous:
                failures.append(f"event_parent_invalid:{index}")
            if event_hash != hash_payload(committed):
                failures.append(f"event_hash_invalid:{index}")
            if event.get("project_scope") != self.project_scope:
                failures.append(f"event_scope_invalid:{index}")
            receipt = event.get("payload", {}).get("receipt")
            if isinstance(receipt, dict):
                claimed = receipt.get("receipt_hash", "")
                receipt_committed = {
                    key: value
                    for key, value in receipt.items()
                    if key
                    not in {
                        "receipt_hash",
                        "baseline_write_authority",
                        "global_authority",
                        "production_activation",
                    }
                }
                if claimed != hash_payload(receipt_committed):
                    failures.append(f"receipt_hash_invalid:{index}")
                receipt_hashes.append(claimed)
                audit_id = receipt.get("candidate", {}).get("audit_id")
                if isinstance(audit_id, str) and audit_id:
                    latest_receipt_hashes[audit_id] = claimed
            previous = event_hash
        snapshot = self._snapshot()
        if snapshot:
            claimed_snapshot_hash = snapshot.get("snapshot_hash", "")
            snapshot_committed = {
                key: value for key, value in snapshot.items() if key != "snapshot_hash"
            }
            if claimed_snapshot_hash != hash_payload(snapshot_committed):
                failures.append("snapshot_hash_invalid")
            if (
                snapshot.get("runtime_id") != self.runtime_id
                or snapshot.get("project_scope") != self.project_scope
            ):
                failures.append("snapshot_scope_invalid")
        if events:
            if snapshot.get("latest_event_hash") != events[-1].get("event_hash"):
                failures.append("snapshot_head_invalid")
            if snapshot.get("event_count") != len(events):
                failures.append("snapshot_count_invalid")
        elif snapshot:
            failures.append("snapshot_without_events")
        return {
            "valid": not failures,
            "failures": failures,
            "event_count": len(events),
            "latest_event_hash": previous,
            "receipt_hashes": receipt_hashes,
            "latest_receipt_hashes": latest_receipt_hashes,
        }

    def _events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        return [
            json.loads(line)
            for line in self.events_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _snapshot(self) -> dict[str, Any]:
        if not self.snapshot_path.exists():
            return {}
        return json.loads(self.snapshot_path.read_text(encoding="utf-8"))

    def _write_snapshot(self, events: list[dict[str, Any]]) -> None:
        payload = {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "event_count": len(events),
            "latest_event_hash": events[-1]["event_hash"] if events else "",
            "latest_receipt": next(
                (
                    event["payload"]["receipt"]
                    for event in reversed(events)
                    if isinstance(event.get("payload", {}).get("receipt"), dict)
                ),
                None,
            ),
        }
        payload["snapshot_hash"] = hash_payload(payload)
        self.snapshot_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
