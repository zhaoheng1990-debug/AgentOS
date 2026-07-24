"""Freeze the v0.30 provider-backed selective role-routing experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_role_routing_experiment import (  # noqa: E402
    build_routing_preregistration,
)
from local_collective_cognition.selective_role_routing_holdout import (  # noqa: E402
    build_selective_role_routing_holdout,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def verify_hash(artifact):
    commitment = {
        key: value for key, value in artifact.items()
        if key != "artifact_hash"
    }
    if artifact.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("source_artifact_hash_invalid")


def main():
    prior_output = (
        REPO_ROOT / "outputs" / "collaborative_stability_v0_29"
    )
    prior_analysis = read(
        prior_output / "collaborative_stability_analysis.json"
    )
    prior_posthoc = read(
        prior_output / "posthoc_routing_diagnostics.json"
    )
    prior_ledger = read(prior_output / "ledger.json")
    prior_closure = read(prior_output / "closure.json")
    for artifact in (
        prior_analysis, prior_posthoc, prior_ledger, prior_closure
    ):
        verify_hash(artifact)
    if (
        prior_ledger.get("source_analysis_hash")
        != prior_analysis["artifact_hash"]
        or prior_closure.get("source_ledger_hash")
        != prior_ledger["artifact_hash"]
    ):
        raise ValueError("v0_29_source_chain_invalid")

    corpus = build_selective_role_routing_holdout()
    preregistration = build_routing_preregistration(
        corpus=corpus,
        prior_analysis=prior_analysis,
        prior_closure=prior_closure,
        prior_posthoc=prior_posthoc,
    )
    output = REPO_ROOT / "outputs" / "selective_role_routing_v0_30"
    output.mkdir(parents=True, exist_ok=True)
    write(output / "source_v0_29_analysis.json", prior_analysis)
    write(output / "source_v0_29_posthoc.json", prior_posthoc)
    write(output / "source_v0_29_closure.json", prior_closure)
    write(
        output / "selective_role_routing_corpus_frozen.json",
        corpus,
    )
    write(
        output / "selective_role_routing_preregistration.json",
        preregistration,
    )
    print(json.dumps({
        "prior_analysis_hash": prior_analysis["artifact_hash"],
        "prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "prior_closure_hash": prior_closure["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": corpus["case_count"],
        "replication_count": len(corpus["replication_ids"]),
        "route_count": len(preregistration["route_ids"]),
        "expected_task_call_count": 120,
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
