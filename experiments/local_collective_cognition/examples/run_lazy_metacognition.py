"""Run v0.32 receipt-native lazy metacognition experiment."""

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
)
from local_collective_cognition.lazy_metacognition_experiment import (  # noqa: E402
    analyze_lazy_metacognition_experiment,
    run_lazy_metacognition_experiment,
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
    output = REPO_ROOT / "outputs" / "lazy_metacognition_v0_32"
    corpus = read(output / "lazy_metacognition_corpus_frozen.json")
    preregistration = read(
        output / "lazy_metacognition_preregistration.json"
    )
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-lazy-metacognition-v0-32",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=3000,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run = run_lazy_metacognition_experiment(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        checkpoint_callback=lambda value: write(
            output / "lazy_metacognition_progress.json",
            value,
        ),
    )
    analysis = analyze_lazy_metacognition_experiment(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    write(output / "lazy_metacognition_run.json", run)
    write(output / "lazy_metacognition_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "metrics": analysis["pooled_contrast_metrics"],
        "triggers": analysis["trigger_metrics"],
        "conditions": analysis["conditions"],
        "tokens": analysis["physical_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
