"""Freeze v0.53 preregistration after reference audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.context_qualification_experiment import (  # noqa: E402
    build_context_qualification_preregistration,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


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
    output = REPO_ROOT / "outputs" / "context_qualification_v0_53"
    values = {
        name: read(output / filename)
        for name, filename in (
            ("corpus", "context_qualification_corpus_frozen.json"),
            ("audit", "reference_completeness_audit.json"),
            ("calibration", "unlabeled_qualification_calibration.json"),
            ("prior_prereg", "source_v0_52_preregistration.json"),
            ("prior_analysis", "source_v0_52_analysis.json"),
            ("prior_closure", "source_v0_52_closure.json"),
            ("prior_posthoc", "source_v0_52_posthoc.json"),
        )
    }
    for value in values.values():
        verify(value)
    prereg = build_context_qualification_preregistration(
        corpus=values["corpus"],
        reference_audit=values["audit"],
        calibration=values["calibration"],
        prior_preregistration=values["prior_prereg"],
        prior_analysis=values["prior_analysis"],
        prior_closure=values["prior_closure"],
        prior_posthoc=values["prior_posthoc"],
    )
    write(output / "context_qualification_preregistration.json", prereg)
    print(json.dumps({
        "corpus_hash": values["corpus"]["artifact_hash"],
        "reference_audit_hash": values["audit"]["artifact_hash"],
        "calibration_hash": values["calibration"]["artifact_hash"],
        "preregistration_hash": prereg["artifact_hash"],
        "minimum_qualified": prereg[
            "success_gate"
        ]["minimum_context_qualified_count"],
        "maximum_qualified": prereg[
            "success_gate"
        ]["maximum_context_qualified_count"],
        "soft_tokens": prereg[
            "success_gate"
        ]["maximum_physical_total_tokens"],
        "hard_tokens": prereg[
            "success_gate"
        ]["hard_runaway_total_tokens"],
        "formal_run_authorized": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
