"""Freeze v0.52 preregistration after the reference audit passes."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selective_rejection_experiment import (  # noqa: E402
    build_selective_rejection_preregistration,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def verify(value):
    commitment = {
        key: item for key, item in value.items()
        if key != "artifact_hash"
    }
    if value["artifact_hash"] != hash_payload(commitment):
        raise ValueError("source_hash_invalid")


def main():
    output = REPO_ROOT / "outputs" / "selective_rejection_v0_52"
    values = {
        name: read(output / filename)
        for name, filename in (
            ("corpus", "selective_rejection_corpus_frozen.json"),
            ("audit", "reference_completeness_audit.json"),
            ("prior_prereg", "source_v0_51_preregistration.json"),
            ("prior_analysis", "source_v0_51_analysis.json"),
            ("prior_closure", "source_v0_51_closure.json"),
            ("prior_posthoc", "source_v0_51_posthoc.json"),
        )
    }
    for value in values.values():
        verify(value)
    preregistration = build_selective_rejection_preregistration(
        corpus=values["corpus"],
        reference_audit=values["audit"],
        prior_preregistration=values["prior_prereg"],
        prior_analysis=values["prior_analysis"],
        prior_closure=values["prior_closure"],
        prior_posthoc=values["prior_posthoc"],
    )
    write(output / "selective_rejection_preregistration.json", preregistration)
    print(json.dumps({
        "corpus_hash": values["corpus"]["artifact_hash"],
        "reference_audit_hash": values["audit"]["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "soft_tokens": preregistration[
            "success_gate"
        ]["maximum_physical_total_tokens"],
        "hard_tokens": preregistration[
            "success_gate"
        ]["hard_runaway_total_tokens"],
        "formal_run_authorized": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
