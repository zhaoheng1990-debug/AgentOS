import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import CreditEvent, CreditLedger, JsonlCreditEventStore


def event(event_id, subject_id, outcome, *, subject_kind="agent", weight=1.0):
    return CreditEvent(
        event_id=event_id,
        subject_id=subject_id,
        subject_kind=subject_kind,
        outcome=outcome,
        adjudication_ref=f"decision://{event_id}",
        evidence_refs=(f"evidence://{event_id}",),
        weight=weight,
        source_claim_id="claim-1",
    )


def test_credit_profile_accumulates_adjudicated_positive_and_negative_history():
    ledger = CreditLedger()
    ledger.append(event("event-1", "agent-a", "CLAIM_SURVIVED_REPLICATION"))
    ledger.append(event("event-2", "agent-a", "CLAIM_FALSIFIED", weight=0.5))

    profile = ledger.profile("agent-a")

    assert profile.event_count == 2
    assert profile.positive_weight == 1.0
    assert profile.negative_weight == 0.5
    assert profile.trust_score == pytest.approx(2 / 3)
    assert profile.advisory_only is True
    assert profile.selection_authority is False


def test_unseen_subject_has_neutral_low_confidence_prior():
    profile = CreditLedger().profile("new-provider")

    assert profile.subject_kind == "unknown"
    assert profile.trust_score == 0.5
    assert profile.confidence == 0.0


def test_duplicate_event_is_rejected_to_preserve_append_only_identity():
    ledger = CreditLedger()
    ledger.append(event("event-1", "agent-a", "RECEIPT_VALIDATED"))

    with pytest.raises(ValueError, match="duplicate_credit_event_id"):
        ledger.append(event("event-1", "agent-a", "RECEIPT_VALIDATED"))


def test_raw_unadjudicated_or_unsupported_outcome_cannot_enter_credit_ledger():
    with pytest.raises(ValueError, match="credit_event_identity_and_adjudication_required"):
        CreditEvent(
            event_id="event-raw",
            subject_id="provider-a",
            subject_kind="provider",
            outcome="RECEIPT_VALIDATED",
            adjudication_ref="",
            evidence_refs=("provider-receipt://raw",),
        )

    with pytest.raises(ValueError, match="unknown_credit_outcome"):
        event("event-praise", "agent-a", "USER_PRAISE")


def test_subject_histories_remain_separate():
    ledger = CreditLedger()
    ledger.append(event("event-a", "agent-a", "CLAIM_SURVIVED_REPLICATION"))
    ledger.append(event("event-b", "provider-b", "RECEIPT_INVALIDATED", subject_kind="provider"))

    assert ledger.profile("agent-a").trust_score == 1.0
    assert ledger.profile("provider-b").trust_score == 0.0


def test_jsonl_store_restores_credit_history_across_runtime_restart(tmp_path):
    store_path = tmp_path / "credit" / "events.jsonl"
    ledger = CreditLedger(JsonlCreditEventStore(store_path))
    ledger.append(event("event-persisted", "agent-a", "CLAIM_SURVIVED_REPLICATION"))

    restarted = CreditLedger(JsonlCreditEventStore(store_path))

    assert restarted.profile("agent-a").event_count == 1
    assert restarted.profile("agent-a").trust_score == 1.0
    assert restarted.snapshot()[0]["event_id"] == "event-persisted"
