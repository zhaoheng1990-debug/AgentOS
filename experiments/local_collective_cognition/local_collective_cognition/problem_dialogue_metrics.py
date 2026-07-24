"""Problem-dialogue object gain, lineage, outcome, and work metrics."""

from __future__ import annotations

from .problem_formulation_metrics import problem_formulation_metrics


def problem_dialogue_metrics(events, failures, audit, comparisons):
    admitted = audit["admitted"]
    final = audit["stages"]["revision_final"]
    compatibility_audit = {
        "admitted_items": admitted["admitted_items"],
        "exact_problem_definitions": admitted["exact_problem_definitions"],
        "field_matches": admitted["field_matches"],
        "candidate_items": final["items"],
        "exact_candidate_definitions": final["exact_definitions"],
        "candidate_union_exact_items": final["union_exact_items"],
        "candidate_field_matches": final["field_matches"],
    }
    result = problem_formulation_metrics(events, failures, compatibility_audit, comparisons)
    sessions = [record for event in events
                for record in (event["primary_argument"], event["peer_argument"])]
    result.update({
        "problem_dialogue_threads": len(sessions) + sum(
            len(item.get("failed_problem_dialogue_lineage_receipts", ()))
            for item in failures
        ),
        "problem_dialogue_lineage_allows": sum(
            item.get("problem_dialogue_lineage_receipt", {}).get("status") == "ALLOW"
            for item in sessions
        ) + sum(
            receipt.get("status") == "ALLOW" for failure in failures
            for receipt in failure.get("failed_problem_dialogue_lineage_receipts", ())
        ),
        "problem_dialogue_lineage_blocks": sum(
            receipt.get("status") == "BLOCK" for failure in failures
            for receipt in failure.get("failed_problem_dialogue_lineage_receipts", ())
        ),
        "problem_dialogue_stage_audit": audit["stages"],
        "proposal_to_suggestion_exact_item_gain":
            audit["proposal_to_suggestion_exact_item_gain"],
        "proposal_to_revision_exact_item_gain":
            audit["proposal_to_revision_exact_item_gain"],
        "problem_dialogue_object_gain_positive":
            audit["proposal_to_revision_exact_item_gain"] > 0,
    })
    return result
