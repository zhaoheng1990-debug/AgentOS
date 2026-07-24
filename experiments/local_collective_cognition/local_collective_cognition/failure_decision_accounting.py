"""Preserve structured decision and gate receipts from failed case stages."""

from __future__ import annotations


def failed_decision_artifacts(runs):
    return {
        "failed_decision_receipts": [receipt for run in runs
                                     for receipt in run.result.get("decision_receipts", ())],
        "failed_plan_intent_receipts": [run.result["plan_intent_receipt"] for run in runs
                                        if run.result.get("plan_intent_receipt")],
        "failed_plan_gate_receipts": [run.result["plan_gate_receipt"] for run in runs
                                      if run.result.get("plan_gate_receipt")],
        "failed_plan_budget_receipts": [run.result["plan_budget_receipt"] for run in runs
                                        if run.result.get("plan_budget_receipt")],
    }
