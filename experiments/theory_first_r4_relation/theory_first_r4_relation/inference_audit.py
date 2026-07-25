"""Deterministic corpus and prompt preflight for R4 v0.3G."""

from __future__ import annotations

import json

from .contracts import PLAN_ACTIONS, RELATION_STATES
from .inference_cases import ATTRIBUTE_NAMES, INFERENCE_CASES, PAIR_EXPECTATIONS
from .inference_prompts import inference_batch_prompt


def audit_inference_corpus() -> dict[str, object]:
    ids = [case.case_id for case in INFERENCE_CASES]
    public = json.dumps(
        [case.public_dict() for case in INFERENCE_CASES],
        ensure_ascii=True,
        sort_keys=True,
    )
    prompt = inference_batch_prompt()
    private_values = set(RELATION_STATES) | set(PLAN_ACTIONS)
    pair_case_ids = [
        case_id
        for _, left_id, right_id, _ in PAIR_EXPECTATIONS
        for case_id in (left_id, right_id)
    ]
    gates = {
        "twelve_unique_cases": len(ids) == 12 and len(set(ids)) == 12,
        "six_disjoint_pairs": len(PAIR_EXPECTATIONS) == 6
        and sorted(pair_case_ids) == sorted(ids),
        "five_private_attributes_each": all(
            set(case.attributes()) == set(ATTRIBUTE_NAMES) for case in INFERENCE_CASES
        ),
        "five_reference_bindings_each": all(
            set(case.attribute_refs()) == set(ATTRIBUTE_NAMES)
            for case in INFERENCE_CASES
        ),
        "case_local_refs": all(
            all(
                set(refs).issubset(set(case.evidence_refs))
                for refs in case.attribute_refs().values()
            )
            for case in INFERENCE_CASES
        ),
        "no_relation_or_action_in_public_cases": not any(
            value in public for value in private_values
        ),
        "no_private_reference_in_prompt": not any(
            json.dumps(case.attributes(), sort_keys=True) in prompt
            for case in INFERENCE_CASES
        ),
        "prompt_has_no_runtime_authority_schema": all(
            token not in prompt
            for token in ('"relation_state":', '"action":', '"composition_action":')
        ),
    }
    return {
        "status": "PASS" if all(gates.values()) else "FAIL",
        "gate_count": len(gates),
        "gate_pass_count": sum(gates.values()),
        "gates": gates,
    }

