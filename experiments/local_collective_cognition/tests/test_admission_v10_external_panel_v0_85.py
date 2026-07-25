import json
from pathlib import Path

from local_collective_cognition.admission_v10_external_panel import (
    build_external_panel,
    validate_external_panel,
)


ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "outputs" / "admission_v10_development_v0_85"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v085_external_panel_is_selective_blinded_and_deterministic():
    inputs = {
        "panel": read(SOURCE / "holdout_private.json"),
        "baseline_run": read(SOURCE / "baseline_run.json"),
        "atomic_run": read(SOURCE / "atomic_run.json"),
        "staged_run": read(SOURCE / "staged_run.json"),
        "candidate_run": read(SOURCE / "candidate_run.json"),
        "evaluation": read(SOURCE / "development_evaluation.json"),
    }
    packs, manifest = build_external_panel(**inputs)

    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=inputs,
    )
    assert manifest["case_count"] == 1
    assert manifest["span_count"] == 4
    assert manifest["selection_basis"] == "ALL_SPANS_FROM_MUTATED_CASES"
    assert manifest["selection_basis_exposed_to_annotators"] is False
    assert manifest["external_acceptance_eligible"] is False
    assert all(pack["selection_basis"] == "WITHHELD" for pack in packs)
