"""Validate v0.15 full-tuple panel responses and build the whole-object K3 pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_reference_first_holdout import validate_reference_first_holdout  # noqa: E402
from local_collective_cognition.clarification_reference_first_panel import (  # noqa: E402
    build_reference_first_adjudication,
    build_reference_first_agreement_analysis,
    render_reference_first_agreement_analysis,
    validate_reference_first_adjudication,
    validate_reference_first_agreement_analysis,
    validate_reference_first_annotation_response,
    validate_reference_first_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_reference_first_v0_15"
    parser.add_argument("--gpt-response", default=r"C:/Users/ZH/Downloads/gpt_5_6_reference_first_results.json")
    parser.add_argument("--gemini-response", default=r"C:/Users/ZH/Downloads/gemini-code-1784730672446.json")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    output = resolve(args.output_dir)
    gpt_response_path = resolve(args.gpt_response)
    gemini_response_path = resolve(args.gemini_response)
    corpus = read(output / "private_reference_first_corpus.json")
    panel_manifest = read(output / "private_reference_first_panel_manifest.json")
    packs = (
        read(output / "gpt_5_6_reference_first_pack.json"),
        read(output / "gemini_3_1_reference_first_pack.json"),
    )
    responses = (read(gpt_response_path), read(gemini_response_path))
    validate_reference_first_holdout(corpus)
    validate_reference_first_panel(packs=packs, manifest=panel_manifest, corpus_artifact=corpus)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    for response in responses:
        validate_reference_first_annotation_response(response, pack=pack_index[response["lane_id"]])
    adjudication_pack, adjudication_manifest = build_reference_first_adjudication(
        packs=packs, panel_manifest=panel_manifest, responses=responses
    )
    validate_reference_first_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        panel_inputs={"packs": packs, "panel_manifest": panel_manifest, "responses": responses},
    )
    analysis = build_reference_first_agreement_analysis(
        corpus_artifact=corpus,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    validate_reference_first_agreement_analysis(
        analysis,
        corpus_artifact=corpus,
        panel_manifest=panel_manifest,
        responses=responses,
        adjudication_pack=adjudication_pack,
        adjudication_manifest=adjudication_manifest,
    )
    names = {
        "annotation-lane-a": "gpt_5_6_reference_first_response.json",
        "annotation-lane-b": "gemini_3_1_reference_first_response.json",
    }
    for response in responses:
        write(output / names[response["lane_id"]], response)
    response_paths = {
        "annotation-lane-a": gpt_response_path,
        "annotation-lane-b": gemini_response_path,
    }
    ingest_commitment = {
        "ingest_version": "clarification_reference_first_panel_ingest_v0_15",
        "panel_id": panel_manifest["panel_id"],
        "source_files": {
            lane: {"file_name": path.name, "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for lane, path in sorted(response_paths.items())
        },
        "validated_response_hashes": {response["lane_id"]: hash_payload(response) for response in responses},
        "full_tuple_coherence_validated": True,
        "object_count_per_lane": 24,
    }
    ingest_receipt = {**ingest_commitment, "artifact_hash": hash_payload(ingest_commitment)}
    write(output / "panel_response_ingestion_receipt.json", ingest_receipt)
    write(output / "kimi_k3_reference_first_adjudication_pack.json", adjudication_pack)
    write(output / "private_reference_first_adjudication_manifest.json", adjudication_manifest)
    write(output / "panel_agreement_analysis.json", analysis)
    (output / "PANEL_AGREEMENT_ANALYSIS.md").write_text(render_reference_first_agreement_analysis(analysis), encoding="utf-8")
    zip_path = output / "kimi_k3_reference_first_adjudication_pack.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        pack_path = output / "kimi_k3_reference_first_adjudication_pack.json"
        archive.write(pack_path, arcname=pack_path.name)
    progress_commitment = {
        "progress_version": "clarification_reference_first_panel_progress_v0_15",
        "source_corpus_hash": corpus["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "annotation_response_hashes": {response["lane_id"]: hash_payload(response) for response in responses},
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "agreement_analysis_hash": analysis["artifact_hash"],
        "panel_response_ingestion_receipt_hash": ingest_receipt["artifact_hash"],
        "current_phase": adjudication_manifest["reference_state"],
        "candidate_run_allowed": False,
        "reference_revision_after_candidate_run_allowed": False,
        "ground_truth_claim": False,
        "action_credit_authority": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    progress = {**progress_commitment, "artifact_hash": hash_payload(progress_commitment)}
    write(output / "reference_first_panel_progress.json", progress)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "full_tuple_agreement_count": analysis["full_tuple_agreement_count"],
        "full_tuple_disagreement_count": analysis["full_tuple_disagreement_count"],
        "full_tuple_agreement_rate": analysis["full_tuple_agreement_rate"],
        "criterion_agreement_counts": analysis["criterion_agreement_counts"],
        "disagreement_object_counts_by_axis_count": analysis["disagreement_object_counts_by_axis_count"],
        "disagreement_object_counts_by_family": analysis["disagreement_object_counts_by_family"],
        "disagreement_object_counts_by_class": analysis["disagreement_object_counts_by_class"],
        "k3_pack_hash": adjudication_pack["pack_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "reference_state": adjudication_manifest["reference_state"],
        "candidate_run_allowed": progress["candidate_run_allowed"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
