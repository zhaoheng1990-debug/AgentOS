import json
from pathlib import Path

from local_collective_cognition.admission_v5_external_panel import (
    validate_external_panel,
)
from local_collective_cognition.admission_v5_external_adjudication import (
    validate_adjudication,
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


def test_v080_adjudication_pack_is_anonymous_and_complete():
    pack = read(OUTPUT / "kimi_k3_atomic_admission_pack_v0_80.json")
    manifest = read(OUTPUT / "adjudication_manifest_private.json")

    validate_adjudication(pack=pack, manifest=manifest)
    assert manifest["agreement_count"] == 37
    assert manifest["disagreement_count"] == 11
    assert manifest["total_span_count"] == 48
    assert manifest["reference_state"] == (
        "AWAITING_KIMI_K3_TYPED_ADJUDICATION"
    )
    assert pack["annotator_identity"] == "WITHHELD"
    assert pack["benchmark_gold"] == "WITHHELD"
    assert pack["baseline_system_outputs"] == "WITHHELD"
    assert pack["candidate_system_outputs"] == "WITHHELD"
