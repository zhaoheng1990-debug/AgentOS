"""Finalize the v0.5 panel and score frozen naive/warranted arms."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_warrant_calibration import build_warrant_calibration, validate_warrant_calibration
from local_collective_cognition.negative_evidence_warrant_holdout import validate_warrant_corpus_artifact
from local_collective_cognition.negative_evidence_warrant_runtime import validate_warrant_candidate_run
from local_collective_cognition.structure_reference_panel_final import build_reference_candidate, validate_reference_candidate


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def load(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def load_bundle(path, panel_id, pack_hash):
    matches = []
    with ZipFile(path) as archive:
        for item in archive.infolist():
            if item.is_dir() or not item.filename.lower().endswith(".json"):
                continue
            value = json.loads(archive.read(item).decode("utf-8-sig"))
            if value.get("panel_id") == panel_id and value.get("adjudication_pack_hash") == pack_hash and {"blinding_attestation", "decisions"}.issubset(value):
                matches.append(value)
    if len(matches) != 1:
        raise ValueError("negative_warrant_k3_bundle_invalid")
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_warrant_v0_5_1"
    parser.add_argument("--corpus", default=f"{base}/private_negative_warrant_corpus.json")
    parser.add_argument("--candidate-run", default=f"{base}/candidate_run.json")
    parser.add_argument("--gpt-pack", default=f"{base}/gpt_5_6_negative_warrant_pack.json")
    parser.add_argument("--gemini-pack", default=f"{base}/gemini_3_1_negative_warrant_pack.json")
    parser.add_argument("--panel-manifest", default=f"{base}/private_panel_manifest.json")
    parser.add_argument("--gpt-response", default=f"{base}/gpt_5_6_negative_warrant_response.json")
    parser.add_argument("--gemini-response", default=f"{base}/gemini_3_1_negative_warrant_response.json")
    parser.add_argument("--adjudication-pack", default=f"{base}/kimi_k3_negative_warrant_adjudication_pack.json")
    parser.add_argument("--adjudication-manifest", default=f"{base}/private_adjudication_manifest.json")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--k3-response")
    group.add_argument("--k3-bundle")
    parser.add_argument("--k3-output", default=f"{base}/kimi_k3_negative_warrant_response.json")
    parser.add_argument("--reference-output", default=f"{base}/model_panel_reference_candidate.json")
    parser.add_argument("--calibration-output", default=f"{base}/warrant_calibration.json")
    args = parser.parse_args()
    corpus = load(args.corpus)
    candidate_run = load(args.candidate_run)
    validate_warrant_corpus_artifact(corpus)
    validate_warrant_candidate_run(candidate_run, corpus_artifact=corpus)
    packs = (load(args.gpt_pack), load(args.gemini_pack))
    panel_manifest = load(args.panel_manifest)
    responses = (load(args.gpt_response), load(args.gemini_response))
    adjudication_pack = load(args.adjudication_pack)
    adjudication_manifest = load(args.adjudication_manifest)
    k3 = load_bundle(resolve(args.k3_bundle), adjudication_pack["panel_id"], adjudication_pack["pack_hash"]) if args.k3_bundle else load(args.k3_response)
    reference = build_reference_candidate(
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        panel_packs=packs,
        panel_manifest=panel_manifest,
        annotation_responses=responses,
        response=k3,
    )
    validate_reference_candidate(
        reference,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
        panel_packs=packs,
        panel_manifest=panel_manifest,
        annotation_responses=responses,
        response=k3,
    )
    calibration = build_warrant_calibration(corpus_artifact=corpus, candidate_run=candidate_run, reference_artifact=reference)
    validate_warrant_calibration(calibration, corpus_artifact=corpus, candidate_run=candidate_run, reference_artifact=reference)
    resolve(args.k3_output).write_text(json.dumps(k3, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.reference_output).write_text(json.dumps(reference, indent=2, sort_keys=True), encoding="utf-8")
    resolve(args.calibration_output).write_text(json.dumps(calibration, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "reference_artifact_hash": reference["artifact_hash"],
        "calibration_artifact_hash": calibration["artifact_hash"],
        "candidate_state": calibration["candidate_state"],
        "arm_metrics": calibration["arm_metrics"],
        "naive_gate_results": calibration["naive_gate_results"],
        "warranted_gate_results": calibration["warranted_gate_results"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
