"""Validate v0.11 panel responses and build the anonymous Kimi-K3 pack."""

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

from local_collective_cognition.clarification_semantic_basis_panel import CRITERIA, build_semantic_basis_adjudication, validate_semantic_basis_adjudication, validate_semantic_basis_annotation_response, validate_semantic_basis_panel
from local_collective_cognition.provider_telemetry import hash_payload


def resolve(path):
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def read(path):
    return json.loads(resolve(path).read_text(encoding="utf-8"))


def write(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/clarification_semantic_basis_v0_11"
    parser.add_argument("--gpt-response", default=r"C:/Users/ZH/Downloads/gpt_5_6_semantic_basis_results.json")
    parser.add_argument("--gemini-response", default=r"C:/Users/ZH/Downloads/gemini-code-1784724522737.json")
    parser.add_argument("--output-dir", default=base)
    args = parser.parse_args()
    output = resolve(args.output_dir)
    packs = (read(f"{base}/gpt_5_6_semantic_basis_pack.json"), read(f"{base}/gemini_3_1_semantic_basis_pack.json"))
    panel_manifest = read(f"{base}/private_semantic_basis_panel_manifest.json")
    responses = (read(args.gpt_response), read(args.gemini_response))
    validate_semantic_basis_panel(packs=packs, manifest=panel_manifest)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    for response in responses:
        validate_semantic_basis_annotation_response(response, pack=pack_index[response["lane_id"]])
    adjudication_pack, adjudication_manifest = build_semantic_basis_adjudication(packs=packs, panel_manifest=panel_manifest, responses=responses)
    validate_semantic_basis_adjudication(pack=adjudication_pack, manifest=adjudication_manifest, panel_packs=packs, panel_manifest=panel_manifest, responses=responses)
    output.mkdir(parents=True, exist_ok=True)
    names = {"annotation-lane-a": "gpt_5_6_semantic_basis_response.json", "annotation-lane-b": "gemini_3_1_semantic_basis_response.json"}
    for response in responses:
        write(output / names[response["lane_id"]], response)
    write(output / "kimi_k3_semantic_basis_adjudication_pack.json", adjudication_pack)
    write(output / "private_semantic_basis_adjudication_manifest.json", adjudication_manifest)
    zip_path = output / "kimi_k3_semantic_basis_adjudication_pack.zip"
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(output / "kimi_k3_semantic_basis_adjudication_pack.json", arcname="kimi_k3_semantic_basis_adjudication_pack.json")
    disagreements = Counter(item["criterion"] for item in adjudication_pack["items"])
    agreement_states = {criterion: Counter(record["selected_state"] for record in adjudication_manifest["agreement_records"] if record["criterion"] == criterion) for criterion in CRITERIA}
    coherence_records = []
    for response in responses:
        for label in response["labels"]:
            criteria = label["criteria"]
            basis = criteria["SELECTION_BASIS"]
            selected = criteria["SELECTED_OBJECT"]
            preference = criteria["PRAGMATIC_PREFERENCE"]
            violation = None
            if basis in ("LEXICAL_EXACT", "COMPOSITIONAL_ENTAILMENT") and selected not in ("CANDIDATE_A", "CANDIDATE_B"):
                violation = "HARD_BASIS_WITHOUT_SELECTED_OBJECT"
            elif basis == "PRAGMATIC_DEFAULT" and (selected != "NONE" or preference not in ("CANDIDATE_A", "CANDIDATE_B")):
                violation = "PRAGMATIC_BASIS_AXIS_MISMATCH"
            elif basis == "NO_PREFERENCE" and (selected != "NONE" or preference != "NONE"):
                violation = "NO_PREFERENCE_AXIS_MISMATCH"
            if violation:
                coherence_records.append({"lane_id": response["lane_id"], "annotation_id": label["annotation_id"], "violation": violation, "criteria": criteria})
    summary_commitment = {
        "analysis_version": "clarification_semantic_basis_panel_agreement_v0_11",
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "response_hashes": {response["lane_id"]: hash_payload(response) for response in responses},
        "agreement_count": adjudication_manifest["agreement_count"],
        "disagreement_count": adjudication_manifest["disagreement_count"],
        "disagreement_counts_by_criterion": dict(sorted(disagreements.items())),
        "agreement_state_counts_by_criterion": {criterion: dict(sorted(counts.items())) for criterion, counts in agreement_states.items()},
        "cross_axis_inconsistency_count": len(coherence_records),
        "cross_axis_inconsistency_counts_by_lane": dict(sorted(Counter(record["lane_id"] for record in coherence_records).items())),
        "cross_axis_inconsistency_records": coherence_records,
        "reference_state": adjudication_manifest["reference_state"],
        "ground_truth_claim": False,
    }
    summary = {**summary_commitment, "artifact_hash": hash_payload(summary_commitment)}
    write(output / "panel_agreement_analysis.json", summary)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "agreement_count": adjudication_manifest["agreement_count"],
        "disagreement_count": adjudication_manifest["disagreement_count"],
        "disagreement_counts_by_criterion": dict(sorted(disagreements.items())),
        "k3_pack_hash": adjudication_pack["pack_hash"],
        "reference_state": adjudication_manifest["reference_state"],
        "response_hashes": summary["response_hashes"],
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
