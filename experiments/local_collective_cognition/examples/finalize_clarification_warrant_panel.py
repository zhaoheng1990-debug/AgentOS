"""Finalize the candidate-only warrant semantics model-panel reference."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_warrant_panel import build_warrant_reference, validate_adjudication_response, validate_warrant_adjudication, validate_warrant_reference


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def load_bundle(path, panel_id, pack_hash):
    path = resolve(path)
    with ZipFile(path) as archive:
        matches = []
        for name in archive.namelist():
            if not name.lower().endswith(".json"):
                continue
            value = json.loads(archive.read(name).decode("utf-8-sig"))
            candidates = value if isinstance(value, list) else [value]
            for candidate in candidates:
                if isinstance(candidate, dict) and candidate.get("panel_id") == panel_id and candidate.get("adjudication_pack_hash") == pack_hash and "decisions" in candidate:
                    matches.append(candidate)
        if len(matches) != 1:
            raise ValueError("warrant_k3_bundle_match_invalid")
        return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_warrant_v0_10"
    parser.add_argument("--adjudication-pack", default=f"{base}/kimi_k3_warrant_semantics_adjudication_pack.json")
    parser.add_argument("--adjudication-manifest", default=f"{base}/private_warrant_adjudication_manifest.json")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--k3-response")
    group.add_argument("--k3-bundle")
    parser.add_argument("--output", default=f"{base}/warrant_model_panel_reference_candidate.json")
    args = parser.parse_args()
    pack, manifest = load(args.adjudication_pack), load(args.adjudication_manifest)
    validate_warrant_adjudication(pack=pack, manifest=manifest)
    response = load(args.k3_response) if args.k3_response else load_bundle(args.k3_bundle, pack["panel_id"], pack["pack_hash"]) if args.k3_bundle else None
    if pack["items"] and response is None:
        parser.error("--k3-response or --k3-bundle is required when disagreements exist")
    if response is not None:
        validate_adjudication_response(response, pack=pack)
        response_path = resolve(base) / "kimi_k3_warrant_semantics_response.json"
        response_path.write_text(json.dumps(response, indent=2, sort_keys=True), encoding="utf-8")
    reference = build_warrant_reference(adjudication_pack=pack, adjudication_manifest=manifest, response=response)
    validate_warrant_reference(reference, adjudication_pack=pack, adjudication_manifest=manifest, response=response)
    resolve(args.output).write_text(json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({"artifact_hash": reference["artifact_hash"], "candidate_state": reference["candidate_state"], "label_count": reference["label_count"], "adjudicated_count": manifest["disagreement_count"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
