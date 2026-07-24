"""Mechanical work totals preserved by failed structured sessions."""

from __future__ import annotations


def summarize_failed_session_work(runs) -> dict[str, int]:
    fields = ("session_provider_turns", "session_applied_steps", "session_invalid_actions",
              "session_control_turns", "session_argument_turns",
              "session_invalid_controls", "session_invalid_arguments",
              "session_tool_turns", "session_registry_options", "session_score_receipts",
              "session_menu_options", "session_inference_passes")
    fields = (*fields, "session_plan_score_receipts", "session_plan_menu_options",
              "session_plan_inference_passes", "session_plan_input_tokens",
              "session_plan_steps")
    return {field: sum(_value(item.result, field) for item in runs) for field in fields}


def _value(result, field):
    if field in result:
        return int(result[field])
    if field == "session_provider_turns":
        return len(result.get("actions", ()))
    if field == "session_applied_steps":
        return len(result.get("step_receipts", ()))
    return 0
