"""Validate GPT/Gemini responses and create the identity-blind Kimi K3 pack."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_warrant_panel import build_warrant_adjudication, validate_warrant_adjudication, validate_warrant_panel


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_warrant_v0_10"
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_warrant_semantics_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_warrant_semantics_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_warrant_panel_manifest.json")
    parser.add_argument("--gpt-response", required=True)
    parser.add_argument("--gemini-response", required=True)
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    packs = (load(args.gpt_pack), load(args.gemini_pack))
    panel_manifest = load(args.panel_manifest)
    validate_warrant_panel(packs=packs, manifest=panel_manifest)
    responses = (load(args.gpt_response), load(args.gemini_response))
    pack, manifest = build_warrant_adjudication(packs=packs, panel_manifest=panel_manifest, responses=responses)
    validate_warrant_adjudication(pack=pack, manifest=manifest, panel_packs=packs, panel_manifest=panel_manifest, responses=responses)
    output = resolve(args.output_dir)
    write(output / "gpt_5_6_warrant_semantics_response.json", responses[0])
    write(output / "gemini_3_1_warrant_semantics_response.json", responses[1])
    path = output / "kimi_k3_warrant_semantics_adjudication_pack.json"
    write(path, pack)
    with ZipFile(path.with_suffix(".zip"), "w", compression=ZIP_DEFLATED) as archive:
        archive.write(path, arcname=path.name)
    write(output / "private_warrant_adjudication_manifest.json", manifest)
    print(json.dumps({"agreement_count": manifest["agreement_count"], "disagreement_count": manifest["disagreement_count"], "reference_state": manifest["reference_state"], "pack_hash": pack["pack_hash"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
