"""Work and receipt metrics for hierarchical enum-scored sessions."""

from __future__ import annotations


def hierarchical_tool_metrics(events, failures, case_count):
    sessions = [record for event in events
                for record in (event["primary_argument"], event["peer_argument"])]
    event_receipts = [receipt for session in sessions
                      for receipt in session.get("decision_receipts", ())]
    judge_receipts = [event["judgment"].get("decision_receipt") for event in events
                      if event["judgment"].get("decision_receipt")]
    verification = [receipt for event in events for receipt in event["verification_receipts"]]
    failure_terminals = sum(item.get("session_final_receipts", 0) for item in failures)
    terminated = len(verification) + failure_terminals
    expected = 2 * case_count
    result = {
        "hierarchical_action_score_receipts": len(event_receipts),
        "hierarchical_judge_score_receipts": len(judge_receipts),
        "hierarchical_score_receipts": len(event_receipts) + len(judge_receipts),
        "hierarchical_judge_receipt_rate": (
            round(len(judge_receipts) / case_count, 12) if case_count else None
        ),
        "hierarchical_candidate_sessions_terminated": terminated,
        "hierarchical_candidate_session_completion_rate": (
            round(terminated / expected, 12) if expected else None
        ),
        "hierarchical_verified": (
            sum(item["status"] == "VERIFIED" for item in verification)
            + sum(item.get("session_verified_receipts", 0) for item in failures)
        ),
    }
    result["hierarchical_completed_action_score_receipts"] = sum(
        int(item.get("session_score_receipts", 0)) for item in sessions
    )
    result["hierarchical_failed_action_score_receipts"] = sum(
        int(item.get("session_score_receipts", 0)) for item in failures
    )
    for field in ("tool_turns", "menu_options", "inference_passes"):
        key = "session_" + field
        completed = sum(int(item.get(key, 0)) for item in sessions)
        failed = sum(int(item.get(key, 0)) for item in failures)
        result["hierarchical_completed_" + field] = completed
        result["hierarchical_failed_" + field] = failed
        result["hierarchical_" + field] = completed + failed
    result["hierarchical_mean_options_per_inference"] = (
        round(result["hierarchical_menu_options"] / result["hierarchical_inference_passes"], 12)
        if result["hierarchical_inference_passes"] else None
    )
    return result
