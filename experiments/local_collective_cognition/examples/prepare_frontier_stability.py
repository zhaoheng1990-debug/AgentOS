"""Freeze the v0.28 two-replication frontier stability experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.frontier_stability_experiment import (  # noqa: E402
    build_stability_preregistration,
)
from local_collective_cognition.frontier_stability_holdout import (  # noqa: E402
    build_frontier_stability_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def verify_hash(artifact, field):
    commitment = {key: value for key, value in artifact.items() if key != field}
    if artifact.get(field) != hash_payload(commitment):
        raise ValueError(f"source_artifact_hash_invalid:{field}")


def main():
    prior_output = REPO_ROOT / "outputs" / "frontier_fresh_v0_27"
    prior_analysis = read(prior_output / "frontier_analysis.json")
    prior_ledger = read(prior_output / "ledger.json")
    prior_closure = read(prior_output / "closure.json")
    verify_hash(prior_analysis, "artifact_hash")
    verify_hash(prior_ledger, "artifact_hash")
    verify_hash(prior_closure, "artifact_hash")
    if (
        prior_ledger.get("source_analysis_hash")
        != prior_analysis["artifact_hash"]
        or prior_closure.get("source_ledger_hash")
        != prior_ledger["artifact_hash"]
    ):
        raise ValueError("v0_27_source_chain_invalid")

    corpus = build_frontier_stability_holdout()
    preregistration = build_stability_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
    )
    output = REPO_ROOT / "outputs" / "frontier_stability_v0_28"
    output.mkdir(parents=True, exist_ok=True)
    write(output / "source_v0_27_analysis.json", prior_analysis)
    write(output / "source_v0_27_closure.json", prior_closure)
    write(output / "frontier_stability_corpus_frozen.json", corpus)
    write(
        output / "frontier_stability_preregistration.json",
        preregistration,
    )
    print(json.dumps({
        "prior_analysis_hash": prior_analysis["artifact_hash"],
        "prior_closure_hash": prior_closure["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "replication_count": len(corpus["replication_ids"]),
        "task_call_count": (
            corpus["case_count"] * len(corpus["replication_ids"]) * 2
        ),
        "soft_expected_total_tokens": preregistration[
            "cost_policy"
        ]["soft_expected_total_tokens"],
        "hard_runaway_total_tokens": preregistration[
            "cost_policy"
        ]["hard_runaway_total_tokens"],
        "reference_state": corpus["reference_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
