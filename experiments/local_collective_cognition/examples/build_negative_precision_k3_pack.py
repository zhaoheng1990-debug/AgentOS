"""Validate v0.3 panel responses and build the blind K3 dispute pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_precision_holdout import validate_precision_corpus_artifact  # noqa: E402
from local_collective_cognition.structure_reference_panel_disagreement import (  # noqa: E402
    build_adjudication_bundle,
    validate_adjudication_bundle,
)
from local_collective_cognition.structure_reference_panel_pack import validate_reference_panel  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _write(path, payload):
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_precision_v0_3"
    parser.add_argument("--corpus", default=f"{base}/private_negative_precision_corpus.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_negative_precision_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_negative_precision_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    corpus = _load(args.corpus)
    validate_precision_corpus_artifact(corpus)
    packs = (_load(args.gpt_pack), _load(args.gemini_pack))
    panel_manifest = _load(args.panel_manifest)
    validate_reference_panel(packs=packs, manifest=panel_manifest, semantic_artifact=corpus)
    responses = (_load(args.gpt_response), _load(args.gemini_response))
    pack, manifest = build_adjudication_bundle(
        packs=packs, panel_manifest=panel_manifest, responses=responses,
    )
    validate_adjudication_bundle(
        pack=pack, manifest=manifest, panel_packs=packs,
        panel_manifest=panel_manifest, responses=responses,
    )
    output = _resolve(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    _write(output / "gpt_5_6_negative_precision_response.json", responses[0])
    _write(output / "gemini_3_1_negative_precision_response.json", responses[1])
    pack_path = output / "kimi_k3_negative_precision_adjudication_pack.json"
    _write(pack_path, pack)
    with ZipFile(pack_path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
        archive.write(pack_path, arcname=pack_path.name)
    _write(output / "private_adjudication_manifest.json", manifest)
    print(json.dumps({
        "agreement_count": manifest["agreement_count"],
        "disagreement_count": manifest["disagreement_count"],
        "reference_state": manifest["reference_state"],
        "adjudication_pack_hash": pack["pack_hash"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
