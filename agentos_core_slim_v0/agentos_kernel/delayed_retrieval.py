"""Pure delayed-retrieval state machine with an injected event-store port."""

from __future__ import annotations

from typing import Any, Protocol

from .sro_retention_models import (
    SRO_ROUTES,
    DelayedRetrievalPrediction,
    DelayedRetrievalScore,
    hash_payload,
    parse_timestamp,
    require_sha256,
    require_text,
    unit_interval,
)


class DelayedRetrievalEventStore(Protocol):
    def load_events(self) -> list[dict[str, Any]]: ...

    def append_event(self, event: dict[str, Any]) -> None: ...

    def current_head(self) -> str: ...


class DelayedRetrievalLedger:
    """Prediction/reveal ledger; persistence is supplied by an adapter."""

    def __init__(self, event_store: DelayedRetrievalEventStore | None = None) -> None:
        self._predictions: dict[str, DelayedRetrievalPrediction] = {}
        self._scores: dict[str, DelayedRetrievalScore] = {}
        self._events: list[dict[str, Any]] = []
        self.event_store = event_store
        if self.event_store is not None:
            self._load(self.event_store.load_events())

    def register_prediction(self, prediction: DelayedRetrievalPrediction) -> dict[str, Any]:
        if prediction.prediction_id in self._predictions:
            raise ValueError(f"duplicate_delayed_retrieval_prediction:{prediction.prediction_id}")
        self._predictions[prediction.prediction_id] = prediction
        return self._append("PREDICTION_SEALED", prediction.as_dict())

    def score_outcome(
        self,
        prediction_id: str,
        *,
        observed_route: str,
        role_reconstruction_fidelity: float,
        negative_transfer_penalty: float,
        outcome_ref: str,
        outcome_hash: str,
        revealed_at: str,
        scoring_authority_ref: str,
    ) -> DelayedRetrievalScore:
        if prediction_id not in self._predictions:
            raise ValueError(f"unknown_delayed_retrieval_prediction:{prediction_id}")
        if prediction_id in self._scores:
            raise ValueError(f"duplicate_delayed_retrieval_outcome:{prediction_id}")
        if observed_route not in SRO_ROUTES:
            raise ValueError(f"unknown_observed_route:{observed_route}")
        fidelity = unit_interval(role_reconstruction_fidelity)
        penalty = unit_interval(negative_transfer_penalty)
        if fidelity is None:
            raise ValueError("role_reconstruction_fidelity_must_be_in_unit_interval")
        if penalty is None:
            raise ValueError("negative_transfer_penalty_must_be_in_unit_interval")
        require_text("outcome_ref", outcome_ref)
        outcome_hash = require_sha256("outcome_hash", outcome_hash)
        scoring_authority_ref = require_text("scoring_authority_ref", scoring_authority_ref)
        reveal_time = parse_timestamp("revealed_at", revealed_at)
        prediction = self._predictions[prediction_id]
        if reveal_time <= parse_timestamp("sealed_at", prediction.sealed_at):
            raise ValueError("delayed_retrieval_outcome_must_follow_prediction_seal")
        score = DelayedRetrievalScore(
            prediction_id=prediction_id,
            predicted_route=prediction.predicted_route,
            observed_route=observed_route,
            route_supported=prediction.predicted_route == observed_route,
            role_reconstruction_fidelity=float(fidelity),
            negative_transfer_penalty=float(penalty),
            delayed_retrieval_score=float(fidelity - penalty),
            outcome_ref=outcome_ref,
            outcome_hash=outcome_hash,
            revealed_at=revealed_at,
            scoring_authority_ref=scoring_authority_ref,
        )
        self._scores[prediction_id] = score
        self._append("OUTCOME_REVEALED_AND_SCORED", score.as_dict())
        return score

    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(dict(event) for event in self._events)

    def verify_replay(self) -> dict[str, Any]:
        failures = self.event_failures(self._events)
        return {
            "valid": not failures,
            "event_count": len(self._events),
            "prediction_count": len(self._predictions),
            "score_count": len(self._scores),
            "head_event_hash": self._events[-1]["event_hash"] if self._events else "",
            "failures": failures,
        }

    def prediction(self, prediction_id: str) -> DelayedRetrievalPrediction | None:
        return self._predictions.get(prediction_id)

    def score(self, prediction_id: str) -> DelayedRetrievalScore | None:
        return self._scores.get(prediction_id)

    def _append(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._assert_store_head()
        event = {
            "sequence": len(self._events) + 1,
            "event_type": event_type,
            "previous_event_hash": self._events[-1]["event_hash"] if self._events else "",
            "payload": payload,
        }
        event["event_hash"] = hash_payload(event)
        if self.event_store is not None:
            self.event_store.append_event(event)
        self._events.append(event)
        return dict(event)

    def _load(self, events: list[dict[str, Any]]) -> None:
        failures = self.event_failures(events)
        if failures:
            raise ValueError("delayed_retrieval_ledger_replay_invalid:" + ";".join(failures))
        for event in events:
            self._apply_event(event)
        self._events = events

    def _apply_event(self, event: dict[str, Any]) -> None:
        payload = dict(event["payload"])
        if event["event_type"] == "PREDICTION_SEALED":
            recorded_hash = payload.pop("prediction_hash", "")
            prediction = DelayedRetrievalPrediction(**payload)
            if prediction.as_dict()["prediction_hash"] != recorded_hash:
                raise ValueError("delayed_retrieval_prediction_hash_mismatch")
            if prediction.prediction_id in self._predictions:
                raise ValueError("delayed_retrieval_prediction_replay_duplicate")
            self._predictions[prediction.prediction_id] = prediction
            return
        if event["event_type"] == "OUTCOME_REVEALED_AND_SCORED":
            recorded_hash = payload.pop("score_hash", "")
            score = DelayedRetrievalScore(**payload)
            if score.as_dict()["score_hash"] != recorded_hash:
                raise ValueError("delayed_retrieval_score_hash_mismatch")
            if score.prediction_id not in self._predictions or score.prediction_id in self._scores:
                raise ValueError("delayed_retrieval_score_replay_order_invalid")
            self._scores[score.prediction_id] = score
            return
        raise ValueError(f"unknown_delayed_retrieval_event_type:{event.get('event_type')}")

    @staticmethod
    def event_failures(events: list[dict[str, Any]]) -> list[str]:
        failures = []
        previous_hash = ""
        for index, event in enumerate(events, start=1):
            committed = dict(event)
            recorded_hash = committed.pop("event_hash", "")
            if event.get("sequence") != index:
                failures.append(f"sequence_mismatch:{index}")
            if event.get("previous_event_hash") != previous_hash:
                failures.append(f"event_chain_mismatch:{index}")
            if hash_payload(committed) != recorded_hash:
                failures.append(f"event_hash_mismatch:{index}")
            previous_hash = recorded_hash
        return failures

    def _assert_store_head(self) -> None:
        if self.event_store is None:
            return
        memory_head = self._events[-1]["event_hash"] if self._events else ""
        if self.event_store.current_head() != memory_head:
            raise RuntimeError("delayed_retrieval_ledger_concurrent_modification")
