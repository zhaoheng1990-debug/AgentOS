"""Append-only artifact revision and pointer retention model."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any


POINTER_CANDIDATE = "candidate"
POINTER_PUBLISHED_CURRENT = "published_current"
POINTER_BASELINE = "baseline"
POINTER_SUPERSEDED_ARCHIVE = "superseded_archive"

PUBLICATION_GATE = "PublicationRetentionGate"
BASELINE_GATE = "BaselineEligibilityGate"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_payload(payload: Any) -> str:
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ArtifactIdentity:
    artifact_id: str
    artifact_kind: str
    namespace: str = "core"


@dataclass(frozen=True)
class ArtifactRevision:
    revision_id: str
    artifact_id: str
    payload: dict[str, Any]
    payload_hash: str
    parent_revision_id: str = ""
    created_at: str = ""


@dataclass(frozen=True)
class ArtifactRelation:
    relation_type: str
    source_revision_id: str
    target_revision_id: str


@dataclass(frozen=True)
class ArtifactPointer:
    pointer_class: str
    artifact_id: str
    revision_id: str


@dataclass(frozen=True)
class PublicationDecision:
    decision: str
    gate_id: str
    artifact_id: str
    revision_id: str
    reason: str


@dataclass(frozen=True)
class RetentionDecision:
    decision: str
    artifact_id: str
    previous_revision_id: str
    restored_revision_id: str
    receipt_id: str


class ArtifactVersionStore:
    """In-memory append-only revision store with replayable pointer ledger."""

    def __init__(self) -> None:
        self.identities: dict[str, ArtifactIdentity] = {}
        self.revisions: dict[str, ArtifactRevision] = {}
        self.relations: list[ArtifactRelation] = []
        self.pointers: dict[tuple[str, str], ArtifactPointer] = {}
        self.ledger: list[dict[str, Any]] = []

    def register_identity(self, identity: ArtifactIdentity) -> None:
        self.identities[identity.artifact_id] = identity
        self._append("register_identity", {"artifact_id": identity.artifact_id, "artifact_kind": identity.artifact_kind})

    def create_candidate_revision(
        self,
        artifact_id: str,
        payload: dict[str, Any],
        *,
        parent_revision_id: str = "",
    ) -> ArtifactRevision:
        if artifact_id not in self.identities:
            self.register_identity(ArtifactIdentity(artifact_id, "generic_artifact"))
        revision = ArtifactRevision(
            revision_id=f"rev-{_hash_payload([artifact_id, payload, parent_revision_id, len(self.revisions)])[:16]}",
            artifact_id=artifact_id,
            payload=payload,
            payload_hash=_hash_payload(payload),
            parent_revision_id=parent_revision_id,
            created_at=_utc_now(),
        )
        self.revisions[revision.revision_id] = revision
        self.pointers[(artifact_id, POINTER_CANDIDATE)] = ArtifactPointer(POINTER_CANDIDATE, artifact_id, revision.revision_id)
        if parent_revision_id:
            self.relations.append(ArtifactRelation("revises", revision.revision_id, parent_revision_id))
        self._append("create_candidate_revision", {"artifact_id": artifact_id, "revision_id": revision.revision_id})
        return revision

    def publish(self, decision: PublicationDecision) -> ArtifactPointer:
        if decision.gate_id != PUBLICATION_GATE:
            raise ValueError("published_pointer_requires_publication_retention_gate")
        if decision.decision != "PUBLISH_CURRENT":
            self._append("publication_rejected", decision.__dict__)
            return self.current_pointer(decision.artifact_id)
        pointer = ArtifactPointer(POINTER_PUBLISHED_CURRENT, decision.artifact_id, decision.revision_id)
        old = self.pointers.get((decision.artifact_id, POINTER_PUBLISHED_CURRENT))
        if old:
            self.pointers[(decision.artifact_id, POINTER_SUPERSEDED_ARCHIVE)] = ArtifactPointer(
                POINTER_SUPERSEDED_ARCHIVE,
                decision.artifact_id,
                old.revision_id,
            )
        self.pointers[(decision.artifact_id, POINTER_PUBLISHED_CURRENT)] = pointer
        self._append("move_published_pointer", decision.__dict__)
        return pointer

    def promote_baseline(self, decision: PublicationDecision) -> ArtifactPointer:
        if decision.gate_id != BASELINE_GATE:
            raise ValueError("baseline_pointer_requires_baseline_eligibility_gate")
        if decision.decision != "PROMOTE_BASELINE":
            self._append("baseline_rejected", decision.__dict__)
            return self.pointers.get((decision.artifact_id, POINTER_BASELINE), ArtifactPointer(POINTER_BASELINE, decision.artifact_id, ""))
        pointer = ArtifactPointer(POINTER_BASELINE, decision.artifact_id, decision.revision_id)
        self.pointers[(decision.artifact_id, POINTER_BASELINE)] = pointer
        self._append("move_baseline_pointer", decision.__dict__)
        return pointer

    def current_pointer(self, artifact_id: str) -> ArtifactPointer:
        return self.pointers.get((artifact_id, POINTER_PUBLISHED_CURRENT), ArtifactPointer(POINTER_PUBLISHED_CURRENT, artifact_id, ""))

    def rollback_published_pointer(self, artifact_id: str, target_revision_id: str) -> RetentionDecision:
        previous = self.current_pointer(artifact_id).revision_id
        self.pointers[(artifact_id, POINTER_PUBLISHED_CURRENT)] = ArtifactPointer(
            POINTER_PUBLISHED_CURRENT,
            artifact_id,
            target_revision_id,
        )
        receipt_id = f"rollback-{_hash_payload([artifact_id, previous, target_revision_id, len(self.ledger)])[:16]}"
        decision = RetentionDecision("ROLLBACK_POINTER", artifact_id, previous, target_revision_id, receipt_id)
        self._append("rollback_published_pointer", decision.__dict__)
        return decision

    def replay_pointers(self) -> dict[tuple[str, str], ArtifactPointer]:
        pointers: dict[tuple[str, str], ArtifactPointer] = {}
        for event in self.ledger:
            payload = event["payload"]
            if event["event_type"] == "create_candidate_revision":
                key = (payload["artifact_id"], POINTER_CANDIDATE)
                pointers[key] = ArtifactPointer(POINTER_CANDIDATE, payload["artifact_id"], payload["revision_id"])
            if event["event_type"] == "move_published_pointer":
                key = (payload["artifact_id"], POINTER_PUBLISHED_CURRENT)
                pointers[key] = ArtifactPointer(POINTER_PUBLISHED_CURRENT, payload["artifact_id"], payload["revision_id"])
            if event["event_type"] == "move_baseline_pointer":
                key = (payload["artifact_id"], POINTER_BASELINE)
                pointers[key] = ArtifactPointer(POINTER_BASELINE, payload["artifact_id"], payload["revision_id"])
            if event["event_type"] == "rollback_published_pointer":
                key = (payload["artifact_id"], POINTER_PUBLISHED_CURRENT)
                pointers[key] = ArtifactPointer(POINTER_PUBLISHED_CURRENT, payload["artifact_id"], payload["restored_revision_id"])
        return pointers

    def _append(self, event_type: str, payload: dict[str, Any]) -> None:
        entry = {
            "event_id": f"evt-{_hash_payload([event_type, payload, len(self.ledger)])[:16]}",
            "event_type": event_type,
            "payload": payload,
            "created_at": _utc_now(),
        }
        entry["event_hash"] = _hash_payload(entry)
        self.ledger.append(entry)
