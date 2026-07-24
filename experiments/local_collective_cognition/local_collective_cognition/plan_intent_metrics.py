"""Outcome, coherence, calibration, and cost gates for plan-intent experiments."""

from __future__ import annotations


MAX_CALL_RATIO_VS_MAJORITY = 1.50
MAX_TOKEN_RATIO_VS_MAJORITY = 4.00


def plan_intent_metrics(events, failures, comparisons):
    sessions = [record for event in events
                for record in (event["primary_argument"], event["peer_argument"])]
    plans = [item.get("plan_intent_receipt") for item in sessions
             if item.get("plan_intent_receipt")]
    gates = [item.get("plan_gate_receipt") for item in sessions if item.get("plan_gate_receipt")]
    judges = [event["judgment"].get("decision_receipt") for event in events
              if event["judgment"].get("decision_receipt")]
    verification = [receipt for event in events for receipt in event["verification_receipts"]]
    result = {
        "plan_intent_receipts": len(plans),
        "plan_gate_receipts": len(gates),
        "plan_gate_allows": sum(item["status"] == "ALLOW" for item in gates),
        "plan_gate_blocks": sum(item["status"] == "BLOCK" for item in gates),
        "calibrated_judge_receipts": len(judges),
        "plan_verified_receipts": sum(item["status"] == "VERIFIED" for item in verification),
        "plan_budget_failure_count": sum(
            any("budget" in str(value).lower() for value in item.get("failures", ()))
            for item in failures
        ),
        "plan_self_operand_actions": sum(
            action["action"] == "APPLY" and len(action["inputs"]) == 2
            and action["inputs"][0] == action["inputs"][1]
            for session in sessions for action in session.get("actions", ())
        ),
    }
    for field in ("plan_score_receipts", "plan_menu_options", "plan_inference_passes",
                  "plan_input_tokens", "plan_steps"):
        key = "session_" + field
        completed = sum(int(item.get(key, 0)) for item in sessions)
        failed = sum(int(item.get(key, 0)) for item in failures)
        result["completed_" + field] = completed
        result["failed_" + field] = failed
        result[field] = completed + failed
    call_ok = comparisons["call_ratio_vs_majority"] <= MAX_CALL_RATIO_VS_MAJORITY
    token_ok = comparisons["token_ratio_vs_majority"] <= MAX_TOKEN_RATIO_VS_MAJORITY
    result.update({
        "calibrated_score_receipts_total": result["plan_score_receipts"] + len(judges),
        "plan_cost_call_ratio_limit": MAX_CALL_RATIO_VS_MAJORITY,
        "plan_cost_token_ratio_limit": MAX_TOKEN_RATIO_VS_MAJORITY,
        "plan_cost_budget_passed": call_ok and token_ok,
    })
    net = comparisons["case_observed_net_cbit"]
    result["plan_intent_improvement_status"] = (
        "HARMFUL_PLAN_INTENT" if net < 0 else
        "POSITIVE_CBIT_OVER_COST_BUDGET" if net > 0 and not (call_ok and token_ok) else
        "POSITIVE_CBIT_WITHIN_COST_BUDGET" if net > 0 else
        "NO_POSITIVE_PLAN_INTENT_CBIT"
    )
    return result
