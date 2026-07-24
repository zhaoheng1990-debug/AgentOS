"""Run the zero-new-call v0.60 PortfolioCritic calibration."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.portfolio_critic_calibration import (  # noqa: E402
    analyze_kernel_displacement,
    build_portfolio_critic_preregistration,
    build_portfolio_critic_receipts,
    run_kernel_displacement,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main():
    source = (
        REPO_ROOT / "outputs" / "marginal_scarcity_transfer_v0_59_1"
    )
    output = (
        REPO_ROOT / "outputs" / "portfolio_critic_calibration_v0_60"
    )
    output.mkdir(parents=True, exist_ok=True)
    corpus = read(source / "transfer_corpus_frozen.json")
    reference = read(source / "reference_completeness_audit.json")
    discovery_run = read(source / "discovery_run.json")
    discovery_analysis = read(source / "discovery_analysis.json")
    discovery_closure = read(source / "closure.json")
    preregistration = build_portfolio_critic_preregistration(
        corpus=corpus,
        reference_audit=reference,
        discovery_run=discovery_run,
        discovery_analysis=discovery_analysis,
        discovery_closure=discovery_closure,
    )
    write(output / "preregistration.json", preregistration)
    critic = build_portfolio_critic_receipts(
        corpus=corpus,
        reference_audit=reference,
        preregistration=preregistration,
    )
    write(output / "portfolio_critic_receipts.json", critic)
    run = run_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        discovery_run=discovery_run,
        critic_artifact=critic,
    )
    write(output / "kernel_displacement_run.json", run)
    analysis = analyze_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    write(output / "analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "replacements": analysis["replacement_count"],
        "abstentions": analysis["abstention_count"],
        "corrective_overrides": analysis["corrective_override_count"],
        "target_position_coverage": analysis[
            "target_position_coverage"
        ],
        "drop_pool_coverage": analysis["drop_pool_coverage"],
        "gross_mean": analysis["realized_gross_cbit_mean"],
        "harmful": analysis["harmful_replacement_count"],
        "protected_loss": analysis[
            "protected_knowledge_loss_count"
        ],
        "critic_conflicts": analysis["critic_conflict_count"],
        "provider_calls_added": run["provider_calls_used"],
        "fresh_generalization_claim": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
