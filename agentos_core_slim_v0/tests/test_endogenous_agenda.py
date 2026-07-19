import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agentos_kernel import AgendaCandidate, AgendaFeedback, EndogenousAgendaLoop, OpenProblem


def problem(problem_id="problem-1", status="OPEN"):
    return OpenProblem(
        problem_id=problem_id,
        statement="Which intervention most reduces the unresolved rival set?",
        research_object="group_cognition_trial",
        scope="project://fixture",
        evidence_refs=(f"evidence://{problem_id}",),
        rival_explanations=("single_agent_quality", "aggregation_only"),
        status=status,
    )


def candidate(candidate_id, **overrides):
    values = {
        "candidate_id": candidate_id,
        "problem_id": "problem-1",
        "proposed_question": "Run an independent adversarial replication trial.",
        "scope": "project://fixture",
        "provider_support_receipt_ref": f"provider-receipt://{candidate_id}",
        "evidence_refs": (f"evidence://{candidate_id}",),
        "expected_cbit_gain": 0.8,
        "falsifiability": 0.9,
        "tractability": 0.8,
        "urgency": 0.6,
        "novelty": 0.6,
        "negative_transfer_risk": 0.1,
        "normalized_cost": 0.3,
    }
    values.update(overrides)
    return AgendaCandidate(**values)


def test_loop_selects_highest_provider_supported_candidate_without_execution_authority():
    loop = EndogenousAgendaLoop()
    loop.register_problem(problem())
    loop.propose(candidate("candidate-low", expected_cbit_gain=0.4, normalized_cost=0.8))
    loop.propose(candidate("candidate-high", expected_cbit_gain=0.9, normalized_cost=0.2))

    selection = loop.select_next()

    assert selection.decision == "SELECT"
    assert selection.candidate_id == "candidate-high"
    assert selection.execution_authorized is False
    assert selection.provider_support_receipt_ref == "provider-receipt://candidate-high"
    assert loop.problem("problem-1").status == "ACTIVE"


def test_feedback_closes_iteration_and_adds_provider_supplied_residual_problem():
    loop = EndogenousAgendaLoop()
    loop.register_problem(problem())
    loop.propose(candidate("candidate-1"))
    loop.select_next()
    residual = problem("problem-residual")

    added = loop.record_feedback(
        AgendaFeedback(
            candidate_id="candidate-1",
            problem_resolution="PARTIAL",
            observed_cbit_gain=0.5,
            evidence_refs=("evidence://feedback",),
            provider_support_receipt_ref="provider-receipt://feedback",
            residual_problems=(residual,),
        )
    )

    assert added == ("problem-residual",)
    assert loop.problem("problem-1").status == "OPEN"
    assert loop.problem("problem-residual").status == "OPEN"


def test_resolved_feedback_removes_problem_from_future_selection():
    loop = EndogenousAgendaLoop()
    loop.register_problem(problem())
    loop.propose(candidate("candidate-1"))
    loop.select_next()
    loop.record_feedback(
        AgendaFeedback(
            candidate_id="candidate-1",
            problem_resolution="RESOLVED",
            observed_cbit_gain=0.8,
            evidence_refs=("evidence://resolved",),
            provider_support_receipt_ref="provider-receipt://resolved",
        )
    )

    assert loop.problem("problem-1").status == "RESOLVED"
    assert loop.select_next().decision == "STOP"


def test_low_value_candidates_trigger_explicit_stop():
    loop = EndogenousAgendaLoop(minimum_priority=0.4)
    loop.register_problem(problem())
    loop.propose(
        candidate(
            "candidate-low",
            expected_cbit_gain=0.1,
            falsifiability=0.1,
            tractability=0.1,
            urgency=0.1,
            novelty=0.1,
            negative_transfer_risk=0.9,
            normalized_cost=0.9,
        )
    )

    assert loop.select_next().decision == "STOP"


def test_candidate_without_provider_support_receipt_is_rejected():
    with pytest.raises(ValueError, match="agenda_candidate_provider_backed_identity_required"):
        candidate("candidate-unbacked", provider_support_receipt_ref="")


def test_kernel_can_apply_provider_backed_group_selection_without_execution_authority():
    loop = EndogenousAgendaLoop()
    loop.register_problem(problem())
    loop.propose(candidate("candidate-provider-selected"))

    selection = loop.select_candidate(
        "candidate-provider-selected",
        "provider-receipt://group-agenda-selection",
    )

    assert selection.decision == "SELECT"
    assert selection.candidate_id == "candidate-provider-selected"
    assert selection.provider_support_receipt_ref == "provider-receipt://group-agenda-selection"
    assert selection.execution_authorized is False
    assert loop.problem("problem-1").status == "ACTIVE"
