"""Run the frozen pre-oracle v0.6 Provider arms."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter
from local_collective_cognition.clarification_regret_contracts import DIRECT_TASK_KIND, REGRET_TASK_KIND
from local_collective_cognition.clarification_regret_fusion import DIRECT, LANES, REGRET_1, REGRET_2, REGRET_3
from local_collective_cognition.clarification_regret_holdout import validate_clarification_regret_artifact
from local_collective_cognition.clarification_regret_runtime import ClarificationRegretRuntime, validate_clarification_regret_run
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def deepseek(provider_id, task_kind):
    adapter = OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
        provider_id, "deepseek-v4-flash", "https://api.deepseek.com/chat/completions", "DEEPSEEK_API_KEY", (task_kind,),
        max_tokens=2200, timeout_seconds=240, extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    ))
    return BoundedRetryProviderAdapter(adapter, max_attempts=2)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_regret_v0_6"
    parser.add_argument("--corpus", default=f"{base}/private_clarification_regret_corpus.json")
    parser.add_argument("--output", default=f"{base}/candidate_run.json")
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    validate_clarification_regret_artifact(corpus)
    adapters = {
        DIRECT: deepseek("deepseek-clarification-direct", DIRECT_TASK_KIND),
        REGRET_1: deepseek("deepseek-clarification-regret-r1", REGRET_TASK_KIND),
        REGRET_2: deepseek("deepseek-clarification-regret-r2", REGRET_TASK_KIND),
        REGRET_3: deepseek("deepseek-clarification-regret-r3", REGRET_TASK_KIND),
    }
    run = ClarificationRegretRuntime(corpus_artifact=corpus).evaluate(
        experiment_id="clarification-regret-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"), adapters=adapters,
    )
    validate_clarification_regret_run(run, corpus_artifact=corpus)
    resolve(args.output).write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    records = run["fusion"]["records"]
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "calls": run["total_unique_provider_calls"],
        "tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "successes": {lane: len(run["lanes"][lane]["judgments"]) for lane in LANES},
        "failures": {lane: len(run["lanes"][lane]["failures"]) for lane in LANES},
        "actions": {
            "DIRECT": dict(Counter(item["direct_policy_action"] for item in records)),
            "SINGLE_REGRET": dict(Counter(item["single_regret_action"] for item in records)),
            "THREE_PASS_REGRET": dict(Counter(item["three_pass_regret_action"] for item in records)),
        },
        "accounting": run["fusion"]["arm_accounting"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
