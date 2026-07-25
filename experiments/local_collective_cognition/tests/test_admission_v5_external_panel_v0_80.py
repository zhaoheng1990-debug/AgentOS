import json
from pathlib import Path

from local_collective_cognition.admission_v5_external_panel import (
    validate_external_panel,
)


ROOT = Path(__file__).parents[3]
OUTPUT = ROOT / "outputs" / "admission_v5_external_panel_v0_80"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_v080_external_panel_is_blinded_and_disjoint():
    packs = (
        read(OUTPUT / "gpt_5_6_atomic_admission_pack_v0_80.json"),
        read(OUTPUT / "gemini_3_1_atomic_admission_pack_v0_80.json"),
    )
    manifest = read(OUTPUT / "panel_manifest_private.json")

    validate_external_panel(packs=packs, manifest=manifest)
    assert manifest["case_count"] == 12
    assert manifest["span_count"] >= 48
    assert manifest["candidate_outputs_exposed_to_annotators"] is False
    assert manifest["baseline_outputs_exposed_to_annotators"] is False
    assert manifest["benchmark_gold_exposed_to_annotators"] is False
    assert not (
        {item["annotation_id"] for item in packs[0]["items"]}
        & {item["annotation_id"] for item in packs[1]["items"]}
    )
