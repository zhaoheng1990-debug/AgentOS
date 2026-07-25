import json
from typing import Any

from theory_first_r4_relation.hard_cases import HARD_CASES
from theory_first_r4_relation.hard_evaluation import run_hard_live


def _item(case, state=None) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "relation_state": state or case.private_relation_state,
        "evidence_refs": list(case.evidence_refs),
        "unresolved_assumptions": (
            ["Source lineage is not available."]
            if case.private_relation_state == "UNRESOLVED"
            else []
        ),
    }


class HardAdapter:
    def __init__(self, overrides=None) -> None:
        self.overrides = overrides or {}
        self.attempts = []

    def call_json(self, logical_call_id, system_prompt, user_prompt, validator):
        assert logical_call_id == "fresh_hard_batch"
        content = json.dumps(
            {
                "payload": [
                    _item(case, self.overrides.get(case.case_id))
                    for case in HARD_CASES
                ]
            }
        )
        parsed = validator(content)
        self.attempts.append(
            {
                "logical_call_id": logical_call_id,
                "attempt": 1,
                "status": "VALID",
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 100,
                    "total_tokens": 200,
                    "cache_hit_tokens": 0,
                },
            }
        )
        return content, parsed

    def ledger(self):
        return self.attempts


def test_perfect_hard_batch_passes_all_gates() -> None:
    result = run_hard_live(HardAdapter())
    assert result["status"] == "PASS_FRESH_HARD_RELATION_GENERALIZATION"
    assert result["gate_pass_count"] == 13
    assert result["relation_accuracy"] == 1.0


def test_false_combine_is_harmful_failure() -> None:
    result = run_hard_live(
        HardAdapter({"R43E-13": "INDEPENDENT_DISTINCT"})
    )
    assert result["status"] == "FAIL_HARMFUL_GENERALIZATION"
    assert result["false_combine_case_ids"] == ["R43E-13"]

