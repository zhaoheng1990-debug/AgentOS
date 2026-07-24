"""Completed, failed-path, and total work metrics for constrained sessions."""

from __future__ import annotations


def constrained_tool_metrics(events, failures, case_count):
    receipts = [receipt for event in events for receipt in event["verification_receipts"]]
    sessions = [record for event in events
                for record in (event["primary_argument"], event["peer_argument"])]
    failure_receipts = sum(item.get("session_final_receipts", 0) for item in failures)
    completed_sessions = len(receipts) + failure_receipts
    expected_sessions = 2 * case_count
    result = {
        "constrained_tool_event_receipts": len(receipts),
        "constrained_tool_failure_path_receipts": failure_receipts,
        "constrained_tool_receipts": completed_sessions,
        "constrained_tool_verified": (
            sum(item["status"] == "VERIFIED" for item in receipts)
            + sum(item.get("session_verified_receipts", 0) for item in failures)
        ),
        "constrained_tool_channel_completion_rate": (
            round(completed_sessions / expected_sessions, 12) if expected_sessions else None
        ),
        "constrained_tool_channel_completion_status": (
            "ALL_CANDIDATE_SESSIONS_TERMINATED" if completed_sessions == expected_sessions
            else "CANDIDATE_SESSION_COMPLETION_INCOMPLETE"
        ),
    }
    for field in ("provider_turns", "tool_turns", "applied_steps",
                  "registry_options", "invalid_actions"):
        key = "session_" + field
        completed = sum(int(item.get(key, 0)) for item in sessions)
        failed = sum(int(item.get(key, 0)) for item in failures)
        result["constrained_completed_" + field] = completed
        result["constrained_failed_" + field] = failed
        result["constrained_" + field] = completed + failed
    return result
