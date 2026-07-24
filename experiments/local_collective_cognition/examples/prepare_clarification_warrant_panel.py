"""Create identity-blind GPT-5.6 and Gemini-3.1 warrant annotation packs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_warrant_holdout import validate_warrant_holdout_artifact
from local_collective_cognition.clarification_warrant_panel import build_warrant_panel, validate_warrant_panel


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_warrant_v0_10"
    parser.add_argument("--corpus", default=f"{base}/private_warrant_corpus.json")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    corpus = json.loads(resolve(args.corpus).read_text(encoding="utf-8"))
    validate_warrant_holdout_artifact(corpus)
    packs, manifest = build_warrant_panel(corpus_artifact=corpus)
    validate_warrant_panel(packs=packs, manifest=manifest, corpus_artifact=corpus)
    output = resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    names = {"annotation-lane-a": "gpt_5_6_warrant_semantics_pack.json", "annotation-lane-b": "gemini_3_1_warrant_semantics_pack.json"}
    for pack in packs:
        path = output / names[pack["lane_id"]]
        write(path, pack)
        with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
            archive.write(path, arcname=path.name)
    write(output / "private_warrant_panel_manifest.json", manifest)
    print(json.dumps({"panel_id": manifest["panel_id"], "pack_hashes": manifest["lane_pack_hashes"], "label_cells_expected": manifest["candidate_count"] * manifest["criterion_count"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
