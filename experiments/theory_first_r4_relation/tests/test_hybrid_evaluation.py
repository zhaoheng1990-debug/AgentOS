import json
from pathlib import Path
from typing import Any

from theory_first_r4_relation.hybrid_evaluation import run_hybrid_live
from theory_first_r4_relation.semantic_cases import CASES


REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "outputs/r4_provider_semantic_relation_v0_3b/raw_attempts"


def _item(case) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "relation_state": case.private_relation_state,
        "evidence_refs": list(case.evidence_refs),
        "unresolved_assumptions": [],
    }


class PerfectAdapter:
    def __init__(self, state_overrides=None) -> None:
        self.calls = []
        self.attempts = []
        self.state_overrides = state_overrides or {}

    def call_json(self, logical_call_id, system_prompt, user_prompt, validator):
        self.calls.append(logical_call_id)
        selected = (
            CASES
            if logical_call_id == "batch_B"
            else (
                next(
                    case
                    for case in CASES
                    if logical_call_id == f"single_{case.case_id}"
                ),
            )
        )
        items = [_item(case) for case in selected]
        for item in items:
            item["relation_state"] = self.state_overrides.get(
                item["case_id"], item["relation_state"]
            )
        content = json.dumps({"payload": items})
        parsed = validator(content)
        self.attempts.append(
            {
                "logical_call_id": logical_call_id,
                "attempt": 1,
                "status": "VALID",
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 10,
                    "total_tokens": 20,
                    "cache_hit_tokens": 0,
                },
            }
        )
        return content, parsed

    def ledger(self):
        return self.attempts


def test_hybrid_runner_calls_only_batch_b_and_singles() -> None:
    adapter = PerfectAdapter()
    result = run_hybrid_live(adapter, RAW_DIR)
    assert result["status"] == "PASS_PRESENTATION_ROBUST_WITH_HYBRID_TIME_LIMIT"
    assert result["gate_pass_count"] == 15
    assert len(adapter.calls) == 13
    assert adapter.calls[0] == "batch_B"
    assert not any(call.lower() == "batch_a" for call in adapter.calls)
    assert result["historical_anchor"]["new_batch_a_calls"] == 0


def test_false_combine_is_a_hard_failure() -> None:
    adapter = PerfectAdapter({"R43B-05": "INDEPENDENT_DISTINCT"})
    result = run_hybrid_live(adapter, RAW_DIR)
    assert result["status"] == "FAIL_HARMFUL_ACTION"
    assert not result["gates"]["harmful_action_zero"]
