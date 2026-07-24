"""Validate v0.13 panel responses and build the anonymous Kimi-K3 pack."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.clarification_joint_coordinator_contracts import semantic_tuple_violations
from local_collective_cognition.clarification_joint_fresh_panel import CRITERIA, build_joint_fresh_adjudication, validate_joint_fresh_adjudication, validate_joint_fresh_annotation_response, validate_joint_fresh_panel
from local_collective_cognition.provider_telemetry import hash_payload


def resolve(path):
    path = Path(path); return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(); base = "outputs/clarification_joint_fresh_v0_13"
    parser.add_argument("--gpt-response", default=r"C:/Users/ZH/Downloads/gpt_5_6_joint_fresh_results.json")
    parser.add_argument("--gemini-response", default=r"C:/Users/ZH/Downloads/gemini-code-1784727662819.json")
    parser.add_argument("--output-dir", default=base); args = parser.parse_args(); output = resolve(args.output_dir)
    packs = (read(f"{base}/gpt_5_6_joint_fresh_pack.json"), read(f"{base}/gemini_3_1_joint_fresh_pack.json")); panel_manifest = read(f"{base}/private_joint_fresh_panel_manifest.json"); responses = (read(args.gpt_response), read(args.gemini_response))
    validate_joint_fresh_panel(packs=packs, manifest=panel_manifest); pack_index = {pack["lane_id"]: pack for pack in packs}
    for response in responses: validate_joint_fresh_annotation_response(response, pack=pack_index[response["lane_id"]])
    k3_pack, k3_manifest = build_joint_fresh_adjudication(packs=packs, panel_manifest=panel_manifest, responses=responses)
    validate_joint_fresh_adjudication(pack=k3_pack, manifest=k3_manifest, panel_packs=packs, panel_manifest=panel_manifest, responses=responses)
    output.mkdir(parents=True, exist_ok=True); names = {"annotation-lane-a": "gpt_5_6_joint_fresh_response.json", "annotation-lane-b": "gemini_3_1_joint_fresh_response.json"}
    for response in responses: write(output / names[response["lane_id"]], response)
    write(output / "kimi_k3_joint_fresh_adjudication_pack.json", k3_pack); write(output / "private_joint_fresh_adjudication_manifest.json", k3_manifest)
    zip_path = output / "kimi_k3_joint_fresh_adjudication_pack.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive: archive.write(output / "kimi_k3_joint_fresh_adjudication_pack.json", arcname="kimi_k3_joint_fresh_adjudication_pack.json")
    disagreement_counts = Counter(item["criterion"] for item in k3_pack["items"]); coherence_records = []
    for response in responses:
        for label in response["labels"]:
            c = label["criteria"]; violations = semantic_tuple_violations(selected=c["SELECTED_OBJECT"], basis=c["SELECTION_BASIS"], preference=c["PRAGMATIC_PREFERENCE"], completeness=c["AXIS_ASSESSMENT_COMPLETE"])
            if violations: coherence_records.append({"lane_id": response["lane_id"], "annotation_id": label["annotation_id"], "violations": violations, "criteria": c})
    summary_commitment = {"analysis_version": "clarification_joint_fresh_panel_agreement_v0_13", "panel_id": panel_manifest["panel_id"], "panel_manifest_hash": panel_manifest["manifest_hash"], "response_hashes": {response["lane_id"]: hash_payload(response) for response in responses}, "agreement_count": k3_manifest["agreement_count"], "disagreement_count": k3_manifest["disagreement_count"], "disagreement_counts_by_criterion": dict(sorted(disagreement_counts.items())), "annotator_cross_axis_inconsistency_count": len(coherence_records), "annotator_cross_axis_inconsistency_counts_by_lane": dict(sorted(Counter(item["lane_id"] for item in coherence_records).items())), "annotator_cross_axis_inconsistency_records": coherence_records, "reference_state": k3_manifest["reference_state"], "ground_truth_claim": False}
    summary = {**summary_commitment, "artifact_hash": hash_payload(summary_commitment)}; write(output / "panel_agreement_analysis.json", summary)
    print(json.dumps({"panel_id": panel_manifest["panel_id"], "agreement_count": k3_manifest["agreement_count"], "disagreement_count": k3_manifest["disagreement_count"], "disagreement_counts_by_criterion": dict(sorted(disagreement_counts.items())), "annotator_cross_axis_inconsistency_count": len(coherence_records), "annotator_cross_axis_inconsistency_counts_by_lane": summary["annotator_cross_axis_inconsistency_counts_by_lane"], "k3_pack_hash": k3_pack["pack_hash"], "reference_state": k3_manifest["reference_state"]}, indent=2, sort_keys=True)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
