"""Portfolio-aware shadow retention policy for selection-first evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .selection_retention_models import (
    ApplicabilityDelta,
    ConsequenceBinding,
    ProspectiveSelectionEvent,
    SemanticOperatorRoute,
    ValidityAssessment,
    ValueDelta,
    hash_selection_payload,
)


@dataclass(frozen=True)
class SelectionRetentionDecision:
    decision: str
    candidate_state: str
    retention_candidate_eligible: bool
    hard_gate_failures: tuple[str, ...]
    aggregate_applicability_delta: float | None
    aggregate_cbit_gain: float | None
    aggregate_cost: float | None
    reason: str
    source_selection_hash: str

    def as_dict(self) -> dict[str, Any]:
        payload = {
            "decision": self.decision,
            "candidate_state": self.candidate_state,
            "retention_candidate_eligible": (
                self.retention_candidate_eligible
            ),
            "hard_gate_failures": list(self.hard_gate_failures),
            "aggregate_applicability_delta": (
                self.aggregate_applicability_delta
            ),
            "aggregate_cbit_gain": self.aggregate_cbit_gain,
            "aggregate_cost": self.aggregate_cost,
            "reason": self.reason,
            "source_selection_hash": self.source_selection_hash,
            "portfolio_aware": True,
            "scalar_legacy_score_authority": False,
            "global_memory_write_authority": False,
            "production_authority": False,
        }
        return {**payload, "decision_hash": hash_selection_payload(payload)}


class PortfolioSelectionRetentionGate:
    """Keep applicability, value, and validity non-compensable."""

    def evaluate(
        self,
        *,
        selection: ProspectiveSelectionEvent,
        consequences: tuple[ConsequenceBinding, ...],
        applicability_deltas: tuple[ApplicabilityDelta, ...],
        value_deltas: tuple[ValueDelta, ...],
        validity: ValidityAssessment | None,
        semantic_route: SemanticOperatorRoute | None,
    ) -> SelectionRetentionDecision:
        selection_hash = selection.preconsequence_hash
        failures: list[str] = []
        for item in consequences:
            if (
                item.project_scope != selection.project_scope
                or item.selection_event_hash != selection_hash
            ):
                failures.append("CONSEQUENCE_SELECTION_BINDING_INVALID")
        consequence_hashes = {item.binding_hash for item in consequences}
        for item in (*applicability_deltas, *value_deltas):
            if (
                item.selection_event_hash != selection_hash
                or item.consequence_binding_hash not in consequence_hashes
            ):
                failures.append("DELTA_CONSEQUENCE_BINDING_INVALID")
        if validity is not None and (
            validity.selection_event_hash != selection_hash
            or validity.boundary_ref != selection.validity_boundary_ref
        ):
            failures.append("VALIDITY_SELECTION_BINDING_INVALID")
        if semantic_route is not None and (
            semantic_route.selection_event_hash != selection_hash
            or semantic_route.project_scope != selection.project_scope
            or semantic_route.selected_ref != selection.selected_ref
            or set(semantic_route.ranked_alternative_refs)
            != set(selection.alternatives)
        ):
            failures.append("SEMANTIC_ROUTE_SELECTION_BINDING_INVALID")
        if validity and validity.validity_state in {"DRIFTED", "STALE"}:
            failures.append("VALIDITY_HARD_STOP")
        applicability = (
            sum(item.applicability_delta for item in applicability_deltas)
            if applicability_deltas
            else None
        )
        cbit = (
            sum(item.observed_cbit_gain for item in value_deltas)
            if value_deltas
            else None
        )
        cost = (
            sum(item.observed_cost for item in value_deltas)
            if value_deltas
            else None
        )
        if failures:
            return self._decision(
                "QUARANTINE",
                "QUARANTINED_SELECTION_EVIDENCE",
                False,
                failures,
                applicability,
                cbit,
                cost,
                "A non-compensable binding or validity gate failed.",
                selection_hash,
            )
        if (
            not consequences
            or not applicability_deltas
            or not value_deltas
            or validity is None
            or semantic_route is None
        ):
            return self._decision(
                "OBSERVE",
                "PENDING_SELECTION_EVIDENCE",
                False,
                (),
                applicability,
                cbit,
                cost,
                "The selection portfolio is incomplete.",
                selection_hash,
            )
        eligible = (
            validity.validity_state == "CURRENT"
            and applicability is not None
            and applicability >= 0
            and cbit is not None
            and cbit > 0
            and semantic_route.expected_cbit_gain > 0
        )
        return self._decision(
            "CANDIDATE_RETAIN" if eligible else "OBSERVE",
            (
                "PENDING_RETENTION_REVIEW"
                if eligible
                else "PENDING_SELECTION_EVIDENCE"
            ),
            eligible,
            (),
            applicability,
            cbit,
            cost,
            (
                "All separate selection-evidence dimensions support review."
                if eligible
                else "The portfolio does not support retention candidacy."
            ),
            selection_hash,
        )

    @staticmethod
    def _decision(
        decision,
        state,
        eligible,
        failures,
        applicability,
        cbit,
        cost,
        reason,
        selection_hash,
    ) -> SelectionRetentionDecision:
        return SelectionRetentionDecision(
            decision=decision,
            candidate_state=state,
            retention_candidate_eligible=eligible,
            hard_gate_failures=tuple(sorted(set(failures))),
            aggregate_applicability_delta=applicability,
            aggregate_cbit_gain=cbit,
            aggregate_cost=cost,
            reason=reason,
            source_selection_hash=selection_hash,
        )
