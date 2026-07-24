"""Run the neutral v0.27 native-schema and partial-admission preflight."""

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
    analyze_frontier_preflight,
    run_frontier_batch,
)
from local_collective_cognition.frontier_fresh_holdout import (  # noqa: E402
    build_frontier_preflight,
)
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def adapter():
    return BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-frontier-preflight-v0-27",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=2200,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )


def main():
    output = REPO_ROOT / "outputs" / "frontier_preflight_v0_27"
    output.mkdir(parents=True, exist_ok=True)
    artifact = build_frontier_preflight()
    write(output / "preflight_corpus_frozen.json", artifact)
    run = run_frontier_batch(
        artifact=artifact,
        adapter=adapter(),
        mode="PREFLIGHT",
        checkpoint_callback=lambda value: write(
            output / "preflight_progress.json", value
        ),
    )
    analysis = analyze_frontier_preflight(artifact=artifact, run=run)
    write(output / "preflight_run.json", run)
    write(output / "preflight_analysis.json", analysis)
    closure_commitment = {
        "closure_version": "frontier_preflight_closure_v0_27",
        "source_corpus_hash": artifact["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "preflight_gate": analysis["preflight_gate"],
        "fresh_holdout_authorized": analysis[
            "fresh_holdout_authorized"
        ],
        "semantic_claim_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)
    print(json.dumps({
        "preflight_hash": artifact["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "conditions": analysis["conditions"],
        "total_tokens": analysis["total_tokens"],
        "average_tokens_per_task": analysis[
            "average_tokens_per_task"
        ],
        "recommended_fresh_holdout_token_budget": analysis[
            "recommended_fresh_holdout_token_budget"
        ],
        "preflight_gate": analysis["preflight_gate"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
