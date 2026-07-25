"""Generate independent GPT/Gemini annotation packs for v0.80."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v5_external_panel import (  # noqa: E402
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
    source = ROOT / "outputs" / "admission_v5_fresh_holdout_v0_80"
    output = ROOT / "outputs" / "admission_v5_external_panel_v0_80"
    output.mkdir(parents=True, exist_ok=True)
    inputs = {
        "panel": read(source / "holdout_private.json"),
        "baseline_run": read(source / "baseline_run.json"),
        "candidate_run": read(source / "candidate_run.json"),
        "evaluation": read(source / "pre_reference_evaluation.json"),
    }
    packs, manifest = build_external_panel(**inputs)
    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=inputs,
    )
    filenames = {
        "ANNOTATION_LANE_A": "gpt_5_6_atomic_admission_pack_v0_80.json",
        "ANNOTATION_LANE_B": "gemini_3_1_atomic_admission_pack_v0_80.json",
    }
    readme = (
        "AgentOS atomic witness typed annotation v0.80\n\n"
        "Give exactly one lane pack to its expected annotator. Do not expose "
        "the peer pack, benchmark gold, baseline/candidate outputs, or prior "
        "scores. Return one JSON object satisfying the embedded response "
        "contract. Assess every span independently.\n"
    )
    readme_path = output / "ANNOTATION_INSTRUCTIONS.txt"
    readme_path.write_text(readme, encoding="utf-8")
    for pack in packs:
        filename = filenames[pack["lane_id"]]
        pack_path = output / filename
        write(pack_path, pack)
        zip_name = (
            "GPT5_6_Atomic_Admission_Annotation_v0_80.zip"
            if pack["lane_id"] == "ANNOTATION_LANE_A"
            else "Gemini3_1_Atomic_Admission_Annotation_v0_80.zip"
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
    write(output / "panel_manifest_public.json", {
        key: value for key, value in manifest.items()
        if key != "private_lane_bindings"
    })
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
        "gpt_zip": str(
            output / "GPT5_6_Atomic_Admission_Annotation_v0_80.zip"
        ),
        "gemini_zip": str(
            output / "Gemini3_1_Atomic_Admission_Annotation_v0_80.zip"
        ),
        "candidate_outputs_exposed": False,
        "baseline_outputs_exposed": False,
        "benchmark_gold_exposed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
