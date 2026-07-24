"""Run the frozen v0.9 three-lane representation experiment."""

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
from local_collective_cognition.clarification_action_credit_contracts import FINGERPRINT_TASK_KIND
from local_collective_cognition.clarification_two_axis_contracts import TWO_AXIS_TASK_KIND
from local_collective_cognition.clarification_two_axis_runtime import CATEGORY_LANE, LANES, PAIRED_AXIS_LANE, SHUFFLED_AXIS_LANE, ClarificationTwoAxisRuntime, validate_two_axis_run
from local_collective_cognition.openai_compatible_provider import OpenAICompatibleJsonAdapter, OpenAICompatibleProviderSpec


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def adapter(provider_id, task_kind):
    spec = OpenAICompatibleProviderSpec(
        provider_id,
        "deepseek-v4-flash",
        "https://api.deepseek.com/chat/completions",
        "DEEPSEEK_API_KEY",
        (task_kind,),
        max_tokens=2400,
        timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    )
    return BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(spec), max_attempts=2)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_two_axis_v0_9"
    parser.add_argument("--corpus", default=f"{base}/private_two_axis_corpus.json")
    parser.add_argument("--output", default=f"{base}/candidate_run.json")
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    adapters = {
        CATEGORY_LANE: adapter("deepseek-two-axis-category", FINGERPRINT_TASK_KIND),
        PAIRED_AXIS_LANE: adapter("deepseek-two-axis-paired", TWO_AXIS_TASK_KIND),
        SHUFFLED_AXIS_LANE: adapter("deepseek-two-axis-shuffled", TWO_AXIS_TASK_KIND),
    }
    experiment_id = "two-axis-representation-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ClarificationTwoAxisRuntime(corpus_artifact=corpus).evaluate(experiment_id=experiment_id, adapters=adapters)
    validate_two_axis_run(run, corpus_artifact=corpus)
    resolve(args.output).write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "calls": run["total_unique_provider_calls"],
        "tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "failures": {lane: len(run["lanes"][lane]["failures"]) for lane in LANES},
        "prediction_counts": {
            "CATEGORY_FINGERPRINT": dict(Counter(row["category_fingerprint"] for row in run["predictions"])),
            "PAIRED_TWO_AXIS": dict(Counter(row["paired_derived_category"] for row in run["predictions"])),
            "SHUFFLED_TWO_AXIS": dict(Counter(row["shuffled_derived_category"] for row in run["predictions"])),
        },
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
