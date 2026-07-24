"""Finalize the model-panel reference and score the frozen candidate judge."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.receipt_quality_calibration_corpus import (  # noqa: E402
    validate_receipt_quality_corpus_artifact,
)
from local_collective_cognition.receipt_quality_candidate_calibration import (  # noqa: E402
    build_receipt_quality_calibration,
    validate_receipt_quality_calibration,
)
from local_collective_cognition.receipt_quality_candidate_runtime import (  # noqa: E402
    validate_receipt_quality_candidate_run,
)
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
        raise ValueError("receipt_quality_k3_bundle_response_surface_invalid")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/receipt_quality_calibration_v0_1"
    parser.add_argument("--corpus", default=f"{base}/private_receipt_quality_corpus.json")
    parser.add_argument("--candidate-run", default=f"{base}/deepseek_receipt_quality_candidate_run.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_receipt_quality_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_receipt_quality_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", default=f"{base}/gpt_5_6_receipt_quality_response.json")
    parser.add_argument("--gemini-response", default=f"{base}/gemini_3_1_receipt_quality_response.json")
    parser.add_argument("--adjudication-pack", default=f"{base}/kimi_k3_receipt_quality_adjudication_pack.json")
    parser.add_argument("--adjudication-manifest", default=f"{base}/private_adjudication_manifest.json")
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--k3-response")
    source.add_argument("--k3-bundle")
    parser.add_argument("--k3-output", default=f"{base}/kimi_k3_receipt_quality_response.json")
    parser.add_argument("--reference-output", default=f"{base}/model_panel_reference_candidate.json")
    parser.add_argument("--calibration-output", default=f"{base}/deepseek_receipt_quality_calibration.json")
    args = parser.parse_args()

    corpus, candidate_run = _load(args.corpus), _load(args.candidate_run)
    validate_receipt_quality_corpus_artifact(corpus)
    validate_receipt_quality_candidate_run(candidate_run, corpus_artifact=corpus)
    packs = (_load(args.gpt_pack), _load(args.gemini_pack))
    panel_manifest = _load(args.panel_manifest)
    responses = (_load(args.gpt_response), _load(args.gemini_response))
    adjudication_pack = _load(args.adjudication_pack)
    adjudication_manifest = _load(args.adjudication_manifest)
    if args.k3_bundle:
        k3_response = _bundle_response(
            _resolve(args.k3_bundle),
            panel_id=adjudication_pack["panel_id"],
            pack_hash=adjudication_pack["pack_hash"],
        )
    elif args.k3_response:
        k3_response = _load(args.k3_response)
    else:
        k3_response = None
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
    if k3_response is not None:
        _resolve(args.k3_output).write_text(
            json.dumps(k3_response, indent=2, sort_keys=True), encoding="utf-8"
        )
    calibration = build_receipt_quality_calibration(
        corpus_artifact=corpus,
        candidate_run=candidate_run,
        reference_artifact=reference,
    )
    validate_receipt_quality_calibration(
        calibration,
        corpus_artifact=corpus,
        candidate_run=candidate_run,
        reference_artifact=reference,
    )
    reference_output = _resolve(args.reference_output)
    calibration_output = _resolve(args.calibration_output)
    reference_output.write_text(json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8")
    calibration_output.write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "reference_artifact_hash": reference["artifact_hash"],
        "calibration_artifact_hash": calibration["artifact_hash"],
        "candidate_state": calibration["candidate_state"],
        "criterion_agreement": calibration["criterion_agreement"],
        "packet_state_accuracy": calibration["packet_state_accuracy"],
        "false_usable_rate": calibration["false_usable_rate"],
        "gate_results": calibration["gate_results"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
