"""Run the frozen v0.11 equal-call semantic-basis experiment."""

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
from local_collective_cognition.clarification_semantic_basis_contracts import SEMANTIC_BASIS_TASK_KIND
from local_collective_cognition.clarification_semantic_basis_runtime import BASELINE_LANE, LANES, SEMANTIC_BASIS_LANE, ClarificationSemanticBasisRuntime, validate_semantic_basis_run
from local_collective_cognition.clarification_warrant_contracts import WARRANT_TASK_KIND
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
        max_tokens=2800,
        timeout_seconds=240,
        extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
    )
    return BoundedRetryProviderAdapter(OpenAICompatibleJsonAdapter(spec), max_attempts=2)


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_semantic_basis_v0_11"
    parser.add_argument("--corpus", default=f"{base}/private_semantic_basis_corpus.json")
    parser.add_argument("--output", default=f"{base}/candidate_run.json")
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    adapters = {
        BASELINE_LANE: adapter("deepseek-v011-warrant-baseline", WARRANT_TASK_KIND),
        SEMANTIC_BASIS_LANE: adapter("deepseek-v011-semantic-basis", SEMANTIC_BASIS_TASK_KIND),
    }
    experiment_id = "semantic-basis-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run = ClarificationSemanticBasisRuntime(corpus_artifact=corpus).evaluate(experiment_id=experiment_id, adapters=adapters)
    validate_semantic_basis_run(run, corpus_artifact=corpus)
    resolve(args.output).write_text(json.dumps(run, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_run_hash": run["candidate_run_hash"],
        "calls": run["total_unique_provider_calls"],
        "tokens": run["total_unique_input_tokens"] + run["total_unique_output_tokens"],
        "failures": {lane: len(run["lanes"][lane]["failures"]) for lane in LANES},
        "prediction_counts": {
            "BASELINE_V0_10_WARRANT": dict(Counter(row["baseline_derived_category"] for row in run["predictions"])),
            "SEMANTIC_BASIS_V0_11": dict(Counter(row["semantic_derived_category"] for row in run["predictions"])),
        },
        "selection_bases": dict(Counter(row["semantic_selection_basis"] for row in run["predictions"])),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
