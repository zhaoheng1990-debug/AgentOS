"""Append-only epistemic credit ledger for agents, providers, and operators."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol


CREDIT_LEDGER_VERSION = "epistemic_credit_ledger_v0_1"

SUBJECT_KINDS = {"agent", "provider", "operator"}
OUTCOME_POLARITY = {
    "CLAIM_SURVIVED_REPLICATION": 1,
    "CLAIM_FALSIFIED": -1,
    "OBJECTION_SUSTAINED": 1,
    "OBJECTION_REJECTED": -1,
    "NEGATIVE_TRANSFER_INTERCEPTED": 1,
    "NEGATIVE_TRANSFER_CAUSED": -1,
    "RECEIPT_VALIDATED": 1,
    "RECEIPT_INVALIDATED": -1,
}


def _hash_payload(payload: Any) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(data).hexdigest()


@dataclass(frozen=True)
class CreditEvent:
    event_id: str
    subject_id: str
    subject_kind: str
    outcome: str
    adjudication_ref: str
    evidence_refs: tuple[str, ...]
    weight: float = 1.0
    source_claim_id: str = ""

    def __post_init__(self) -> None:
        if not self.event_id or not self.subject_id or not self.adjudication_ref:
            raise ValueError("credit_event_identity_and_adjudication_required")
        if self.subject_kind not in SUBJECT_KINDS:
            raise ValueError(f"unknown_credit_subject_kind:{self.subject_kind}")
        if self.outcome not in OUTCOME_POLARITY:
            raise ValueError(f"unknown_credit_outcome:{self.outcome}")
        if not self.evidence_refs:
            raise ValueError("credit_event_evidence_refs_required")
        if not 0.0 < self.weight <= 1.0:
            raise ValueError("credit_event_weight_outside_bounded_interval")

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "subject_id": self.subject_id,
            "subject_kind": self.subject_kind,
            "outcome": self.outcome,
            "adjudication_ref": self.adjudication_ref,
            "evidence_refs": list(self.evidence_refs),
            "weight": self.weight,
            "source_claim_id": self.source_claim_id,
            "polarity": OUTCOME_POLARITY[self.outcome],
        }


@dataclass(frozen=True)
class CreditProfile:
    subject_id: str
    subject_kind: str
    event_count: int
    positive_weight: float
    negative_weight: float
    trust_score: float
    confidence: float
    advisory_only: bool = True
    selection_authority: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "subject_kind": self.subject_kind,
            "event_count": self.event_count,
            "positive_weight": self.positive_weight,
            "negative_weight": self.negative_weight,
            "trust_score": self.trust_score,
            "confidence": self.confidence,
            "advisory_only": self.advisory_only,
            "selection_authority": self.selection_authority,
        }


class CreditEventStore(Protocol):
    def append(self, payload: dict[str, Any]) -> None:
        """Persist one validated event before it enters the live projection."""

    def load(self) -> tuple[dict[str, Any], ...]:
        """Load and verify all previously persisted events."""


class JsonlCreditEventStore:
    """Append-only durable adapter with per-event integrity hashes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: dict[str, Any]) -> None:
        record = dict(payload)
        record["event_hash"] = _hash_payload(record)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def load(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(self.path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            expected_hash = record.pop("event_hash", "")
            if not expected_hash or _hash_payload(record) != expected_hash:
                raise ValueError(f"credit_event_store_hash_mismatch:{line_number}")
            records.append(record)
        return tuple(records)


class CreditLedger:
    """P2 evidence-backed track record with no route-selection authority."""

    module_id = CREDIT_LEDGER_VERSION
    capabilities = ("epistemic_credit_recording", "credit_profile_projection")

    def __init__(self, store: CreditEventStore | None = None) -> None:
        self._store = store
        self._events: list[CreditEvent] = []
        self._event_ids: set[str] = set()
        self._subject_kinds: dict[str, str] = {}
        if self._store is not None:
            for payload in self._store.load():
                self._commit(self._from_payload(payload))

    def append(self, event: CreditEvent) -> dict[str, Any]:
        self._validate_append(event)
        payload = event.as_dict()
        if self._store is not None:
            self._store.append(payload)
        self._commit(event)
        return payload

    def _validate_append(self, event: CreditEvent) -> None:
        if event.event_id in self._event_ids:
            raise ValueError(f"duplicate_credit_event_id:{event.event_id}")
        known_kind = self._subject_kinds.get(event.subject_id)
        if known_kind is not None and known_kind != event.subject_kind:
            raise ValueError("credit_subject_kind_changed_across_events")

    def _commit(self, event: CreditEvent) -> None:
        self._validate_append(event)
        self._events.append(event)
        self._event_ids.add(event.event_id)
        self._subject_kinds[event.subject_id] = event.subject_kind

    @staticmethod
    def _from_payload(payload: dict[str, Any]) -> CreditEvent:
        return CreditEvent(
            event_id=payload["event_id"],
            subject_id=payload["subject_id"],
            subject_kind=payload["subject_kind"],
            outcome=payload["outcome"],
            adjudication_ref=payload["adjudication_ref"],
            evidence_refs=tuple(payload["evidence_refs"]),
            weight=payload.get("weight", 1.0),
            source_claim_id=payload.get("source_claim_id", ""),
        )

    def events_for(self, subject_id: str) -> tuple[CreditEvent, ...]:
        return tuple(event for event in self._events if event.subject_id == subject_id)

    def profile(self, subject_id: str) -> CreditProfile:
        events = self.events_for(subject_id)
        if not events:
            return CreditProfile(
                subject_id=subject_id,
                subject_kind="unknown",
                event_count=0,
                positive_weight=0.0,
                negative_weight=0.0,
                trust_score=0.5,
                confidence=0.0,
            )
        positive = sum(event.weight for event in events if OUTCOME_POLARITY[event.outcome] > 0)
        negative = sum(event.weight for event in events if OUTCOME_POLARITY[event.outcome] < 0)
        total = positive + negative
        return CreditProfile(
            subject_id=subject_id,
            subject_kind=events[0].subject_kind,
            event_count=len(events),
            positive_weight=round(positive, 12),
            negative_weight=round(negative, 12),
            trust_score=round(positive / total, 12) if total else 0.5,
            confidence=round(total / (total + 1.0), 12),
        )

    def snapshot(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.as_dict() for event in self._events)
