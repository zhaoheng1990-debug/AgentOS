"""Build the identity-blind v0.5 K3 dispute pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_warrant_holdout import validate_warrant_corpus_artifact
from local_collective_cognition.structure_reference_panel_disagreement import build_adjudication_bundle, validate_adjudication_bundle
from local_collective_cognition.structure_reference_panel_pack import validate_reference_panel


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_warrant_v0_5_1"
    parser.add_argument("--corpus", default=f"{base}/private_negative_warrant_corpus.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_negative_warrant_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_negative_warrant_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    corpus = load(args.corpus)
    validate_warrant_corpus_artifact(corpus)
    packs = (load(args.gpt_pack), load(args.gemini_pack))
    manifest = load(args.panel_manifest)
    validate_reference_panel(packs=packs, manifest=manifest, semantic_artifact=corpus)
    responses = (load(args.gpt_response), load(args.gemini_response))
    pack, private = build_adjudication_bundle(packs=packs, panel_manifest=manifest, responses=responses)
    validate_adjudication_bundle(pack=pack, manifest=private, panel_packs=packs, panel_manifest=manifest, responses=responses)
    output_dir = resolve(args.output_dir)
    write(output_dir / "gpt_5_6_negative_warrant_response.json", responses[0])
    write(output_dir / "gemini_3_1_negative_warrant_response.json", responses[1])
    path = output_dir / "kimi_k3_negative_warrant_adjudication_pack.json"
    write(path, pack)
    with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
        archive.write(path, arcname=path.name)
    write(output_dir / "private_adjudication_manifest.json", private)
    print(json.dumps({
        "agreement_count": private["agreement_count"],
        "disagreement_count": private["disagreement_count"],
        "reference_state": private["reference_state"],
        "pack_hash": pack["pack_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
