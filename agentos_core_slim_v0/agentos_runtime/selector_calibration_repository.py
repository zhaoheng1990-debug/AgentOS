"""Append-only ledger and replay for Selector calibration revisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel import (
    SelectorCalibrationDecision,
    SelectorCalibrationObservation,
    SelectorCalibrationProfile,
    SelectorCalibrationProviderJudgment,
    SelectorCalibrationReceipt,
)
from agentos_kernel.contextual_policy_models import hash_payload

from .deliberation import DeliberationEventStore
from .selector_calibration_contracts import (
    SELECTOR_CALIBRATION_RUNTIME_VERSION,
    SelectorCalibrationSnapshot,
    selector_calibration_scope_key,
)


class SelectorCalibrationRepository:
    """Own immutable revisions, exact-scope lineage, and deterministic replay."""

    def __init__(self, *, runtime_id: str, project_scope: str, workspace_root: str | Path) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self._receipts: dict[str, SelectorCalibrationReceipt] = {}
        self._latest: dict[tuple[str, str, str], str] = {}
        self._feedback_hashes: set[str] = set()
        self._trial_keys: set[tuple[str, str, str, str]] = set()
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "selector-calibration-public", runtime_id)
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    def receipt(self, calibration_id: str) -> SelectorCalibrationReceipt | None:
        return self._receipts.get(calibration_id)

    def receipts(self) -> tuple[SelectorCalibrationReceipt, ...]:
        return tuple(self._receipts.values())

    def observations(
        self, *, context_key: str, evidence_tier: str, policy_id: str
    ) -> tuple[SelectorCalibrationObservation, ...]:
        return tuple(
            item.observation
            for item in self.receipts()
            if (
                item.observation.context_key,
                item.observation.evidence_tier,
                item.observation.policy_id,
            )
            == (context_key, evidence_tier, policy_id)
        )

    def latest(self, *, context_key: str, evidence_tier: str, policy_id: str):
        item_id = self._latest.get((context_key, evidence_tier, policy_id))
        return self._receipts.get(item_id) if item_id else None

    def save(self, receipt: SelectorCalibrationReceipt) -> None:
        self._validate_new(receipt)
        key = self._key(receipt)
        prior = self._latest.get(key)
        self._index(receipt)
        try:
            self._persist("SELECTOR_CALIBRATION_RECORDED", {"receipt": receipt.as_dict()})
        except Exception:
            self._deindex(receipt, prior)
            raise

    def persist_blocked(self, payload: dict[str, Any]) -> None:
        self._persist("SELECTOR_CALIBRATION_BLOCKED", payload)

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._persist(event_type, payload)

    def snapshot(self) -> SelectorCalibrationSnapshot:
        return SelectorCalibrationSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            receipts=self.receipts(),
        )

    def verify_replay(self) -> dict[str, Any]:
        event_replay = self._event_store.verify()
        current = self._snapshot_is_current()
        failures = [f"events:{item}" for item in event_replay["failures"]]
        if not current:
            failures.append("snapshot_state_mismatch")
        return {
            "valid": not failures,
            "event_replay": event_replay,
            "snapshot_state_current": current,
            "receipt_count": len(self._receipts),
            "profile_count": len(self._latest),
            "latest_receipt_hashes": {
                selector_calibration_scope_key(
                    context_key=context_key,
                    evidence_tier=evidence_tier,
                    policy_id=policy_id,
                ): self._receipts[calibration_id].receipt_hash
                for (context_key, evidence_tier, policy_id), calibration_id in self._latest.items()
            },
            "failures": failures,
        }

    @staticmethod
    def _key(receipt: SelectorCalibrationReceipt) -> tuple[str, str, str]:
        item = receipt.observation
        return item.context_key, item.evidence_tier, item.policy_id

    def _validate_new(self, receipt: SelectorCalibrationReceipt) -> None:
        if receipt.calibration_id in self._receipts:
            raise ValueError(f"duplicate_selector_calibration:{receipt.calibration_id}")
        if receipt.observation.project_scope != self.project_scope:
            raise ValueError("selector_calibration_repository_scope_mismatch")
        if receipt.observation.feedback_receipt_hash in self._feedback_hashes:
            raise ValueError("duplicate_selector_calibration_feedback")
        trial_key = (*self._key(receipt), receipt.observation.trial_group_id)
        if trial_key in self._trial_keys:
            raise ValueError("duplicate_selector_calibration_trial_group")
        latest = self.latest(
            context_key=receipt.observation.context_key,
            evidence_tier=receipt.observation.evidence_tier,
            policy_id=receipt.observation.policy_id,
        )
        expected = latest.receipt_hash if latest else ""
        if receipt.supersedes_receipt_hash != expected:
            raise ValueError("selector_calibration_revision_predecessor_mismatch")
        if latest is not None and receipt.profile.threshold_hash != latest.profile.threshold_hash:
            raise ValueError("selector_calibration_lineage_threshold_change_forbidden")
        expected_observations = (*self.observations(
            context_key=receipt.observation.context_key,
            evidence_tier=receipt.observation.evidence_tier,
            policy_id=receipt.observation.policy_id,
        ), receipt.observation)
        if receipt.profile.observation_hashes != tuple(item.observation_hash for item in expected_observations):
            raise ValueError("selector_calibration_profile_history_mismatch")

    def _index(self, receipt: SelectorCalibrationReceipt) -> None:
        self._receipts[receipt.calibration_id] = receipt
        self._latest[self._key(receipt)] = receipt.calibration_id
        self._feedback_hashes.add(receipt.observation.feedback_receipt_hash)
        self._trial_keys.add((*self._key(receipt), receipt.observation.trial_group_id))

    def _deindex(self, receipt: SelectorCalibrationReceipt, prior: str | None) -> None:
        self._receipts.pop(receipt.calibration_id, None)
        key = self._key(receipt)
        if prior:
            self._latest[key] = prior
        else:
            self._latest.pop(key, None)
        self._feedback_hashes.discard(receipt.observation.feedback_receipt_hash)
        self._trial_keys.discard((*key, receipt.observation.trial_group_id))

    def _persist(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def _initialize_or_replay(self) -> None:
        events = self._event_store.events()
        if not events:
            self._persist(
                "SELECTOR_CALIBRATION_INITIALIZED",
                {"project_scope": self.project_scope, "module_id": SELECTOR_CALIBRATION_RUNTIME_VERSION},
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("selector_calibration_replay_invalid:" + ";".join(verification["failures"]))
        for event in events:
            event_type = event.get("event_type")
            payload = event.get("payload") or {}
            if event_type == "SELECTOR_CALIBRATION_RECORDED":
                receipt = self._receipt_from_dict(payload["receipt"])
                self._validate_new(receipt)
                self._index(receipt)
            elif event_type not in {
                "SELECTOR_CALIBRATION_INITIALIZED",
                "SELECTOR_CALIBRATION_PROVIDER_BLOCKED",
                "SELECTOR_CALIBRATION_BLOCKED",
            }:
                raise ValueError(f"unknown_selector_calibration_event:{event_type}")
        if not self._snapshot_is_current():
            raise ValueError("selector_calibration_snapshot_state_mismatch")

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        payload = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return payload.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @staticmethod
    def _receipt_from_dict(payload: dict[str, Any]) -> SelectorCalibrationReceipt:
        item = dict(payload)
        for key in ("global_policy_authority", "production_activation"):
            item.pop(key, None)
        observation = dict(item["observation"])
        observation["evidence_refs"] = tuple(observation["evidence_refs"])
        profile = dict(item["profile"])
        profile.pop("evidence_ref", None)
        profile["observation_hashes"] = tuple(profile["observation_hashes"])
        profile["source_result_hashes"] = tuple(profile["source_result_hashes"])
        judgment = dict(item["provider_judgment"])
        judgment["drift_drivers"] = tuple(judgment["drift_drivers"])
        judgment["evidence_refs"] = tuple(judgment["evidence_refs"])
        decision = dict(item["kernel_decision"])
        for key in ("global_policy_authority", "production_activation"):
            decision.pop(key, None)
        return SelectorCalibrationReceipt(
            calibration_id=item["calibration_id"],
            runtime_id=item["runtime_id"],
            observation=SelectorCalibrationObservation(**observation),
            profile=SelectorCalibrationProfile(**profile),
            provider_judgment=SelectorCalibrationProviderJudgment(**judgment),
            kernel_decision=SelectorCalibrationDecision(**decision),
            supersedes_receipt_hash=item["supersedes_receipt_hash"],
            created_at=item["created_at"],
            receipt_hash=item["receipt_hash"],
            candidate_state=item["candidate_state"],
        )
