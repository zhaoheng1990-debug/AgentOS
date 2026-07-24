"""Problem-object formation, admission, binding, outcome, and work metrics."""

from __future__ import annotations


def problem_formulation_metrics(events, failures, audit, comparisons):
    sessions = [record for event in events
                for record in (event["primary_argument"], event["peer_argument"])]
    definitions = [item.get("problem_definition_receipt") for item in sessions
                   if item.get("problem_definition_receipt")]
    bindings = [item.get("problem_plan_binding_receipt") for item in sessions
                if item.get("problem_plan_binding_receipt")]
    coordinations = [event["judgment"].get("problem_coordination_receipt") for event in events
                     if event["judgment"].get("problem_coordination_receipt")]
    admissions = [event["judgment"].get("problem_admission_receipt") for event in events
                  if event["judgment"].get("problem_admission_receipt")]
    failed_definitions = [item for failure in failures
                          for item in failure.get("failed_problem_definition_receipts", ())]
    failed_admissions = [item for failure in failures
                         for item in failure.get("failed_problem_admission_receipts", ())]
    failed_bindings = [item for failure in failures
                       for item in failure.get("failed_problem_plan_binding_receipts", ())]
    score_receipts = [item.get("problem_decision_receipt") for item in sessions
                      if item.get("problem_decision_receipt")]
    score_receipts += [event["judgment"].get("problem_coordination_decision_receipt")
                       for event in events
                       if event["judgment"].get("problem_coordination_decision_receipt")]
    score_receipts += [item for failure in failures
                       for item in failure.get("failed_problem_decision_receipts", ())]
    net = comparisons["case_observed_net_cbit"]
    return {
        "problem_definition_receipts": len(definitions) + len(failed_definitions),
        "problem_coordination_receipts": len(coordinations) + sum(
            len(item.get("failed_problem_coordination_receipts", ())) for item in failures),
        "problem_admission_receipts": len(admissions) + len(failed_admissions),
        "problem_admission_allows": sum(item["status"] == "ALLOW" for item in admissions)
        + sum(item["status"] == "ALLOW" for item in failed_admissions),
        "problem_admission_blocks": sum(item["status"] == "BLOCK" for item in failed_admissions),
        "problem_plan_binding_receipts": len(bindings) + len(failed_bindings),
        "problem_plan_binding_allows": sum(item["status"] == "ALLOW" for item in bindings)
        + sum(item["status"] == "ALLOW" for item in failed_bindings),
        "problem_plan_binding_blocks": sum(item["status"] == "BLOCK" for item in failed_bindings),
        "problem_score_receipts": len(score_receipts),
        "problem_inference_passes": sum(item["inference_passes"] for item in score_receipts),
        "problem_input_tokens": sum(decision["input_tokens"] for item in score_receipts
                                    for decision in item["decisions"]),
        "admitted_problem_items_audited": audit["admitted_items"],
        "exact_problem_definitions": audit["exact_problem_definitions"],
        "problem_field_matches": audit["field_matches"],
        "problem_candidate_items_audited": audit["candidate_items"],
        "exact_problem_candidate_definitions": audit["exact_candidate_definitions"],
        "problem_candidate_union_exact_items": audit["candidate_union_exact_items"],
        "problem_candidate_field_matches": audit["candidate_field_matches"],
        "problem_formulation_improvement_status": (
            "POSITIVE_PROBLEM_GROUNDED_CBIT" if net > 0 else
            "NEGATIVE_PROBLEM_GROUNDED_CBIT" if net < 0 else
            "NO_POSITIVE_PROBLEM_GROUNDED_CBIT"
        ),
    }
