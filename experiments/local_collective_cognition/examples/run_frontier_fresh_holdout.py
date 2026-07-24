"""Run the frozen v0.27 A0/A1 frontier-gray holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import (  # noqa: E402
    BoundedRetryProviderAdapter,
)
from local_collective_cognition.frontier_experiment import (  # noqa: E402
    TASK_KIND,
    analyze_frontier_holdout,
    run_frontier_batch,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "frontier_fresh_v0_27"
    corpus = read(output / "frontier_corpus_frozen.json")
    preregistration = read(output / "frontier_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-frontier-fresh-v0-27",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=2600,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run = run_frontier_batch(
        artifact=corpus,
        adapter=adapter,
        mode="FRESH_HOLDOUT",
        checkpoint_callback=lambda value: write(
            output / "frontier_progress.json", value
        ),
    )
    analysis = analyze_frontier_holdout(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    write(output / "frontier_run.json", run)
    write(output / "frontier_analysis.json", analysis)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "comparison_valid": analysis["comparison_valid"],
        "arm_runtime_metrics": analysis["arm_runtime_metrics"],
        "arm_cbit_metrics": analysis[
            "realized_cbit_ledger"
        ]["arm_metrics"],
        "a1_cbit_gain_per_case": analysis[
            "a1_cbit_gain_per_case"
        ],
        "a1_cbit_efficiency_ratio_to_a0": analysis[
            "a1_cbit_efficiency_ratio_to_a0"
        ],
        "conditions": analysis["conditions"],
        "frontier_holdout_gate": analysis["frontier_holdout_gate"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
