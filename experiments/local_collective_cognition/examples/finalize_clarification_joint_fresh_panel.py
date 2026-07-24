"""Finalize v0.13 K3 adjudication, coherence gate, and panel recalibration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from zipfile import ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_fresh_panel import build_joint_fresh_reference, validate_joint_fresh_adjudication, validate_joint_fresh_adjudication_response, validate_joint_fresh_reference
from local_collective_cognition.clarification_joint_fresh_panel_calibration import build_joint_fresh_final_analysis, build_joint_fresh_panel_calibration, render_joint_fresh_final_analysis, validate_joint_fresh_panel_calibration


def resolve(path):
    path = Path(path); return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def read_exact(bundle, panel_id):
    with ZipFile(resolve(bundle)) as archive:
        matches = [name for name in archive.namelist() if panel_id in Path(name).name and Path(name).suffix.casefold() == ".json"]
        if len(matches) != 1: raise ValueError(f"joint_fresh_k3_bundle_match_invalid:{matches}")
        return json.loads(archive.read(matches[0]).decode("utf-8")), matches[0]


def main():
    parser = argparse.ArgumentParser(); base = "outputs/clarification_joint_fresh_v0_13"
    parser.add_argument("--bundle", default=r"C:/Users/ZH/Downloads/Kimi_Agent_裁定结果摘要 (8).zip"); parser.add_argument("--output-dir", default=base); args = parser.parse_args(); output = resolve(args.output_dir)
    corpus = read(f"{base}/private_joint_corpus.json"); run = read(f"{base}/candidate_run.json"); pack = read(f"{base}/kimi_k3_joint_fresh_adjudication_pack.json"); manifest = read(f"{base}/private_joint_fresh_adjudication_manifest.json")
    validate_joint_fresh_adjudication(pack=pack, manifest=manifest); response, member = read_exact(args.bundle, pack["panel_id"]); validate_joint_fresh_adjudication_response(response, pack=pack)
    reference = build_joint_fresh_reference(adjudication_pack=pack, adjudication_manifest=manifest, response=response); validate_joint_fresh_reference(reference, adjudication_pack=pack, adjudication_manifest=manifest, response=response)
    calibration = build_joint_fresh_panel_calibration(corpus_artifact=corpus, run=run, panel_reference=reference); validate_joint_fresh_panel_calibration(calibration, corpus_artifact=corpus, run=run, panel_reference=reference)
    analysis = build_joint_fresh_final_analysis(calibration, panel_reference=reference)
    write(output / "kimi_k3_joint_fresh_response.json", response); write(output / "joint_fresh_model_panel_reference_candidate.json", reference); write(output / "panel_recalibration.json", calibration); write(output / "final_panel_analysis.json", analysis); (output / "FINAL_PANEL_ANALYSIS.md").write_text(render_joint_fresh_final_analysis(analysis), encoding="utf-8")
    print(json.dumps({"bundle_member": member, "reference_hash": reference["artifact_hash"], "reference_state": reference["candidate_state"], "cross_axis_inconsistency_count": reference["cross_axis_inconsistency_count"], "calibration_hash": calibration["artifact_hash"], "analysis_hash": analysis["artifact_hash"], "transfer_recommendation": calibration["transfer_recommendation"], "candidate_metrics": calibration["candidate_metrics"], "construction_panel_alignment": calibration["construction_panel_alignment"]}, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
