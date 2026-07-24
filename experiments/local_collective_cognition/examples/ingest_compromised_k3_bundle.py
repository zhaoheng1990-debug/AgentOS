"""Ingest the disclosed context-compromised K3 response from a ZIP bundle."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
import shutil
import sys
from pathlib import Path
from zipfile import ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.structure_reference_panel_compromised import (  # noqa: E402
    build_compromised_shadow,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _response_entry(bundle):
    matches = []
    with ZipFile(bundle) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            raw = archive.read(info)
            payload = json.loads(raw.decode("utf-8-sig"))
            if {"adjudication_pack_hash", "blinding_attestation", "decisions"}.issubset(payload):
                matches.append((raw, payload))
    if len(matches) != 1:
        raise ValueError("compromised_k3_bundle_response_surface_invalid")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/structure_reference_panel_v0_1"
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    bundle, output = _resolve(args.bundle), _resolve(args.output_dir)
    raw, response = _response_entry(bundle)
    packs = (_load(f"{base}/gpt_5_6_annotation_pack.json"), _load(f"{base}/gemini_3_1_annotation_pack.json"))
    responses = (_load(f"{base}/gpt_5_6_annotation_response.json"), _load(f"{base}/gemini_3_1_annotation_response.json"))
    artifact = build_compromised_shadow(
        response=response, source_zip_sha256=sha256(bundle.read_bytes()).hexdigest(),
        response_entry_sha256=sha256(raw).hexdigest(),
        adjudication_pack=_load(f"{base}/kimi_k3_adjudication_pack.json"),
        adjudication_manifest=_load(f"{base}/private_adjudication_manifest.json"),
        panel_packs=packs, panel_manifest=_load(f"{base}/private_panel_manifest.json"),
        annotation_responses=responses,
        prior_shadow=_load(f"{base}/identity_aware_shadow_reference_candidate.json"),
    )
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(bundle, output / "source_kimi_compromised_adjudication_bundle.zip")
    (output / "kimi_k3_compromised_context_response.json").write_bytes(raw)
    target = output / "context_compromised_adjudication_shadow_candidate.json"
    target.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "candidate_state": artifact["candidate_state"], "protocol_compliant": False,
        "dispute_flip_count": artifact["dispute_flip_count"],
        "dispute_count": artifact["dispute_count"],
        "packet_verdict_change_count": artifact["packet_verdict_change_count"],
        "artifact_hash": artifact["artifact_hash"], "output": str(target),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
