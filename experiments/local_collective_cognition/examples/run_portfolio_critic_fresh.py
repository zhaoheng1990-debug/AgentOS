"""Run v0.61 target-only discovery and selective Kernel actions."""

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
from local_collective_cognition.openai_compatible_provider import (  # noqa: E402
    OpenAICompatibleJsonAdapter,
    OpenAICompatibleProviderSpec,
)
from local_collective_cognition.portfolio_critic_calibration import (  # noqa: E402
    build_portfolio_critic_receipts,
)
from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    validate_portfolio_critic_fresh_holdout,
    validate_portfolio_critic_fresh_holdout_v0_61_1,
)
from local_collective_cognition.portfolio_critic_fresh_runtime import (  # noqa: E402
    analyze_fresh_kernel_actions,
    run_fresh_kernel_actions,
)
from local_collective_cognition.portfolio_target_discovery import (  # noqa: E402
    analyze_target_discovery,
    run_target_discovery,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    revision = os.environ.get("AGENTOS_PORTFOLIO_REVISION", "v0_61")
    if revision not in {"v0_61", "v0_61_1"}:
        raise ValueError("portfolio_revision_invalid")
    validator = (
        validate_portfolio_critic_fresh_holdout_v0_61_1
        if revision == "v0_61_1"
        else validate_portfolio_critic_fresh_holdout
    )
    runtime_version = f"portfolio_critic_fresh_runtime_{revision}"
    target_runtime_version = f"portfolio_target_discovery_{revision}"
    output = (
        REPO_ROOT / "outputs" / f"portfolio_critic_fresh_{revision}"
    )
    corpus = read(output / "fresh_corpus_frozen.json")
    reference = read(output / "reference_completeness_audit.json")
    preregistration = read(output / "preregistration.json")
    adapter = BoundedRetryProviderAdapter(
        OpenAICompatibleJsonAdapter(OpenAICompatibleProviderSpec(
            provider_id="deepseek-portfolio-target-only-v0-61",
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
    target_run = run_target_discovery(
        corpus=corpus,
        preregistration=preregistration,
        adapter=adapter,
        corpus_validator=validator,
        runtime_version=target_runtime_version,
    )
    write(output / "target_discovery_run.json", target_run)
    target_analysis = analyze_target_discovery(
        corpus=corpus,
        preregistration=preregistration,
        run=target_run,
        corpus_validator=validator,
        runtime_version=target_runtime_version,
    )
    write(output / "target_discovery_analysis.json", target_analysis)
    result = {
        "target_decision": target_analysis["decision"],
        "target_receipts": target_analysis["receipt_count"],
        "target_consensus": target_analysis["consensus_count"],
        "exact_target": target_analysis["exact_target_consensus_count"],
        "wrong_target": target_analysis["wrong_target_consensus_count"],
        "target_position_coverage": target_analysis[
            "target_position_coverage"
        ],
        "target_tokens": target_analysis["physical_total_tokens"],
    }
    if target_analysis["decision"] == "PASS_FRESH_TARGET_ONLY_DISCOVERY":
        critic = build_portfolio_critic_receipts(
            corpus=corpus,
            reference_audit=reference,
            preregistration=preregistration,
            corpus_validator=validator,
            runtime_version=runtime_version,
        )
        write(output / "portfolio_critic_receipts.json", critic)
        action_run = run_fresh_kernel_actions(
            corpus=corpus,
            preregistration=preregistration,
            target_run=target_run,
            target_analysis=target_analysis,
            critic_artifact=critic,
            corpus_validator=validator,
            runtime_version=runtime_version,
        )
        write(output / "kernel_action_run.json", action_run)
        action_analysis = analyze_fresh_kernel_actions(
            corpus=corpus,
            preregistration=preregistration,
            run=action_run,
            corpus_validator=validator,
            runtime_version=runtime_version,
        )
        write(output / "kernel_action_analysis.json", action_analysis)
        result.update({
            "action_decision": action_analysis["decision"],
            "unique_replacements": action_analysis[
                "unique_replacement_count"
            ],
            "no_eligible_abstentions": action_analysis[
                "no_eligible_abstention_count"
            ],
            "ambiguous_abstentions": action_analysis[
                "ambiguous_abstention_count"
            ],
            "target_nonconsensus": action_analysis[
                "target_nonconsensus_count"
            ],
            "harmful": action_analysis[
                "harmful_replacement_count"
            ],
            "protected_loss": action_analysis[
                "protected_knowledge_loss_count"
            ],
            "fresh_generalization_supported": action_analysis[
                "fresh_generalization_supported"
            ],
        })
    else:
        result["action_decision"] = "NOT_RUN_FAIL_CLOSED"
    print(json.dumps(
        {"revision": revision, **result}, indent=2, sort_keys=True
    ))


if __name__ == "__main__":
    raise SystemExit(main())
