"""Finalize the v0.3 model panel and score all frozen precision arms."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_precision_calibration import (  # noqa: E402
    build_precision_calibration,
    validate_precision_calibration,
)
from local_collective_cognition.negative_evidence_precision_holdout import validate_precision_corpus_artifact  # noqa: E402
from local_collective_cognition.negative_evidence_precision_runtime import validate_precision_candidate_run  # noqa: E402
from local_collective_cognition.structure_reference_panel_final import (  # noqa: E402
    build_reference_candidate,
    validate_reference_candidate,
)


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def _load(path):
    return json.loads(_resolve(path).read_text(encoding="utf-8"))


def _bundle_response(path, *, panel_id, pack_hash):
    matches = []
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".json"):
                continue
            payload = json.loads(archive.read(info).decode("utf-8-sig"))
            if (
                {"adjudication_pack_hash", "blinding_attestation", "decisions"}.issubset(payload)
                and payload.get("panel_id") == panel_id
                and payload.get("adjudication_pack_hash") == pack_hash
            ):
                matches.append(payload)
    if len(matches) != 1:
        raise ValueError("negative_precision_k3_bundle_surface_invalid")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_precision_v0_3"
    parser.add_argument("--corpus", default=f"{base}/private_negative_precision_corpus.json")
    parser.add_argument("--candidate-run", default=f"{base}/four_arm_candidate_run_v0_3_1.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_negative_precision_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_negative_precision_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", default=f"{base}/gpt_5_6_negative_precision_response.json")
    parser.add_argument("--gemini-response", default=f"{base}/gemini_3_1_negative_precision_response.json")
    parser.add_argument("--adjudication-pack", default=f"{base}/kimi_k3_negative_precision_adjudication_pack.json")
    parser.add_argument("--adjudication-manifest", default=f"{base}/private_adjudication_manifest.json")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--k3-response")
    source.add_argument("--k3-bundle")
    parser.add_argument("--k3-output", default=f"{base}/kimi_k3_negative_precision_response.json")
    parser.add_argument("--reference-output", default=f"{base}/model_panel_reference_candidate.json")
    parser.add_argument("--calibration-output", default=f"{base}/four_arm_precision_calibration.json")
    args = parser.parse_args()
    corpus = _load(args.corpus)
    run = _load(args.candidate_run)
    validate_precision_corpus_artifact(corpus)
    validate_precision_candidate_run(run, corpus_artifact=corpus)
    packs = (_load(args.gpt_pack), _load(args.gemini_pack))
    panel_manifest = _load(args.panel_manifest)
    responses = (_load(args.gpt_response), _load(args.gemini_response))
    adjudication_pack = _load(args.adjudication_pack)
    adjudication_manifest = _load(args.adjudication_manifest)
    k3_response = (
        _bundle_response(_resolve(args.k3_bundle), panel_id=adjudication_pack["panel_id"], pack_hash=adjudication_pack["pack_hash"])
        if args.k3_bundle else _load(args.k3_response)
    )
    reference = build_reference_candidate(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        panel_packs=packs,
        panel_manifest=panel_manifest,
        annotation_responses=responses,
        response=k3_response,
    )
    validate_reference_candidate(
        reference,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        panel_packs=packs,
        panel_manifest=panel_manifest,
        annotation_responses=responses,
        response=k3_response,
    )
    calibration = build_precision_calibration(
        corpus_artifact=corpus, candidate_run=run, reference_artifact=reference,
    )
    validate_precision_calibration(
        calibration, corpus_artifact=corpus,
        candidate_run=run, reference_artifact=reference,
    )
    _resolve(args.k3_output).write_text(json.dumps(k3_response, indent=2, sort_keys=True), encoding="utf-8")
    _resolve(args.reference_output).write_text(json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8")
    _resolve(args.calibration_output).write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "reference_artifact_hash": reference["artifact_hash"],
        "calibration_artifact_hash": calibration["artifact_hash"],
        "candidate_state": calibration["candidate_state"],
        "arm_metrics": calibration["arm_metrics"],
        "gate_results": calibration["gate_results"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
