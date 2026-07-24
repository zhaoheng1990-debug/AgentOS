"""Run v0.54 decision-blind evidence-first arbitration."""

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
from local_collective_cognition.evidence_first_experiment import (  # noqa: E402
    analyze_evidence_first_experiment,
    run_evidence_first_experiment,
)
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    output = REPO_ROOT / "outputs" / "evidence_first_v0_54"
    corpus = read(output / "evidence_first_corpus_frozen.json")
    prereg = read(output / "evidence_first_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-evidence-first-v0-54",
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
    run = run_evidence_first_experiment(
        corpus=corpus,
        preregistration=prereg,
        adapter=adapter,
        base_checkpoint_callback=lambda value: write(
            output / "evidence_first_base_progress.json", value
        ),
        overlay_checkpoint_callback=lambda value: write(
            output / "evidence_first_overlay_progress.json", value
        ),
    )
    write(output / "evidence_first_run.json", run)
    analysis = analyze_evidence_first_experiment(
        corpus=corpus, preregistration=prereg, run=run
    )
    write(output / "evidence_first_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "context": analysis["context_qualification_metrics"],
        "blind": analysis["blind_evidence_metrics"],
        "composition": analysis["composition_metrics"],
        "replacement_gate": analysis["replacement_gate_metrics"],
        "failed_conditions": sorted(
            key for key, value in analysis["conditions"].items()
            if not value
        ),
        "tokens": analysis["physical_total_tokens"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
