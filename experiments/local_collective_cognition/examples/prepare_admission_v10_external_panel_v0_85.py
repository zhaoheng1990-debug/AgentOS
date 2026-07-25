"""Generate selective GPT/Gemini annotation packs for v0.85."""

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.admission_v10_external_panel import (  # noqa: E402
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
    source = ROOT / "outputs" / "admission_v10_development_v0_85"
    output = ROOT / "outputs" / "admission_v10_external_panel_v0_85"
    output.mkdir(parents=True, exist_ok=True)
    inputs = {
        "panel": read(source / "holdout_private.json"),
        "baseline_run": read(source / "baseline_run.json"),
        "atomic_run": read(source / "atomic_run.json"),
        "staged_run": read(source / "staged_run.json"),
        "candidate_run": read(source / "candidate_run.json"),
        "evaluation": read(source / "development_evaluation.json"),
    }
    packs, manifest = build_external_panel(**inputs)
    validate_external_panel(
        packs=packs,
        manifest=manifest,
        source_inputs=inputs,
    )
    filenames = {
        "ANNOTATION_LANE_A": "gpt_5_6_study_relation_pack_v0_85.json",
        "ANNOTATION_LANE_B": "gemini_3_1_study_relation_pack_v0_85.json",
    }
    instructions = (
        "AgentOS study-relation mutation-case annotation v0.85\n\n"
        "Give exactly one lane pack to its expected annotator. Do not expose "
        "the peer pack, benchmark gold, selection basis, or system outputs. "
        "Return one JSON object satisfying the embedded response contract. "
        "Assess all supplied spans independently.\n"
    )
    instructions_path = output / "ANNOTATION_INSTRUCTIONS.txt"
    instructions_path.write_text(instructions, encoding="utf-8")
    for pack in packs:
        filename = filenames[pack["lane_id"]]
        pack_path = output / filename
        write(pack_path, pack)
        zip_name = (
            "GPT5_6_Study_Relation_Admission_v0_85.zip"
            if pack["lane_id"] == "ANNOTATION_LANE_A"
            else "Gemini3_1_Study_Relation_Admission_v0_85.zip"
        )
        with zipfile.ZipFile(
            output / zip_name,
            "w",
            compression=zipfile.ZIP_DEFLATED,
        ) as archive:
            archive.write(pack_path, arcname=filename)
            archive.write(
                instructions_path,
                arcname="ANNOTATION_INSTRUCTIONS.txt",
            )
    write(output / "panel_manifest_private.json", manifest)
    write(output / "panel_manifest_public.json", {
        key: value for key, value in manifest.items()
        if key not in {
            "private_lane_bindings",
            "private_selected_case_ids",
        }
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
            output / "GPT5_6_Study_Relation_Admission_v0_85.zip"
        ),
        "gemini_zip": str(
            output / "Gemini3_1_Study_Relation_Admission_v0_85.zip"
        ),
        "selection_basis_exposed": False,
        "system_outputs_exposed": False,
        "external_acceptance_eligible": False,
    }, indent=2))


if __name__ == "__main__":
    main()
