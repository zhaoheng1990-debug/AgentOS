"""Run the v0.26 structure-first smoke on DeepSeek API."""

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
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.structural_world_expansion import (  # noqa: E402
    TASK_KIND,
    analyze_structural_world_smoke,
    run_structural_world_smoke,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    output = REPO_ROOT / "outputs" / "structural_world_v0_26"
    constraints = read(output / "science_constraints_frozen.json")
    corpus = read(output / "structural_world_corpus_frozen.json")
    preregistration = read(output / "structural_world_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-structural-world-v0-26",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=3400,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run = run_structural_world_smoke(
        constraints=constraints,
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
    )
    analysis = analyze_structural_world_smoke(
        constraints=constraints,
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    write(output / "structural_world_run.json", run)
    write(output / "structural_world_analysis.json", analysis)
    print(json.dumps({
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "task_call_count": analysis["task_call_count"],
        "valid_receipt_count": analysis["valid_receipt_count"],
        "failure_count": analysis["failure_count"],
        "arm_metrics": analysis["arm_metrics"],
        "best_structural_arm": analysis["best_structural_arm"],
        "problem_target_f1_gain_over_direct": (
            analysis["problem_target_f1_gain_over_direct"]
        ),
        "gate_conditions": analysis["gate_conditions"],
        "structure_first_smoke_gate": (
            analysis["structure_first_smoke_gate"]
        ),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
