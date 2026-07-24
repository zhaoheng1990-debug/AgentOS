"""Run the frozen v0.57 target-blind discovery panel."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.marginal_scarcity_experiment import (  # noqa: E402
    analyze_discovery_panel,
    run_discovery_panel,
)
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
    output = REPO_ROOT / "outputs" / "marginal_scarcity_v0_57"
    corpus = read(output / "marginal_scarcity_corpus_frozen.json")
    prereg = read(output / "discovery_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-marginal-scarcity-v0-57",
            model_id="deepseek-v4-flash",
            endpoint="https://api.deepseek.com/chat/completions",
            api_key_env="DEEPSEEK_API_KEY",
            task_kinds=(TASK_KIND,),
            max_tokens=3200,
            timeout_seconds=300,
            extra_body={
                "thinking": {"type": "disabled"},
                "temperature": 0,
            },
        )),
        max_attempts=2,
        delay_seconds=1.0,
    )
    run = run_discovery_panel(
        corpus=corpus, preregistration=prereg, adapter=adapter
    )
    write(output / "discovery_run.json", run)
    analysis = analyze_discovery_panel(
        corpus=corpus, preregistration=prereg, run=run
    )
    write(output / "discovery_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "receipts": analysis["receipt_count"],
        "consensus": analysis["consensus_count"],
        "exact_target_consensus": analysis[
            "exact_target_consensus_count"
        ],
        "cross_replication_witnesses": analysis[
            "cross_replication_target_witness_count"
        ],
        "active_relation_proposals": analysis[
            "active_relation_proposal_count"
        ],
        "tokens": analysis["physical_total_tokens"],
        "failed": sorted(
            key for key, value in analysis["conditions"].items()
            if not value
        ),
        "formal_replacement_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
