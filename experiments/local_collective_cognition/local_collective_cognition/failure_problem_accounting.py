"""Preserve problem-formulation artifacts from failed case stages."""

from __future__ import annotations


def failed_problem_artifacts(runs):
    pairs = (
        ("failed_problem_definition_receipts", ("problem_definition_receipt", "problem_receipt")),
        ("failed_problem_coordination_receipts", ("problem_coordination_receipt",
                                                    "coordination_receipt")),
        ("failed_problem_admission_receipts", ("problem_admission_receipt",)),
        ("failed_problem_plan_binding_receipts", ("problem_plan_binding_receipt",)),
        ("failed_problem_proposal_receipts", ("problem_proposal_receipt",)),
        ("failed_problem_critique_receipts", ("problem_critique_receipt",)),
        ("failed_problem_critic_suggestion_receipts",
         ("problem_critic_suggestion_receipt",)),
        ("failed_problem_revision_receipts", ("problem_revision_receipt",)),
        ("failed_problem_dialogue_lineage_receipts",
         ("problem_dialogue_lineage_receipt",)),
        ("failed_problem_dialogue_final_receipts", ("problem_dialogue_final_receipt",)),
    )
    result = {name: _unique(run.result.get(key) for run in runs for key in keys)
              for name, keys in pairs}
    result["failed_problem_decision_receipts"] = _unique(
        value for run in runs for value in _problem_decisions(run.result)
    )
    return result


def _unique(values):
    result, seen = [], set()
    for value in values:
        if not value or value.get("receipt_hash") in seen:
            continue
        seen.add(value["receipt_hash"]); result.append(value)
    return result


def _problem_decisions(result):
    if result.get("problem_dialogue_decision_receipts"):
        return tuple(result["problem_dialogue_decision_receipts"])
    if result.get("problem_decision_receipt"):
        return (result["problem_decision_receipt"],)
    if result.get("problem_receipt") or result.get("coordination_receipt"):
        return (result.get("decision_receipt"),)
    return ()
