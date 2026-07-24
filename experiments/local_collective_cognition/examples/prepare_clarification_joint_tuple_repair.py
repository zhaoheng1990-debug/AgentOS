"""Build the identity-blind v0.14 Kimi-K3 full-tuple repair pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_tuple_repair import (  # noqa: E402
    build_joint_tuple_repair_pack,
    validate_joint_tuple_repair_pack,
)


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-dir", default="outputs/clarification_joint_fresh_v0_13")
    parser.add_argument("--output-dir", default="outputs/clarification_joint_tuple_repair_v0_14")
    args = parser.parse_args()
    source = resolve(args.source_dir)
    output = resolve(args.output_dir)
    source_inputs = {
        "corpus_artifact": read(source / "private_joint_corpus.json"),
        "panel_packs": (
            read(source / "gpt_5_6_joint_fresh_pack.json"),
            read(source / "gemini_3_1_joint_fresh_pack.json"),
        ),
        "panel_manifest": read(source / "private_joint_fresh_panel_manifest.json"),
        "panel_responses": (
            read(source / "gpt_5_6_joint_fresh_response.json"),
            read(source / "gemini_3_1_joint_fresh_response.json"),
        ),
        "cell_adjudication_pack": read(source / "kimi_k3_joint_fresh_adjudication_pack.json"),
        "cell_adjudication_manifest": read(source / "private_joint_fresh_adjudication_manifest.json"),
        "cell_adjudication_response": read(source / "kimi_k3_joint_fresh_response.json"),
        "panel_reference": read(source / "joint_fresh_model_panel_reference_candidate.json"),
    }
    pack, manifest = build_joint_tuple_repair_pack(**source_inputs)
    validate_joint_tuple_repair_pack(pack=pack, manifest=manifest, source_inputs=source_inputs)
    output.mkdir(parents=True, exist_ok=True)
    pack_path = output / "kimi_k3_joint_tuple_repair_pack.json"
    write(pack_path, pack)
    write(output / "private_joint_tuple_repair_manifest.json", manifest)
    zip_path = output / "kimi_k3_joint_tuple_repair_pack.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(pack_path, arcname=pack_path.name)
    print(json.dumps({
        "repair_count": manifest["repair_count"],
        "pack_hash": pack["pack_hash"],
        "reference_state": manifest["reference_state"],
        "zip_path": str(zip_path),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
