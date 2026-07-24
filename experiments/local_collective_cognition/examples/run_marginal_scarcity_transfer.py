"""Run the frozen v0.59 transfer discovery and replacement gates."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.bounded_retry_provider import BoundedRetryProviderAdapter  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.marginal_scarcity_experiment import (  # noqa: E402
    run_discovery_panel,
)
from local_collective_cognition.marginal_scarcity_transfer import (  # noqa: E402
    analyze_transfer_discovery,
    analyze_transfer_replacement,
    run_transfer_replacement,
)
from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    validate_marginal_scarcity_transfer_holdout,
    validate_marginal_scarcity_transfer_holdout_v0_59_1,
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
    revision = os.environ.get("AGENTOS_TRANSFER_REVISION", "v0_59")
    if revision not in {"v0_59", "v0_59_1"}:
        raise ValueError("transfer_revision_invalid")
    runtime_version = f"marginal_scarcity_transfer_{revision}"
    corpus_validator = (
        validate_marginal_scarcity_transfer_holdout_v0_59_1
        if revision == "v0_59_1"
        else validate_marginal_scarcity_transfer_holdout
    )
    output = (
        REPO_ROOT / "outputs" / f"marginal_scarcity_transfer_{revision}"
    )
    corpus = read(output / "transfer_corpus_frozen.json")
    preregistration = read(output / "transfer_preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-marginal-scarcity-transfer-v0-59",
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
    discovery_run = run_discovery_panel(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        corpus_validator=corpus_validator,
        runtime_version=runtime_version,
    )
    write(output / "discovery_run.json", discovery_run)
    discovery_analysis = analyze_transfer_discovery(
        corpus=corpus,
        preregistration=preregistration,
        run=discovery_run,
        corpus_validator=corpus_validator,
        runtime_version=runtime_version,
    )
    write(output / "discovery_analysis.json", discovery_analysis)
    result = {
        "discovery_decision": discovery_analysis["decision"],
        "receipts": discovery_analysis["receipt_count"],
        "consensus": discovery_analysis["consensus_count"],
        "exact_target": discovery_analysis[
            "exact_target_consensus_count"
        ],
        "exact_target_and_drop": discovery_analysis[
            "exact_target_and_drop_consensus_count"
        ],
        "wrong_target": discovery_analysis[
            "wrong_target_consensus_count"
        ],
        "target_position_coverage": discovery_analysis[
            "target_source_position_coverage"
        ],
        "drop_pool_coverage": discovery_analysis["drop_pool_coverage"],
        "tokens": discovery_analysis["physical_total_tokens"],
    }
    if (
        discovery_analysis["decision"]
        == "PASS_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
    ):
        replacement_run = run_transfer_replacement(
            corpus=corpus,
            preregistration=preregistration,
            discovery_run=discovery_run,
            discovery_analysis=discovery_analysis,
            corpus_validator=corpus_validator,
            runtime_version=runtime_version,
        )
        write(output / "replacement_run.json", replacement_run)
        replacement_analysis = analyze_transfer_replacement(
            corpus=corpus,
            preregistration=preregistration,
            run=replacement_run,
            corpus_validator=corpus_validator,
            runtime_version=runtime_version,
        )
        write(output / "replacement_analysis.json", replacement_analysis)
        result.update({
            "replacement_decision": replacement_analysis["decision"],
            "replacements": replacement_analysis["replacement_count"],
            "abstentions": replacement_analysis["abstention_count"],
            "gross_mean": replacement_analysis[
                "realized_gross_cbit_mean"
            ],
            "harmful": replacement_analysis[
                "harmful_replacement_count"
            ],
            "protected_loss": replacement_analysis[
                "protected_knowledge_loss_count"
            ],
        })
    else:
        result["replacement_decision"] = "NOT_RUN_FAIL_CLOSED"
    print(json.dumps(
        {"revision": revision, **result}, indent=2, sort_keys=True
    ))


if __name__ == "__main__":
    raise SystemExit(main())
