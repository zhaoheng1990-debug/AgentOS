import json
from pathlib import Path

from local_collective_cognition.admission_v7_external_panel import (
    build_external_panel,
    validate_external_panel,
)


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "outputs" / "admission_v7_fresh_holdout_v0_82"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v082_external_panel_is_complete_blinded_and_deterministic():
    inputs = {
        "panel": read(SOURCE / "holdout_private.json"),
        "baseline_run": read(SOURCE / "baseline_run.json"),
        "atomic_run": read(SOURCE / "atomic_run.json"),
        "candidate_run": read(SOURCE / "candidate_run.json"),
        "evaluation": read(SOURCE / "pre_reference_evaluation.json"),
    }
    packs, manifest = build_external_panel(**inputs)

    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=inputs,
    )
    assert manifest["span_count"] == 48
    assert all(pack["benchmark_gold"] == "WITHHELD" for pack in packs)
    assert all(
        pack["baseline_system_outputs"] == "WITHHELD"
        and pack["atomic_system_outputs"] == "WITHHELD"
        and pack["candidate_system_outputs"] == "WITHHELD"
        for pack in packs
    )
