"""Freeze v0.53 corpus, prior artifacts, and unlabeled calibration."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.context_qualification_holdout import (  # noqa: E402
    build_context_qualification_holdout,
)
from local_collective_cognition.context_qualification_policy import (  # noqa: E402
    audit_context_qualification_calibration,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def verify(value, hash_field="artifact_hash"):
    commitment = {
        key: item for key, item in value.items() if key != hash_field
    }
    if value[hash_field] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    v51 = REPO_ROOT / "outputs" / "reference_complete_portfolio_v0_51"
    v52 = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    corpus51 = read(v51 / "reference_complete_portfolio_corpus_frozen.json")
    run51 = read(v51 / "reference_complete_portfolio_run.json")
    corpus52 = read(v52 / "selective_rejection_corpus_frozen.json")
    run52 = read(v52 / "selective_rejection_run.json")
    prior_prereg = read(v52 / "selective_rejection_preregistration.json")
    prior_analysis = read(v52 / "selective_rejection_analysis.json")
    prior_closure = read(v52 / "closure.json")
    prior_posthoc = read(v52 / "posthoc_selective_rejection.json")
    for value in (
        corpus51, corpus52, prior_prereg, prior_analysis,
        prior_closure, prior_posthoc,
    ):
        verify(value)
    verify(run51, "run_hash")
    verify(run52, "run_hash")
    calibration = audit_context_qualification_calibration(
        sources=(
            ("V0_51", corpus51, run51),
            ("V0_52", corpus52, run52),
        )
    )
    corpus = build_context_qualification_holdout()
    output = REPO_ROOT / "outputs" / "context_qualification_v0_53"
    output.mkdir(parents=True, exist_ok=True)
    for name, value in (
        ("source_v0_52_preregistration.json", prior_prereg),
        ("source_v0_52_analysis.json", prior_analysis),
        ("source_v0_52_closure.json", prior_closure),
        ("source_v0_52_posthoc.json", prior_posthoc),
        ("unlabeled_qualification_calibration.json", calibration),
        ("context_qualification_corpus_frozen.json", corpus),
    ):
        write(output / name, value)
    print(json.dumps({
        "corpus_hash": corpus["artifact_hash"],
        "calibration_hash": calibration["artifact_hash"],
        "source_metrics": {
            key: {
                "old": value["old_qualified_count"],
                "new": value["new_qualified_count"],
                "rate": value["new_qualification_rate"],
            }
            for key, value in calibration["source_metrics"].items()
        },
        "basis": calibration["qualification_basis_distribution"],
        "cross_source_rate_range": calibration[
            "cross_source_rate_range"
        ],
        "private_outcomes_accessed": calibration[
            "private_outcomes_accessed"
        ],
        "formal_run_authorized": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
