from local_collective_cognition.fresh_holdout_metrics import (
    build_candidate_cost_view,
    paired_outcome_summary,
)


def test_candidate_cost_view_includes_shared_admission_only():
    baseline = {
        "run_hash": "baseline-hash",
        "task_calls": [
            {"role": "A1_SPAN_ADMISSION", "task_id": "admit"},
            {"role": "A1_STAGED_BINDING", "task_id": "bind"},
        ],
        "contract_failures": [],
    }
    candidate = {
        "run_hash": "candidate-hash",
        "runtime_version": "candidate",
        "arm_id": "candidate",
        "task_calls": [{"role": "A10_FRAME", "task_id": "frame"}],
        "contract_failures": [],
        "receipts": {},
    }
    view = build_candidate_cost_view(
        baseline_run=baseline,
        candidate_run=candidate,
    )

    assert [call["task_id"] for call in view["task_calls"]] == [
        "admit",
        "frame",
    ]
    assert view["shared_admission_task_count"] == 1
    assert view["incremental_candidate_task_count"] == 1
    assert view["source_candidate_run_hash"] == "candidate-hash"


def test_paired_summary_is_deterministic_and_counts_direction():
    baseline = _score(
        "baseline",
        {
            "A": (1, 0.9),
            "B": (0, 0.2),
            "C": (0, 0.3),
            "D": (1, 0.8),
        },
    )
    candidate = _score(
        "candidate",
        {
            "A": (1, 0.9),
            "B": (1, 0.8),
            "C": (1, 0.9),
            "D": (0, 0.4),
        },
    )

    first = paired_outcome_summary(
        baseline_score=baseline,
        candidate_score=candidate,
    )
    second = paired_outcome_summary(
        baseline_score=baseline,
        candidate_score=candidate,
    )
    assert first == second
    assert first["corrected_case_ids"] == ["B", "C"]
    assert first["harmed_case_ids"] == ["D"]
    assert first["net_label_corrections"] == 1
    assert first["effective_cbit_delta"] > 0
    assert first["label_discordance_exact_p"] == 1.0


def _score(artifact_hash, values):
    cases = [
        {
            "case_id": case_id,
            "label_correct": label_correct,
            "effective_cbit": cbit,
        }
        for case_id, (label_correct, cbit) in values.items()
    ]
    return {
        "artifact_hash": artifact_hash,
        "label_accuracy": sum(
            value["label_correct"] for value in cases
        ) / len(cases),
        "evidence_f1": 0.5,
        "rationale_token_f1": 0.5,
        "effective_cbit": sum(
            value["effective_cbit"] for value in cases
        ) / len(cases),
        "cases": cases,
    }
