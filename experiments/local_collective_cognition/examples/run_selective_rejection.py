"""Run v0.52 selective rejection challenge."""

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
from local_collective_cognition.selective_rejection_experiment import (  # noqa: E402
    analyze_selective_rejection_experiment,
    run_selective_rejection_experiment,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    corpus = read(output / "selective_rejection_corpus_frozen.json")
    preregistration = read(
        output / "selective_rejection_preregistration.json"
    )
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-selective-rejection-v0-52",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=4200,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run = run_selective_rejection_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        base_checkpoint_callback=lambda value: write(
            output / "selective_rejection_base_progress.json", value
        ),
        overlay_checkpoint_callback=lambda value: write(
            output / "selective_rejection_overlay_progress.json", value
        ),
    )
    write(output / "selective_rejection_run.json", run)
    analysis = analyze_selective_rejection_experiment(
        corpus=corpus, preregistration=preregistration, run=run
    )
    write(output / "selective_rejection_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "pooled": analysis["pooled_contrast_metrics"],
        "composition": analysis["composition_metrics"],
        "replacement_gate": analysis["replacement_gate_metrics"],
        "selective": analysis["selective_rejection_metrics"],
        "conditions": analysis["conditions"],
        "tokens": analysis["physical_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
