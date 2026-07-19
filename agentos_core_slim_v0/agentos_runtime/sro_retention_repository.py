"""SRO runtime state repository, event replay, and snapshot verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from agentos_kernel import DelayedRetrievalLedger, SerialSelectionWitness

from .deliberation import DeliberationEventStore
from .sro_retention_contracts import (
    LegacyRetentionMigrationCandidate,
    SRORetentionRouteReceipt,
    SRORetentionRuntimeSnapshot,
    hash_payload,
)
from .sro_retention_persistence import JsonlDelayedRetrievalEventStore


class SRORetentionRepository:
    """Own durable runtime state while domain services remain stateless."""

    def __init__(
        self,
        *,
        runtime_id: str,
        project_scope: str,
        module_id: str,
        workspace_root: str | Path,
    ) -> None:
        self.runtime_id = runtime_id
        self.project_scope = project_scope
        self.module_id = module_id
        self._migrations: dict[str, LegacyRetentionMigrationCandidate] = {}
        self._witnesses: dict[str, SerialSelectionWitness] = {}
        self._route_receipts: dict[str, SRORetentionRouteReceipt] = {}
        root = Path(workspace_root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        self._event_store = DeliberationEventStore(root / "sro-retention-public", runtime_id)
        self.delayed_ledger = DelayedRetrievalLedger(
            JsonlDelayedRetrievalEventStore(
                self._event_store.path / "delayed_retrieval_events.jsonl"
            )
        )
        self._initialize_or_replay()

    @property
    def public_store_path(self) -> Path:
        return self._event_store.path

    @property
    def route_count(self) -> int:
        return len(self._route_receipts)

    def migration(self, migration_id: str) -> LegacyRetentionMigrationCandidate | None:
        return self._migrations.get(migration_id)

    def migration_by_legacy_hash(self, legacy_hash: str) -> LegacyRetentionMigrationCandidate | None:
        return next(
            (item for item in self._migrations.values() if item.legacy_candidate_hash == legacy_hash),
            None,
        )

    def witness(self, witness_id: str) -> SerialSelectionWitness | None:
        return self._witnesses.get(witness_id)

    def route_receipt(self, route_receipt_id: str) -> SRORetentionRouteReceipt | None:
        return self._route_receipts.get(route_receipt_id)

    def save_migration_created(self, migration: LegacyRetentionMigrationCandidate) -> None:
        self._migrations[migration.migration_id] = migration
        self.persist_event(
            "LEGACY_RETENTION_MIGRATION_CANDIDATE_CREATED",
            {"migration": migration.as_dict()},
        )

    def save_migration_revalidated(
        self,
        migration: LegacyRetentionMigrationCandidate,
        *,
        revalidated_candidate_hash: str,
        kernel_authorization_ref: str,
    ) -> None:
        self._migrations[migration.migration_id] = migration
        self.persist_event(
            "LEGACY_RETENTION_MIGRATION_REVALIDATED",
            {
                "migration": migration.as_dict(),
                "revalidated_candidate_hash": revalidated_candidate_hash,
                "kernel_authorization_ref": kernel_authorization_ref,
            },
        )

    def register_witness(
        self,
        witness: SerialSelectionWitness,
        *,
        kernel_authorization_ref: str,
        migration: LegacyRetentionMigrationCandidate | None = None,
    ) -> None:
        if not kernel_authorization_ref.startswith("kernel://"):
            raise ValueError("sro_witness_registration_kernel_authority_required")
        if witness.witness_id in self._witnesses:
            raise ValueError(f"duplicate_sro_witness:{witness.witness_id}")
        if witness.project_scope_ref != self.project_scope:
            raise ValueError("sro_witness_project_scope_mismatch")
        if migration is not None:
            if witness.selection_context_ref != f"migration://{migration.migration_id}":
                raise ValueError("migrated_witness_selection_context_mismatch")
            self._migrations[migration.migration_id] = migration
        self._witnesses[witness.witness_id] = witness
        self.persist_event(
            "SRO_WITNESS_REGISTERED",
            {
                "witness": witness.as_dict(),
                "kernel_authorization_ref": kernel_authorization_ref,
                "migration": migration.as_dict() if migration else None,
            },
        )

    def save_route(self, route_receipt: SRORetentionRouteReceipt) -> None:
        route_id = route_receipt.route_receipt_id
        if route_id in self._route_receipts:
            raise ValueError(f"duplicate_sro_route_receipt:{route_id}")
        self._route_receipts[route_id] = route_receipt
        self.persist_event("SRO_RETENTION_ROUTE_DECIDED", {"route_receipt": route_receipt.as_dict()})

    def snapshot(self) -> SRORetentionRuntimeSnapshot:
        return SRORetentionRuntimeSnapshot(
            runtime_id=self.runtime_id,
            project_scope=self.project_scope,
            migrations=tuple(sorted(self._migrations.values(), key=lambda item: item.migration_id)),
            witnesses=tuple(sorted(self._witnesses.values(), key=lambda item: item.witness_id)),
            route_receipts=tuple(
                sorted(self._route_receipts.values(), key=lambda item: item.route_receipt_id)
            ),
            delayed_retrieval_replay=self.delayed_ledger.verify_replay(),
        )

    def verify_replay(self) -> dict[str, Any]:
        runtime_replay = self._event_store.verify()
        delayed_replay = self.delayed_ledger.verify_replay()
        snapshot_current = self._snapshot_is_current()
        failures = [
            *(f"runtime:{item}" for item in runtime_replay["failures"]),
            *(f"delayed:{item}" for item in delayed_replay["failures"]),
        ]
        if not snapshot_current:
            failures.append("runtime:snapshot_state_mismatch")
        return {
            "valid": not failures,
            "runtime_replay": runtime_replay,
            "delayed_retrieval_replay": delayed_replay,
            "snapshot_state_current": snapshot_current,
            "failures": failures,
        }

    def persist_event(self, event_type: str, payload: dict[str, Any]) -> None:
        self._event_store.append(event_type, payload)
        self._event_store.write_snapshot(self.snapshot())

    def _initialize_or_replay(self) -> None:
        existing_events = self._event_store.events()
        if not existing_events:
            self.persist_event(
                "SRO_RETENTION_RUNTIME_INITIALIZED",
                {"project_scope": self.project_scope, "module_id": self.module_id},
            )
            return
        verification = self._event_store.verify()
        if not verification["valid"]:
            raise ValueError("sro_retention_runtime_replay_invalid:" + ";".join(verification["failures"]))
        self._replay(existing_events)
        if not self._snapshot_is_current():
            raise ValueError("sro_retention_runtime_snapshot_state_mismatch")

    def _replay(self, events: tuple[dict[str, Any], ...]) -> None:
        for event in events:
            payload = event.get("payload") or {}
            event_type = event.get("event_type")
            if event_type in {
                "LEGACY_RETENTION_MIGRATION_CANDIDATE_CREATED",
                "LEGACY_RETENTION_MIGRATION_REVALIDATED",
            }:
                migration = self._migration_from_dict(payload["migration"])
                self._migrations[migration.migration_id] = migration
            elif event_type == "SRO_WITNESS_REGISTERED":
                self._replay_witness(payload)
            elif event_type == "SRO_RETENTION_ROUTE_DECIDED":
                route = self._route_from_dict(payload["route_receipt"])
                self._route_receipts[route.route_receipt_id] = route
            elif event_type not in {
                "SRO_RETENTION_RUNTIME_INITIALIZED",
                "SRO_PROVIDER_ROUTE_BLOCKED",
                "SRO_DELAYED_PREDICTION_SEALED",
                "SRO_DELAYED_OUTCOME_SCORED",
            }:
                raise ValueError(f"unknown_sro_runtime_event_type:{event_type}")

    def _replay_witness(self, payload: dict[str, Any]) -> None:
        witness = self._witness_from_dict(payload["witness"])
        self._witnesses[witness.witness_id] = witness
        if payload.get("migration"):
            migration = self._migration_from_dict(payload["migration"])
            self._migrations[migration.migration_id] = migration

    def _snapshot_is_current(self) -> bool:
        if not self._event_store.snapshot_path.exists():
            return False
        record = json.loads(self._event_store.snapshot_path.read_text(encoding="utf-8"))
        return record.get("snapshot_hash") == hash_payload(self.snapshot().as_dict())

    @staticmethod
    def _witness_from_dict(payload: dict[str, Any]) -> SerialSelectionWitness:
        item = dict(payload)
        recorded_hash = item.pop("record_hash", "")
        item["evidence_refs"] = tuple(item["evidence_refs"])
        witness = SerialSelectionWitness(**item)
        if witness.as_dict()["record_hash"] != recorded_hash:
            raise ValueError("sro_witness_replay_hash_mismatch")
        return witness

    @staticmethod
    def _migration_from_dict(payload: dict[str, Any]) -> LegacyRetentionMigrationCandidate:
        item = dict(payload)
        recorded_hash = item.pop("migration_hash", "")
        item["evidence_refs"] = tuple(item["evidence_refs"])
        item["required_reconstruction_refs"] = tuple(item["required_reconstruction_refs"])
        migration = LegacyRetentionMigrationCandidate(**item)
        if migration.as_dict()["migration_hash"] != recorded_hash:
            raise ValueError("legacy_migration_replay_hash_mismatch")
        return migration

    @staticmethod
    def _route_from_dict(payload: dict[str, Any]) -> SRORetentionRouteReceipt:
        item = dict(payload)
        recorded_hash = item.pop("route_receipt_hash", "")
        item.pop("global_memory_write_authority", None)
        item.pop("production_activation", None)
        item["evidence_refs"] = tuple(item["evidence_refs"])
        route = SRORetentionRouteReceipt(**item)
        if route.as_dict()["route_receipt_hash"] != recorded_hash:
            raise ValueError("sro_route_receipt_replay_hash_mismatch")
        return route
