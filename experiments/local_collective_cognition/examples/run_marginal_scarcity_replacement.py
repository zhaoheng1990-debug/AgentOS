"""Freeze and run the v0.58 synthetic replacement gate."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.marginal_scarcity_replacement import (  # noqa: E402
    analyze_replacement_gate,
    build_replacement_preregistration,
    run_replacement_gate,
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
    prereg = build_replacement_preregistration(
        corpus=corpus,
        discovery_preregistration=read(
            output / "discovery_preregistration.json"
        ),
        discovery_run=read(output / "discovery_run.json"),
        discovery_analysis=read(output / "discovery_analysis.json"),
        discovery_closure=read(output / "closure.json"),
    )
    write(output / "replacement_preregistration.json", prereg)
    run = run_replacement_gate(
        corpus=corpus,
        preregistration=prereg,
        discovery_run=read(output / "discovery_run.json"),
    )
    write(output / "replacement_run.json", run)
    analysis = analyze_replacement_gate(
        corpus=corpus, preregistration=prereg, run=run
    )
    write(output / "replacement_analysis.json", analysis)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "replacements": analysis["replacement_count"],
        "abstentions": analysis["abstention_count"],
        "gross_mean": analysis["realized_gross_cbit_mean"],
        "harmful": analysis["harmful_replacement_count"],
        "protected_loss": analysis[
            "protected_knowledge_loss_count"
        ],
        "provider_calls": run["provider_calls_used"],
        "promotion_allowed": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
