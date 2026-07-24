"""Run all pre-reference v0.3 precision-confirmation arms."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.negative_evidence_audit_contracts import (  # noqa: E402
    FABRICATION_AUDIT,
    LIVE_AMBIGUITY_AUDIT,
    TASK_KINDS,
)
from local_collective_cognition.negative_evidence_precision_contracts import CONFIRMATION_TASK_KIND  # noqa: E402
from local_collective_cognition.negative_evidence_precision_fusion import (  # noqa: E402
    BASELINE,
    FABRICATION,
    LIVE_AMBIGUITY,
    MONOLITHIC_REPEAT_2,
    MONOLITHIC_REPEAT_3,
    MONOLITHIC_REPEAT_4,
    VETO_CONFIRMATION,
)
from local_collective_cognition.negative_evidence_precision_holdout import validate_precision_corpus_artifact  # noqa: E402
from local_collective_cognition.negative_evidence_precision_runtime import (  # noqa: E402
    NegativeEvidencePrecisionRuntime,
    validate_precision_candidate_run,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.structure_semantic_judge_contracts import JUDGE_TASK_KIND  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _deepseek(provider_id, task_kind, max_tokens):
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id, "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY",
        (task_kind,), max_tokens=max_tokens, timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    return BoundedRetryProviderAdapter(adapter, max_attempts=2)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_precision_v0_3"
    parser.add_argument("--corpus", default=f"{base}/private_negative_precision_corpus.json")
    parser.add_argument("--output", default=f"{base}/four_arm_candidate_run.json")
    args = parser.parse_args()
    corpus = json.loads(_resolve(args.corpus).read_text(encoding="utf-8"))
    validate_precision_corpus_artifact(corpus)
    adapters = {
        BASELINE: _deepseek("deepseek-precision-baseline", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_2: _deepseek("deepseek-precision-monolithic-r2", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_3: _deepseek("deepseek-precision-monolithic-r3", JUDGE_TASK_KIND, 2600),
        MONOLITHIC_REPEAT_4: _deepseek("deepseek-precision-monolithic-r4", JUDGE_TASK_KIND, 2600),
        LIVE_AMBIGUITY: _deepseek("deepseek-precision-live", TASK_KINDS[LIVE_AMBIGUITY_AUDIT], 1800),
        FABRICATION: _deepseek("deepseek-precision-fabrication", TASK_KINDS[FABRICATION_AUDIT], 1800),
        VETO_CONFIRMATION: _deepseek("deepseek-precision-confirmation", CONFIRMATION_TASK_KIND, 1800),
    }
    experiment_id = "negative-precision-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = NegativeEvidencePrecisionRuntime(corpus_artifact=corpus).evaluate(
        experiment_id=experiment_id, adapters=adapters,
    )
    validate_precision_candidate_run(run, corpus_artifact=corpus)
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    records = run["fusion"]["records"]
    state_keys = {
        "SINGLE_MONOLITHIC": "single_monolithic_state",
        "BUDGET_CEILING_MONOLITHIC": "budget_ceiling_monolithic_state",
        "NAIVE_VETO": "naive_veto_state",
        "CONFIRMED_VETO": "confirmed_veto_state",
    }
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "source_artifact_hash": run["source_artifact_hash"],
        "total_unique_provider_calls": run["total_unique_provider_calls"],
        "total_unique_tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "lane_successes": {lane: len(value["judgments"]) for lane, value in run["lanes"].items()},
        "lane_failures": {lane: len(value["failures"]) for lane, value in run["lanes"].items()},
        "confirmation_target_count": len(run["fusion"]["confirmation_target_ids"]),
        "arm_states": {
            arm: dict(Counter(item[key] for item in records))
            for arm, key in state_keys.items()
        },
        "arm_accounting": run["fusion"]["arm_accounting"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
