import json

from theory_first_r4_relation.semantic_cases import CASES
from theory_first_r4_relation.semantic_evaluation import run_live


class PerfectAdapter:
    def __init__(self):
        self.calls = []

    def call_json(self, logical_call_id, system_prompt, user_prompt, validator):
        if logical_call_id.startswith("batch_"):
            selected = CASES
        else:
            case_id = logical_call_id.removeprefix("single_")
            selected = tuple(case for case in CASES if case.case_id == case_id)
        content = json.dumps(
            {
                "receipts": [
                    {
                        "case_id": case.case_id,
                        "relation_state": case.private_relation_state,
                        "evidence_refs": list(case.evidence_refs),
                        "unresolved_assumptions": [],
                    }
                    for case in selected
                ]
            }
        )
        parsed = validator(content)
        self.calls.append(
            {
                "logical_call_id": logical_call_id,
                "status": "VALID",
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "cache_hit_tokens": 0,
                },
            }
        )
        return content, parsed

    def ledger(self):
        return list(self.calls)


def test_perfect_semantic_panel_passes_all_gates() -> None:
    result = run_live(PerfectAdapter())
    assert result["status"] == "PASS"
    assert result["gate_pass_count"] == result["gate_count"] == 14
    assert result["logical_call_count"] == 14
