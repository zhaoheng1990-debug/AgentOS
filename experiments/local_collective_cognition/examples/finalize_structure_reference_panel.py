"""Finalize the candidate-only model-panel reference artifact."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_reference_panel_final import (  # noqa: E402
    build_reference_candidate, validate_reference_candidate,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _load_bundle_response(path):
    matches = []
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            raw = archive.read(info)
            payload = json.loads(raw.decode("utf-8-sig"))
            if {"adjudication_pack_hash", "blinding_attestation", "decisions"}.issubset(payload):
                matches.append((raw, payload))
    if len(matches) != 1:
        raise ValueError("reference_adjudication_bundle_response_surface_invalid")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/structure_reference_panel_v0_1"
    parser.add_argument("--adjudication-pack", default=f"{base}/kimi_k3_adjudication_pack.json")
    parser.add_argument("--private-adjudication-manifest", default=f"{base}/private_adjudication_manifest.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_annotation_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_annotation_pack.json")
    parser.add_argument("--private-panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", default=f"{base}/gpt_5_6_annotation_response.json")
    parser.add_argument("--gemini-response", default=f"{base}/gemini_3_1_annotation_response.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--k3-response")
    source.add_argument("--k3-bundle")
    parser.add_argument("--output", default=f"{base}/model_panel_reference_candidate.json")
    args = parser.parse_args()
    pack, manifest = _load(args.adjudication_pack), _load(args.private_adjudication_manifest)
    bundle = _resolve(args.k3_bundle) if args.k3_bundle else None
    if bundle:
        response_raw, response = _load_bundle_response(bundle)
    else:
        response_path = _resolve(args.k3_response)
        response_raw, response = response_path.read_bytes(), _load(response_path)
    panel_packs = (_load(args.gpt_pack), _load(args.gemini_pack))
    panel_manifest = _load(args.private_panel_manifest)
    annotation_responses = (_load(args.gpt_response), _load(args.gemini_response))
    artifact = build_reference_candidate(
        adjudication_pack=pack, adjudication_manifest=manifest,
        panel_packs=panel_packs, panel_manifest=panel_manifest,
        annotation_responses=annotation_responses, response=response,
    )
    validate_reference_candidate(
        artifact, adjudication_pack=pack, adjudication_manifest=manifest,
        panel_packs=panel_packs, panel_manifest=panel_manifest,
        annotation_responses=annotation_responses, response=response,
    )
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    (output.parent / "kimi_k3_blind_adjudication_response.json").write_bytes(response_raw)
    if bundle:
        shutil.copyfile(bundle, output.parent / "source_kimi_blind_adjudication_bundle.zip")
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": artifact["candidate_state"], "label_count": artifact["label_count"],
        "uncertain_label_count": artifact["uncertain_label_count"],
        "artifact_hash": artifact["artifact_hash"], "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
