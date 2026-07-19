"""Provider-supported, Runtime-owned endogenous research agenda loop."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


ENDOGENOUS_AGENDA_VERSION = "endogenous_agenda_loop_v0_2"

PROBLEM_STATUSES = {"OPEN", "ACTIVE", "RESOLVED", "INVALIDATED"}
FEEDBACK_STATUSES = {"RESOLVED", "PARTIAL", "UNRESOLVED", "INVALIDATED"}


def _validate_unit_interval(name: str, value: float) -> None:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise ValueError(f"{name}_outside_unit_interval")


@dataclass(frozen=True)
class OpenProblem:
    problem_id: str
    statement: str
    research_object: str
    scope: str
    evidence_refs: tuple[str, ...]
    rival_explanations: tuple[str, ...] = ()
    status: str = "OPEN"

    def __post_init__(self) -> None:
        if not all((self.problem_id, self.statement, self.research_object, self.scope)):
            raise ValueError("open_problem_identity_required")
        if not self.evidence_refs:
            raise ValueError("open_problem_evidence_refs_required")
        if self.status not in PROBLEM_STATUSES:
            raise ValueError(f"unknown_problem_status:{self.status}")


@dataclass(frozen=True)
class AgendaCandidate:
    candidate_id: str
    problem_id: str
    proposed_question: str
    scope: str
    provider_support_receipt_ref: str
    evidence_refs: tuple[str, ...]
    expected_cbit_gain: float
    falsifiability: float
    tractability: float
    urgency: float
    novelty: float
    negative_transfer_risk: float
    normalized_cost: float

    def __post_init__(self) -> None:
        if not all(
            (
                self.candidate_id,
                self.problem_id,
                self.proposed_question,
                self.scope,
                self.provider_support_receipt_ref,
            )
        ):
            raise ValueError("agenda_candidate_provider_backed_identity_required")
        if not self.evidence_refs:
            raise ValueError("agenda_candidate_evidence_refs_required")
        for name in (
            "expected_cbit_gain",
            "falsifiability",
            "tractability",
            "urgency",
            "novelty",
            "negative_transfer_risk",
            "normalized_cost",
        ):
            _validate_unit_interval(name, getattr(self, name))


@dataclass(frozen=True)
class AgendaSelection:
    decision: str
    candidate_id: str
    problem_id: str
    priority_score: float
    reason: str
    provider_support_receipt_ref: str
    execution_authorized: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "candidate_id": self.candidate_id,
            "problem_id": self.problem_id,
            "priority_score": self.priority_score,
            "reason": self.reason,
            "provider_support_receipt_ref": self.provider_support_receipt_ref,
            "execution_authorized": self.execution_authorized,
        }


@dataclass(frozen=True)
class AgendaFeedback:
    candidate_id: str
    problem_resolution: str
    observed_cbit_gain: float | None
    evidence_refs: tuple[str, ...]
    provider_support_receipt_ref: str
    residual_problems: tuple[OpenProblem, ...] = ()

    def __post_init__(self) -> None:
        if self.problem_resolution not in FEEDBACK_STATUSES:
            raise ValueError(f"unknown_problem_resolution:{self.problem_resolution}")
        if self.observed_cbit_gain is not None:
            _validate_unit_interval("observed_cbit_gain", self.observed_cbit_gain)
        if not self.candidate_id or not self.provider_support_receipt_ref:
            raise ValueError("agenda_feedback_provider_backed_identity_required")
        if not self.evidence_refs:
            raise ValueError("agenda_feedback_evidence_refs_required")


class EndogenousAgendaLoop:
    """P4 problem-space loop; semantic estimates enter via support receipts."""

    module_id = ENDOGENOUS_AGENDA_VERSION
    capabilities = ("problem_space_tracking", "agenda_selection", "agenda_feedback")

    def __init__(self, *, minimum_priority: float = 0.2) -> None:
        self.minimum_priority = minimum_priority
        self._problems: dict[str, OpenProblem] = {}
        self._candidates: dict[str, AgendaCandidate] = {}
        self._candidate_states: dict[str, str] = {}
        self._feedback: list[AgendaFeedback] = []

    def register_problem(self, problem: OpenProblem) -> None:
        if problem.problem_id in self._problems:
            raise ValueError(f"duplicate_problem_id:{problem.problem_id}")
        self._problems[problem.problem_id] = problem

    def propose(self, candidate: AgendaCandidate) -> None:
        if candidate.candidate_id in self._candidates:
            raise ValueError(f"duplicate_agenda_candidate_id:{candidate.candidate_id}")
        problem = self._problems.get(candidate.problem_id)
        if problem is None:
            raise KeyError(f"agenda_problem_not_registered:{candidate.problem_id}")
        if problem.status == "RESOLVED":
            raise ValueError("cannot_propose_for_resolved_problem")
        if candidate.scope != problem.scope:
            raise ValueError("agenda_candidate_scope_mismatch")
        self._candidates[candidate.candidate_id] = candidate
        self._candidate_states[candidate.candidate_id] = "CANDIDATE"

    def rank_candidates(self) -> tuple[tuple[str, float], ...]:
        ranked = [
            (candidate.candidate_id, self._priority(candidate))
            for candidate in self._candidates.values()
            if self._candidate_states[candidate.candidate_id] == "CANDIDATE"
            and self._problems[candidate.problem_id].status != "RESOLVED"
        ]
        return tuple(sorted(ranked, key=lambda item: (-item[1], item[0])))

    def select_next(self) -> AgendaSelection:
        ranked = self.rank_candidates()
        if not ranked or ranked[0][1] < self.minimum_priority:
            return AgendaSelection(
                decision="STOP",
                candidate_id="",
                problem_id="",
                priority_score=ranked[0][1] if ranked else 0.0,
                reason="no_candidate_meets_runtime_priority_gate",
                provider_support_receipt_ref="",
            )
        candidate_id, priority = ranked[0]
        return self._activate_candidate(
            candidate_id,
            priority,
            self._candidates[candidate_id].provider_support_receipt_ref,
            "highest_provider_supported_candidate_passed_runtime_priority_gate",
        )

    def select_candidate(
        self,
        candidate_id: str,
        selection_support_receipt_ref: str,
    ) -> AgendaSelection:
        """Apply a provider-backed group selection after deterministic eligibility gates."""

        if not candidate_id or not selection_support_receipt_ref:
            raise ValueError("provider_backed_agenda_selection_identity_required")
        candidate = self._candidates.get(candidate_id)
        if candidate is None:
            raise KeyError(f"agenda_candidate_not_registered:{candidate_id}")
        if self._candidate_states[candidate_id] != "CANDIDATE":
            raise ValueError("agenda_selection_requires_candidate_state")
        if self._problems[candidate.problem_id].status == "RESOLVED":
            raise ValueError("cannot_select_candidate_for_resolved_problem")
        priority = self._priority(candidate)
        if priority < self.minimum_priority:
            raise ValueError("provider_selected_candidate_below_runtime_priority_gate")
        return self._activate_candidate(
            candidate_id,
            priority,
            selection_support_receipt_ref,
            "provider_backed_group_selection_passed_runtime_priority_gate",
        )

    def _activate_candidate(
        self,
        candidate_id: str,
        priority: float,
        provider_support_receipt_ref: str,
        reason: str,
    ) -> AgendaSelection:
        candidate = self._candidates[candidate_id]
        problem = self._problems[candidate.problem_id]
        self._candidate_states[candidate_id] = "SELECTED"
        self._problems[problem.problem_id] = OpenProblem(
            problem_id=problem.problem_id,
            statement=problem.statement,
            research_object=problem.research_object,
            scope=problem.scope,
            evidence_refs=problem.evidence_refs,
            rival_explanations=problem.rival_explanations,
            status="ACTIVE",
        )
        return AgendaSelection(
            decision="SELECT",
            candidate_id=candidate_id,
            problem_id=candidate.problem_id,
            priority_score=priority,
            reason=reason,
            provider_support_receipt_ref=provider_support_receipt_ref,
        )

    def record_feedback(self, feedback: AgendaFeedback) -> tuple[str, ...]:
        candidate = self._candidates.get(feedback.candidate_id)
        if candidate is None:
            raise KeyError(f"agenda_candidate_not_registered:{feedback.candidate_id}")
        if self._candidate_states[candidate.candidate_id] != "SELECTED":
            raise ValueError("agenda_feedback_requires_selected_candidate")

        problem = self._problems[candidate.problem_id]
        if feedback.problem_resolution == "RESOLVED":
            next_status = "RESOLVED"
        elif feedback.problem_resolution == "INVALIDATED":
            next_status = "INVALIDATED"
        else:
            next_status = "OPEN"
        self._problems[problem.problem_id] = OpenProblem(
            problem_id=problem.problem_id,
            statement=problem.statement,
            research_object=problem.research_object,
            scope=problem.scope,
            evidence_refs=tuple(dict.fromkeys((*problem.evidence_refs, *feedback.evidence_refs))),
            rival_explanations=problem.rival_explanations,
            status=next_status,
        )
        self._candidate_states[candidate.candidate_id] = "COMPLETED"
        self._feedback.append(feedback)

        added: list[str] = []
        for residual in feedback.residual_problems:
            self.register_problem(residual)
            added.append(residual.problem_id)
        return tuple(added)

    def problem(self, problem_id: str) -> OpenProblem:
        try:
            return self._problems[problem_id]
        except KeyError as exc:
            raise KeyError(f"agenda_problem_not_registered:{problem_id}") from exc

    @staticmethod
    def _priority(candidate: AgendaCandidate) -> float:
        score = (
            0.35 * candidate.expected_cbit_gain
            + 0.20 * candidate.falsifiability
            + 0.15 * candidate.tractability
            + 0.15 * candidate.urgency
            + 0.15 * candidate.novelty
            - 0.25 * candidate.negative_transfer_risk
            - 0.15 * candidate.normalized_cost
        )
        return round(score, 12)
