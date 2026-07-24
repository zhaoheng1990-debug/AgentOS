"""Run the frozen v0.30 selective role-routing experiment."""

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
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.selective_role_routing_experiment import (  # noqa: E402
    analyze_selective_routing_experiment,
    run_selective_routing_experiment,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "selective_role_routing_v0_30"
    corpus = read(
        output / "selective_role_routing_corpus_frozen.json"
    )
    preregistration = read(
        output / "selective_role_routing_preregistration.json"
    )
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-selective-role-routing-v0-30",
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
    run = run_selective_routing_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        checkpoint_callback=lambda value: write(
            output / "selective_role_routing_progress.json", value
        ),
    )
    analysis = analyze_selective_routing_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    write(output / "selective_role_routing_run.json", run)
    write(output / "selective_role_routing_analysis.json", analysis)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "runtime_metrics": analysis["runtime_metrics"],
        "pooled_contrast_metrics": analysis[
            "pooled_contrast_metrics"
        ],
        "majority_positive_case_rate": analysis[
            "majority_positive_case_rate"
        ],
        "route_distribution": analysis["route_distribution"],
        "shadow_regret_audit": analysis["shadow_regret_audit"],
        "formal_path_tokens": analysis["formal_path_tokens"],
        "physical_total_tokens": analysis["physical_total_tokens"],
        "conditions": analysis["conditions"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
