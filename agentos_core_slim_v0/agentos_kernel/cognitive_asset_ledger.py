"""Generic cognitive asset ledger and read-only projection contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Protocol


ASSET_STATUSES = {"candidate", "published", "baseline", "archived", "invalidated", "quarantined", "revoked"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CognitiveAssetEntry:
    asset_id: str
    revision_id: str
    asset_type: str
    status: str
    source_refs: tuple[str, ...]
    visibility_boundary: str
    freshness: str = "unknown"
    expiry: str = ""
    drift_state: str = "unknown"
    supersedes: str = ""
    created_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "revision_id": self.revision_id,
            "asset_type": self.asset_type,
            "status": self.status,
            "source_refs": list(self.source_refs),
            "visibility_boundary": self.visibility_boundary,
            "freshness": self.freshness,
            "expiry": self.expiry,
            "drift_state": self.drift_state,
            "supersedes": self.supersedes,
            "created_at": self.created_at,
        }


class CognitiveAssetLedger:
    """Append-only status and provenance ledger."""

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def append(self, entry: CognitiveAssetEntry) -> dict[str, Any]:
        if entry.status not in ASSET_STATUSES:
            raise ValueError(f"unknown_asset_status:{entry.status}")
        payload = entry.as_dict()
        if not payload["created_at"]:
            payload["created_at"] = _utc_now()
        payload["entry_hash"] = _hash_payload(payload)
        self.entries.append(payload)
        return payload

    def latest(self, asset_id: str) -> dict[str, Any] | None:
        for entry in reversed(self.entries):
            if entry["asset_id"] == asset_id:
                return dict(entry)
        return None

    def project(self, projection: "ArtifactProjection") -> dict[str, Any]:
        before = _hash_payload(self.entries)
        rendered = projection.render(tuple(dict(item) for item in self.entries))
        after = _hash_payload(self.entries)
        if before != after:
            raise RuntimeError("projection_mutated_ledger")
        rendered["projection_mutation_authority"] = False
        rendered["baseline_write_authority"] = False
        return rendered


class ArtifactProjection(Protocol):
    projection_id: str

    def render(self, entries: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        """Render ledger-backed content without mutation authority."""
