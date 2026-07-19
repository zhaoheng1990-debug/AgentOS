"""Persistent exact-scope ledger for Anti-Additive calibration receipts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agentos_kernel import (
    AntiAdditiveCalibrationDecision,
    AntiAdditiveCalibrationObservation,
    AntiAdditiveCalibrationProfile,
    AntiAdditiveCalibrationReceipt,
)
from agentos_kernel.contextual_policy_models import hash_payload


def anti_additive_calibration_scope_key(project_scope: str, change_kind: str, target_type: str) -> str:
    return "|".join((project_scope, change_kind, target_type))


class AntiAdditiveCalibrationRepository:
    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.public_store_path = Path(workspace_root).resolve() / "anti-additive-calibration-public" / runtime_id
        self.public_store_path.mkdir(parents=True, exist_ok=True)
        self.events_path = self.public_store_path / "events.jsonl"
        self.snapshot_path = self.public_store_path / "snapshot.json"

    def save(self, receipt: AntiAdditiveCalibrationReceipt) -> None:
        events = self._events()
        committed = {
            "sequence": len(events) + 1,
            "previous_event_hash": events[-1]["event_hash"] if events else "",
            "event_type": "ANTI_ADDITIVE_CALIBRATION_RECORDED",
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
            "payload": {"receipt": receipt.as_dict()},
        }
        event = {**committed, "event_hash": hash_payload(committed)}
        with self.events_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")
        self._write_snapshot(self.receipts())

    def receipts(self) -> tuple[AntiAdditiveCalibrationReceipt, ...]:
        return tuple(
            self._receipt(event["payload"]["receipt"])
            for event in self._events()
            if isinstance(event.get("payload", {}).get("receipt"), dict)
        )

    def observations(self) -> tuple[AntiAdditiveCalibrationObservation, ...]:
        return tuple(item.observation for item in self.receipts())

    def latest_calibration_receipt(
        self, *, project_scope: str, change_kind: str, target_type: str
    ) -> AntiAdditiveCalibrationReceipt | None:
        matches = [
            item
            for item in self.receipts()
            if (
                item.decision.project_scope,
                item.decision.change_kind,
                item.decision.target_type,
            )
            == (project_scope, change_kind, target_type)
        ]
        return matches[-1] if matches else None

    def verify_replay(self) -> dict[str, Any]:
        try:
            events = self._events()
            receipts = self.receipts()
        except Exception as exc:
            return {"valid": False, "failures": [f"anti_additive_calibration_parse_failed:{exc}"]}
        failures = []
        previous = ""
        for index, event in enumerate(events, start=1):
            committed = {key: value for key, value in event.items() if key != "event_hash"}
            if event.get("sequence") != index:
                failures.append(f"event_sequence_invalid:{index}")
            if event.get("previous_event_hash") != previous:
                failures.append(f"event_parent_invalid:{index}")
            if event.get("event_hash") != hash_payload(committed):
                failures.append(f"event_hash_invalid:{index}")
            if event.get("project_scope") != self.project_scope:
                failures.append(f"event_scope_invalid:{index}")
            previous = event.get("event_hash", "")
        latest: dict[str, str] = {}
        for receipt in receipts:
            key = anti_additive_calibration_scope_key(
                receipt.decision.project_scope,
                receipt.decision.change_kind,
                receipt.decision.target_type,
            )
            latest[key] = receipt.receipt_hash
        snapshot = self._snapshot()
        if events and (
            snapshot.get("latest_event_hash") != previous
            or snapshot.get("event_count") != len(events)
            or snapshot.get("latest_receipt_hashes") != latest
        ):
            failures.append("snapshot_projection_invalid")
        if snapshot:
            committed = {key: value for key, value in snapshot.items() if key != "snapshot_hash"}
            if snapshot.get("snapshot_hash") != hash_payload(committed):
                failures.append("snapshot_hash_invalid")
        return {
            "valid": not failures,
            "failures": failures,
            "event_count": len(events),
            "latest_event_hash": previous,
            "latest_receipt_hashes": latest,
        }

    def _events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        return [json.loads(line) for line in self.events_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _snapshot(self) -> dict[str, Any]:
        return json.loads(self.snapshot_path.read_text(encoding="utf-8")) if self.snapshot_path.exists() else {}

    def _write_snapshot(self, receipts: tuple[AntiAdditiveCalibrationReceipt, ...]) -> None:
        events = self._events()
        latest = {}
        for receipt in receipts:
            key = anti_additive_calibration_scope_key(
                receipt.decision.project_scope, receipt.decision.change_kind, receipt.decision.target_type
            )
            latest[key] = receipt.receipt_hash
        payload = {
            "runtime_id": self.runtime_id,
            "project_scope": self.project_scope,
            "event_count": len(events),
            "latest_event_hash": events[-1]["event_hash"] if events else "",
            "latest_receipt_hashes": latest,
        }
        payload["snapshot_hash"] = hash_payload(payload)
        self.snapshot_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    @staticmethod
    def _receipt(payload: dict[str, Any]) -> AntiAdditiveCalibrationReceipt:
        observation = AntiAdditiveCalibrationObservation(**{
            **payload["observation"],
            "evidence_refs": tuple(payload["observation"]["evidence_refs"]),
        })
        profile = AntiAdditiveCalibrationProfile(**{
            **payload["profile"],
            "observation_hashes": tuple(payload["profile"]["observation_hashes"]),
            "outcome_source_hashes": tuple(payload["profile"]["outcome_source_hashes"]),
        })
        decision = AntiAdditiveCalibrationDecision(**payload["decision"])
        return AntiAdditiveCalibrationReceipt(
            observation=observation,
            profile=profile,
            decision=decision,
            created_at=payload["created_at"],
            receipt_hash=payload["receipt_hash"],
        )
