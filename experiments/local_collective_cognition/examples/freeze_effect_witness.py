"""Freeze v0.56 preregistration."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.effect_witness_experiment import build_effect_witness_preregistration  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    output = REPO_ROOT / "outputs" / "effect_witness_v0_56"
    prereg = build_effect_witness_preregistration(
        corpus=read(output / "effect_witness_corpus_frozen.json"),
        reference_audit=read(output / "reference_completeness_audit.json"),
        prior_preregistration=read(output / "source_v0_54_preregistration.json"),
        prior_analysis=read(output / "source_v0_54_analysis.json"),
        prior_closure=read(output / "source_v0_54_closure.json"),
        prior_posthoc=read(output / "source_v0_54_posthoc.json"),
        stability_closure=read(output / "source_v0_55_closure.json"),
        gate_candidate=read(output / "source_dual_axis_gate_candidate.json"),
    )
    write(output / "effect_witness_preregistration.json", prereg)
    print(json.dumps({
        "preregistration_hash": prereg["artifact_hash"],
        "minimum_effect_acceptance": prereg["success_gate"]["minimum_effect_lane_acceptance_count"],
        "soft_tokens": prereg["success_gate"]["maximum_physical_total_tokens"],
        "hard_tokens": prereg["success_gate"]["hard_runaway_total_tokens"],
        "formal_run_authorized": True,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
