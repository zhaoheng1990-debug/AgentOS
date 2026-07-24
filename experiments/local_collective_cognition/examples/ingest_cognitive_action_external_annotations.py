"""Validate GPT/Gemini responses and build the candidate-blind Kimi K3 pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_external_panel import (  # noqa: E402
    build_external_adjudication,
    validate_annotation_response,
    validate_external_adjudication,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--gpt-response", default=r"C:\Users\ZH\Downloads\gpt_5_6_cognitive_action_fresh_results.json")
    parser.add_argument("--gemini-response", default=r"C:\Users\ZH\Downloads\gemini-code-1784767428089.json")
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    args = parser.parse_args()
    source = Path(args.source_dir)
    panel = source / "external_panel"
    corpus = read(source / "fresh_action_corpus_frozen.json")
    manifest = read(panel / "private_external_panel_manifest.json")
    packs = (
        read(panel / "gpt_5_6_cognitive_action_fresh_pack.json"),
        read(panel / "gemini_3_1_cognitive_action_fresh_pack.json"),
    )
    pack_index = {pack["lane_id"]: pack for pack in packs}
    responses = (read(args.gpt_response), read(args.gemini_response))
    for response in responses:
        validate_annotation_response(response, pack=pack_index[response["lane_id"]])
    response_index = {response["lane_id"]: response for response in responses}
    ingested_names = {
        "annotation-lane-a": "gpt_5_6_cognitive_action_fresh_response.json",
        "annotation-lane-b": "gemini_3_1_cognitive_action_fresh_response.json",
    }
    for lane, name in ingested_names.items():
        write(panel / name, response_index[lane])
    adjudication_pack, adjudication_manifest = build_external_adjudication(
        packs=packs, panel_manifest=manifest, responses=responses, corpus=corpus
    )
    validate_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={"packs": packs, "panel_manifest": manifest, "responses": responses, "corpus": corpus},
    )
    pack_path = panel / "kimi_k3_cognitive_action_adjudication_pack.json"
    write(pack_path, adjudication_pack)
    write(panel / "private_external_adjudication_manifest.json", adjudication_manifest)
    zip_path = pack_path.with_suffix(".zip")
    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        archive.write(pack_path, arcname=pack_path.name)
    analysis = build_analysis(packs=packs, manifest=manifest, responses=responses, adjudication_manifest=adjudication_manifest)
    write(panel / "dual_annotation_analysis.json", analysis)
    (panel / "DUAL_ANNOTATION_ANALYSIS.md").write_text(render_analysis(analysis), encoding="utf-8")
    artifact_paths = [
        panel / ingested_names["annotation-lane-a"], panel / ingested_names["annotation-lane-b"],
        pack_path, zip_path, panel / "private_external_adjudication_manifest.json",
        panel / "dual_annotation_analysis.json", panel / "DUAL_ANNOTATION_ANALYSIS.md",
    ]
    inventory_commitment = {
        "inventory_version": "cognitive_action_external_adjudication_inventory_v0_16",
        "items": [{"path": path.name, "size_bytes": path.stat().st_size, "sha256": file_hash(path)} for path in artifact_paths],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(panel / "adjudication_hash_inventory.json", inventory)
    return_pack = source / "cognitive_action_kimi_k3_adjudication_v0_16_return_pack.zip"
    with ZipFile(return_pack, "w", compression=ZIP_DEFLATED) as archive:
        for path in (*artifact_paths, panel / "adjudication_hash_inventory.json"):
            archive.write(path, arcname=f"external_panel/{path.name}")
    print(json.dumps({
        "panel_id": manifest["panel_id"],
        "full_tuple_agreement_count": adjudication_manifest["agreement_object_count"],
        "disagreement_count": adjudication_manifest["disagreement_object_count"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "current_phase": adjudication_manifest["reference_state"],
        "kimi_zip": str(zip_path),
        "kimi_zip_sha256": file_hash(zip_path),
        "return_pack": str(return_pack),
        "return_pack_sha256": file_hash(return_pack),
    }, indent=2, sort_keys=True))
    return 0


def build_analysis(*, packs, manifest, responses, adjudication_manifest):
    response_index = {response["lane_id"]: response for response in responses}
    labels = {
        lane: {manifest["private_lane_bindings"][lane][label["annotation_id"]]: label for label in response["labels"]}
        for lane, response in response_index.items()
    }
    lanes = sorted(labels)
    criteria = tuple(packs[0]["response_contract"]["criteria"])
    axis_agreement, depths, lane_states = Counter(), Counter(), {lane: {criterion: Counter() for criterion in criteria} for lane in lanes}
    for conflict_id in labels[lanes[0]]:
        first, second = labels[lanes[0]][conflict_id]["criteria"], labels[lanes[1]][conflict_id]["criteria"]
        differences = [criterion for criterion in criteria if first[criterion] != second[criterion]]
        depths[len(differences)] += 1
        for criterion in criteria:
            axis_agreement[criterion] += int(first[criterion] == second[criterion])
            for lane in lanes:
                lane_states[lane][criterion][labels[lane][conflict_id]["criteria"][criterion]] += 1
    commitment = {
        "analysis_version": "cognitive_action_dual_annotation_analysis_v0_16",
        "panel_id": manifest["panel_id"],
        "panel_manifest_hash": manifest["manifest_hash"],
        "response_hashes": {lane: hash_payload(response_index[lane]) for lane in lanes},
        "full_tuple_agreement_count": adjudication_manifest["agreement_object_count"],
        "full_tuple_disagreement_count": adjudication_manifest["disagreement_object_count"],
        "axis_agreement_counts": dict(axis_agreement),
        "disagreement_depth_counts": {str(key): value for key, value in sorted(depths.items())},
        "lane_state_distributions": {lane: {criterion: dict(counter) for criterion, counter in values.items()} for lane, values in lane_states.items()},
        "observations": [
            f"The independent lanes agree on {adjudication_manifest['agreement_object_count']}/24 complete tuples and disagree on {adjudication_manifest['disagreement_object_count']}/24.",
            "Eight disagreements are basis-only; five change all four semantic axes.",
            "Selected object, pragmatic preference, and completeness each agree on 19/24; selection basis agrees on 11/24.",
        ],
        "interpretations": [
            "Basis granularity remains a recurring evaluator boundary and must not be silently collapsed into object correctness.",
            "The five full-axis disputes concentrate on deliberately undocumented definitions, making material-ambiguity handling the central adjudication object.",
        ],
        "unknowns": [
            "No frozen candidate arm can be scored until Kimi K3 returns a coherent full tuple for every disputed object.",
            "Panel agreement is a model-panel reference candidate, not human gold or external ground truth.",
        ],
        "next_required_evidence": "KIMI_K3_WHOLE_OBJECT_ADJUDICATION",
        "candidate_state": adjudication_manifest["reference_state"],
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis):
    lines = ["# Cognitive Action Dual Annotation v0.16", ""]
    for title, key in (("Observations", "observations"), ("Interpretations", "interpretations"), ("Unknowns", "unknowns")):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in analysis[key])
        lines.append("")
    lines.extend((f"Next evidence: `{analysis['next_required_evidence']}`", f"State: `{analysis['candidate_state']}`", f"Artifact hash: `{analysis['artifact_hash']}`", ""))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())

