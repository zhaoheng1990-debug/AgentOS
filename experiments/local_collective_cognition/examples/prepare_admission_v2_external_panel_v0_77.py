"""Generate independent GPT/Gemini Admission V2 annotation packs."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v2_external_panel import (  # noqa: E402
    build_external_panel,
    validate_external_panel,
)


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main():
    source = ROOT / "outputs" / "admission_v2_v0_76"
    output = ROOT / "outputs" / "admission_v2_external_panel_v0_77"
    output.mkdir(parents=True, exist_ok=True)
    inputs = {
        "panel": read(source / "calibration_private.json"),
        "run": read(source / "calibration_candidate_run.json"),
        "score": read(source / "calibration_score.json"),
        "decision": read(source / "calibration_decision.json"),
    }
    packs, manifest = build_external_panel(**inputs)
    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=inputs,
    )
    filenames = {
        "ANNOTATION_LANE_A": "gpt_5_6_typed_admission_pack_v0_77.json",
        "ANNOTATION_LANE_B": "gemini_3_1_typed_admission_pack_v0_77.json",
    }
    readme = (
        "AgentOS Admission V2 typed annotation v0.77\n\n"
        "Give exactly one lane pack to its expected annotator.\n"
        "Do not expose the peer pack, benchmark gold, candidate outputs, "
        "or prior scores.\n"
        "The annotator must return one JSON object satisfying the embedded "
        "response_contract. Every span is assessed independently; a more "
        "concise sibling must not demote valid corroborating evidence.\n"
    )
    readme_path = output / "ANNOTATION_INSTRUCTIONS.txt"
    readme_path.write_text(readme, encoding="utf-8")
    for pack in packs:
        filename = filenames[pack["lane_id"]]
        pack_path = output / filename
        write(pack_path, pack)
        zip_name = (
            "GPT5_6_Admission_V2_Annotation_v0_77.zip"
            if pack["lane_id"] == "ANNOTATION_LANE_A"
            else "Gemini3_1_Admission_V2_Annotation_v0_77.zip"
        )
        with zipfile.ZipFile(
            output / zip_name,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.write(pack_path, arcname=filename)
            archive.write(
                readme_path,
                arcname="ANNOTATION_INSTRUCTIONS.txt",
            )
    write(output / "panel_manifest_private.json", manifest)
    public_manifest = {
        key: value
        for key, value in manifest.items()
        if key != "private_lane_bindings"
    }
    write(output / "panel_manifest_public.json", public_manifest)
    inventory = {
        path.name: {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "size": path.stat().st_size,
        }
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "hash_inventory.json"
    }
    write(output / "hash_inventory.json", inventory)
    print(json.dumps({
        "panel_id": manifest["panel_id"],
        "case_count": manifest["case_count"],
        "span_count": manifest["span_count"],
        "lane_pack_hashes": manifest["lane_pack_hashes"],
        "output": str(output),
        "gpt_zip": str(
            output / "GPT5_6_Admission_V2_Annotation_v0_77.zip"
        ),
        "gemini_zip": str(
            output / "Gemini3_1_Admission_V2_Annotation_v0_77.zip"
        ),
        "candidate_outputs_exposed": False,
        "benchmark_gold_exposed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
