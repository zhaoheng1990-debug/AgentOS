"""Schema and mechanical lineage checks for revision workers."""

from __future__ import annotations

import copy

from .collaborative_stability_experiment import exact_three_schema
from .runtime_escalation_policy import DIAGNOSTIC_FLAGS, ROUTE_IDS


REVISION_ACTIONS = ("KEEP", "REVISE", "REPLACE")
_CANDIDATE_FIELDS = (
    "candidate_id", "lane", "question", "source_object_id",
    "target_object_id", "constraint_object_ids", "epistemic_basis",
    "structural_origin", "falsifier", "required_observation",
    "evidence_span_ids", "estimated_test_cost",
)


def lineage_revision_schema(*, item, refs, provisional_receipt):
    schema = copy.deepcopy(exact_three_schema(
        item=item,
        arm_id="A1_ONTOLOGY",
        refs=refs,
    ))
    candidate_ids = [
        value["candidate_id"]
        for value in provisional_receipt["problem_candidates"]
    ]
    schema["properties"]["problem_candidates"]["items"]["properties"][
        "candidate_id"
    ] = {"type": "string", "enum": candidate_ids}
    span_ids = [
        value["span_id"] for value in item["evidence_spans"]
    ]
    schema["required"].extend([
        "worker_route_id", "revision_actions", "revision_summary",
    ])
    schema["properties"]["worker_route_id"] = {
        "type": "string", "enum": list(ROUTE_IDS),
    }
    schema["properties"]["revision_actions"] = {
        "type": "array", "minItems": 3, "maxItems": 3,
        "items": {
            "type": "object", "additionalProperties": False,
            "required": [
                "original_candidate_id", "final_candidate_id", "action",
                "addressed_diagnostic_flags", "evidence_span_ids",
                "rationale",
            ],
            "properties": {
                "original_candidate_id": {
                    "type": "string", "enum": candidate_ids,
                },
                "final_candidate_id": {
                    "type": "string", "enum": candidate_ids,
                },
                "action": {
                    "type": "string", "enum": list(REVISION_ACTIONS),
                },
                "addressed_diagnostic_flags": {
                    "type": "array", "uniqueItems": True,
                    "items": {
                        "type": "string",
                        "enum": list(DIAGNOSTIC_FLAGS),
                    },
                },
                "evidence_span_ids": {
                    "type": "array", "uniqueItems": True,
                    "items": {"type": "string", "enum": span_ids},
                },
                "rationale": {"type": "string"},
            },
        },
    }
    schema["properties"]["revision_summary"] = {"type": "string"}
    return schema


def lineage_failures(*, final_receipt, provisional_receipt, trigger, item):
    failures = []
    if final_receipt.get("worker_route_id") != trigger["route_id"]:
        failures.append("WORKER_ROUTE_MISMATCH")
    actions = final_receipt.get("revision_actions")
    if not isinstance(actions, list) or len(actions) != 3:
        return failures + ["REVISION_ACTION_COUNT_INVALID"]
    original = {
        value["candidate_id"]: value
        for value in provisional_receipt.get("problem_candidates", [])
        if isinstance(value, dict) and "candidate_id" in value
    }
    final = {
        value["candidate_id"]: value
        for value in final_receipt.get("problem_candidates", [])
        if isinstance(value, dict) and "candidate_id" in value
    }
    original_action_ids = {
        value.get("original_candidate_id")
        for value in actions if isinstance(value, dict)
    }
    final_action_ids = {
        value.get("final_candidate_id")
        for value in actions if isinstance(value, dict)
    }
    if original_action_ids != set(original):
        failures.append("ORIGINAL_CANDIDATE_LINEAGE_INCOMPLETE")
    if final_action_ids != set(final):
        failures.append("FINAL_CANDIDATE_LINEAGE_INCOMPLETE")
    allowed_spans = {
        value["span_id"] for value in item["evidence_spans"]
    }
    allowed_flags = set(trigger["diagnostic_flags"])
    for action in actions:
        if not isinstance(action, dict):
            failures.append("REVISION_ACTION_NOT_OBJECT")
            continue
        source_id = action.get("original_candidate_id")
        target_id = action.get("final_candidate_id")
        if source_id != target_id:
            failures.append("CANDIDATE_SLOT_ID_CHANGED")
            continue
        before = original.get(source_id)
        after = final.get(target_id)
        if before is None or after is None:
            continue
        action_id = action.get("action")
        same_candidate = all(
            before.get(field) == after.get(field)
            for field in _CANDIDATE_FIELDS
        )
        same_relation = (
            before.get("source_object_id") == after.get("source_object_id")
            and before.get("target_object_id")
            == after.get("target_object_id")
        )
        if action_id == "KEEP" and not same_candidate:
            failures.append(f"KEEP_MUTATED_CANDIDATE:{source_id}")
        elif action_id == "REVISE" and (
            same_candidate or not same_relation
        ):
            failures.append(f"REVISE_RELATION_OR_NOOP_INVALID:{source_id}")
        elif action_id == "REPLACE" and (
            same_candidate or same_relation
        ):
            failures.append(f"REPLACE_RELATION_UNCHANGED:{source_id}")
        elif action_id not in REVISION_ACTIONS:
            failures.append(f"REVISION_ACTION_INVALID:{source_id}")
        flags = action.get("addressed_diagnostic_flags")
        if (
            not isinstance(flags, list)
            or not set(flags).issubset(allowed_flags)
        ):
            failures.append(f"ADDRESSED_FLAGS_INVALID:{source_id}")
        spans = action.get("evidence_span_ids")
        if (
            not isinstance(spans, list)
            or not set(spans).issubset(allowed_spans)
        ):
            failures.append(f"REVISION_EVIDENCE_SCOPE_INVALID:{source_id}")
    return failures
