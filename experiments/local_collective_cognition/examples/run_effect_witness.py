"""Run v0.56 fresh EFFECT witness experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.effect_witness_experiment import (  # noqa: E402
    analyze_effect_witness_experiment,
    run_effect_witness_experiment,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    output = REPO_ROOT / "outputs" / "effect_witness_v0_56"
    corpus = read(output / "effect_witness_corpus_frozen.json")
    prereg = read(output / "effect_witness_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-effect-witness-v0-56",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=4200,
            timeout_seconds=300,
            extra_body={"thinking": {"type": "disabled"}, "temperature": 0},
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run_path = output / "effect_witness_run.json"
    if run_path.exists():
        run = read(run_path)
    else:
        run = run_effect_witness_experiment(
            corpus=corpus, preregistration=prereg, adapter=adapter
        )
        write(run_path, run)
    analysis = analyze_effect_witness_experiment(
        corpus=corpus, preregistration=prereg, run=run
    )
    write(output / "effect_witness_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "effect": analysis["effect_witness_metrics"],
        "replacement": analysis["replacement_gate_metrics"],
        "stability": analysis["relation_stability_metrics"]["arm_summaries"],
        "failed": sorted(k for k, v in analysis["conditions"].items() if not v),
        "tokens": analysis["physical_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
