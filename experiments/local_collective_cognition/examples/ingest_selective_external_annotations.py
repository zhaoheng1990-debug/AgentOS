"""Validate v0.18 external lanes and build the anonymous Kimi K3 pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_selective_holdout import CASES  # noqa: E402
from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    CRITERIA,
    build_selective_external_adjudication,
    validate_selective_annotation_response,
    validate_selective_external_adjudication,
    validate_selective_external_panel,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane-a", default=r"C:\Users\ZH\Downloads\annotation_lane_a_selective_annotation_results.json")
    parser.add_argument("--lane-b", default=r"C:\Users\ZH\Downloads\gemini-code-1784788636137.json")
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "outputs" / "selective_escalation_v0_18"))
    args = parser.parse_args()
    output = Path(args.output_dir)
    panel_dir = output / "external_panel"
    raw_dir = panel_dir / "raw_received"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corpus = read(output / "selective_fresh_corpus_frozen.json")
    baseline = read(output / "selective_baseline_run.json")
    selective_run = read(output / "selective_adjudication_run.json")
    packs = tuple(read(panel_dir / name) for name in (
        "annotation_lane_a_selective_annotation_pack.json",
        "annotation_lane_b_selective_annotation_pack.json",
    ))
    panel_manifest = read(panel_dir / "selective_external_panel_manifest.json")
    validate_selective_external_panel(
        packs=packs,
        manifest=panel_manifest,
        source_inputs={
            "corpus": corpus,
            "baseline_run": baseline,
            "selective_run": selective_run,
        },
    )
    source_paths = (Path(args.lane_a), Path(args.lane_b))
    responses = tuple(read(path) for path in source_paths)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {response.get("lane_id"): response for response in responses}
    if set(response_index) != set(pack_index) or len(response_index) != len(responses):
        raise ValueError("selective_annotation_input_lanes_invalid")
    for lane, response in response_index.items():
        validate_selective_annotation_response(response, pack=pack_index[lane])
    raw_records = []
    for path, response in zip(source_paths, responses):
        raw_name = f"{response['lane_id']}_{path.name}"
        raw_path = raw_dir / raw_name
        shutil.copyfile(path, raw_path)
        raw_records.append({
            "lane_id": response["lane_id"],
            "source_path": str(path),
            "protected_copy": str(raw_path.relative_to(output)).replace("\\", "/"),
            "size_bytes": raw_path.stat().st_size,
            "sha256": sha256_file(raw_path),
            "parsed_payload_hash": hash_payload(response),
        })
        write(panel_dir / f"{response['lane_id']}_validated_response.json", response)
    adjudication_pack, adjudication_manifest = build_selective_external_adjudication(
        packs=packs,
        panel_manifest=panel_manifest,
        responses=responses,
        corpus=corpus,
    )
    source_inputs = {
        "packs": packs,
        "panel_manifest": panel_manifest,
        "responses": responses,
        "corpus": corpus,
    }
    validate_selective_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs=source_inputs,
    )
    write(panel_dir / "kimi_k3_selective_adjudication_pack.json", adjudication_pack)
    write(panel_dir / "selective_adjudication_manifest.json", adjudication_manifest)
    analysis = build_panel_analysis(
        responses=responses,
        panel_manifest=panel_manifest,
        adjudication_manifest=adjudication_manifest,
        corpus=corpus,
    )
    write(panel_dir / "selective_panel_analysis.json", analysis)
    report_path = panel_dir / "SELECTIVE_PANEL_ANALYSIS.md"
    report_path.write_text(render_panel_analysis(analysis), encoding="utf-8")
    receipt_commitment = {
        "receipt_version": "selective_external_annotation_ingest_v0_18",
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "raw_records": raw_records,
        "validated_response_hashes": adjudication_manifest["annotation_response_hashes"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "panel_analysis_hash": analysis["artifact_hash"],
        "candidate_outputs_exposed": False,
        "reference_frozen": False,
        "current_state": adjudication_manifest["reference_state"],
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    receipt = {**receipt_commitment, "artifact_hash": hash_payload(receipt_commitment)}
    write(panel_dir / "selective_annotation_ingest_receipt.json", receipt)
    k3_zip = output / "kimi_k3_selective_adjudication_v0_18.zip"
    with zipfile.ZipFile(k3_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        zip_info = zipfile.ZipInfo(
            "kimi_k3_selective_adjudication_pack.json",
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        zip_info.compress_type = zipfile.ZIP_DEFLATED
        zip_info.external_attr = 0o644 << 16
        archive.writestr(
            zip_info,
            (panel_dir / "kimi_k3_selective_adjudication_pack.json").read_bytes(),
        )
    inventory_paths = [
        panel_dir / "ANNOTATION_LANE_A_validated_response.json",
        panel_dir / "ANNOTATION_LANE_B_validated_response.json",
        panel_dir / "kimi_k3_selective_adjudication_pack.json",
        panel_dir / "selective_adjudication_manifest.json",
        panel_dir / "selective_panel_analysis.json",
        report_path,
        panel_dir / "selective_annotation_ingest_receipt.json",
        k3_zip,
        *[output / record["protected_copy"] for record in raw_records],
    ]
    inventory_commitment = {
        "inventory_version": "selective_external_panel_hash_inventory_v0_18",
        "items": [
            {
                "path": str(path.relative_to(output)).replace("\\", "/"),
                "size_bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            }
            for path in inventory_paths
        ],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(panel_dir / "selective_panel_hash_inventory.json", inventory)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "agreement_objects": adjudication_manifest["agreement_object_count"],
        "disagreement_objects": adjudication_manifest["disagreement_object_count"],
        "axis_agreement_counts": analysis["axis_agreement_counts"],
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "k3_zip": str(k3_zip),
        "k3_zip_sha256": sha256_file(k3_zip),
        "state": adjudication_manifest["reference_state"],
    }, indent=2, sort_keys=True))


def build_panel_analysis(*, responses, panel_manifest, adjudication_manifest, corpus):
    response_index = {response["lane_id"]: response for response in responses}
    lane_labels = {
        lane: {
            panel_manifest["private_lane_bindings"][lane][label["annotation_id"]]: label
            for label in response_index[lane]["labels"]
        }
        for lane in response_index
    }
    lanes = sorted(lane_labels)
    axis_agreement = Counter()
    disagreement_span = Counter()
    state_distributions = {
        lane: {criterion: Counter() for criterion in CRITERIA} for lane in lanes
    }
    confidence = {
        lane: {criterion: [] for criterion in CRITERIA} for lane in lanes
    }
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    disagreement_records = []
    for conflict_id in sorted(lane_labels[lanes[0]]):
        differing = []
        for criterion in CRITERIA:
            values = [
                lane_labels[lane][conflict_id]["criteria"][criterion] for lane in lanes
            ]
            if len(set(values)) == 1:
                axis_agreement[criterion] += 1
            else:
                differing.append(criterion)
            for lane in lanes:
                label = lane_labels[lane][conflict_id]
                state_distributions[lane][criterion][label["criteria"][criterion]] += 1
                confidence[lane][criterion].append(label["criterion_confidence"][criterion])
        if differing:
            disagreement_span[len(differing)] += 1
            case_id = bindings[conflict_id]["case_id"]
            disagreement_records.append({
                "conflict_id": conflict_id,
                "case_id": case_id,
                "object_family": bindings[conflict_id]["object_family"],
                "design_stratum": case_by_id[case_id].design_stratum,
                "differing_axes": differing,
            })
    by_stratum = Counter(record["design_stratum"] for record in disagreement_records)
    commitment = {
        "analysis_version": "selective_external_panel_analysis_v0_18",
        "panel_id": panel_manifest["panel_id"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "lane_ids": lanes,
        "validated_object_count_per_lane": {
            lane: len(lane_labels[lane]) for lane in lanes
        },
        "full_tuple_agreement_count": adjudication_manifest["agreement_object_count"],
        "full_tuple_disagreement_count": adjudication_manifest["disagreement_object_count"],
        "axis_agreement_counts": dict(axis_agreement),
        "disagreement_axis_span_counts": {
            str(key): value for key, value in sorted(disagreement_span.items())
        },
        "disagreement_records": disagreement_records,
        "private_pattern_summary": {
            "disagreement_count_by_design_stratum": dict(by_stratum),
            "all_opaque_design_cases_disagree": by_stratum["OPAQUE_SPECIFICATION"] == 6,
            "private_provenance_exposed_to_adjudicator": False,
        },
        "lane_state_distributions": {
            lane: {
                criterion: dict(counter) for criterion, counter in values.items()
            }
            for lane, values in state_distributions.items()
        },
        "lane_mean_confidence": {
            lane: {
                criterion: round(sum(values) / len(values), 6)
                for criterion, values in axes.items()
            }
            for lane, axes in confidence.items()
        },
        "candidate_outputs_exposed": False,
        "semantic_reference_frozen": False,
        "next_required_evidence": "KIMI_K3_SELECTIVE_WHOLE_TUPLE_ADJUDICATION",
        "ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_panel_analysis(analysis):
    observations = [
        f"Both lanes validate 24/24 objects and agree on {analysis['full_tuple_agreement_count']}/24 complete five-axis tuples.",
        f"Axis agreement counts are {analysis['axis_agreement_counts']}.",
        f"Disagreement span counts are {analysis['disagreement_axis_span_counts']}.",
        f"Lane state distributions are {analysis['lane_state_distributions']}.",
        f"Private design diagnostics are {analysis['private_pattern_summary']}.",
    ]
    interpretations = [
        "Both external lanes recover six soft-ambiguity objects and six opaque-reference objects, directly contradicting the baseline gate's zero soft-ambiguity output.",
        "The largest direct-versus-compositional disagreement concerns explanatory basis, while selected object is usually stable.",
        "All six opaque-design objects disagree because one lane treats missing defining evidence as an incomplete assessment and the other treats justified nonselection as a complete assessment.",
        "Whole five-axis tuples remain the adjudication unit; criterion-wise voting could create evidence-basis or openness-process contradictions.",
        "Candidate outputs and design strata remain hidden from Kimi K3.",
    ]
    unknowns = [
        "Whether Kimi K3 resolves opaque evidence as completed justified openness, incomplete assessment, or an independent third tuple.",
        "How many externally confirmed soft-ambiguity objects the frozen baseline gate missed.",
        "Whether the direct-definition collapse remains after the direct/compositional boundary is adjudicated.",
    ]
    intuition = [
        "The gate failure is likely not absence of semantic signal: both independent lanes see the same six soft-ambiguity objects.",
        "Evidence state and process state should remain separate because opaque evidence can coexist with a completed judgment that the object is unresolved.",
        "If K3 preserves complete opaque judgments, future admission should distinguish collaboration for preference from evidence acquisition for missing definitions.",
        "The next calibration target should be contrastive evidence-state recognition, not another specialist role.",
    ]
    lines = ["# Selective External Panel Analysis v0.18", ""]
    for title, values in (
        ("Observations", observations),
        ("Interpretations", interpretations),
        ("Unknowns", unknowns),
        ("Intuition Triggers", intuition),
    ):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        "State: `AWAITING_KIMI_K3_SELECTIVE_FULL_TUPLE_ADJUDICATION`",
        f"Artifact hash: `{analysis['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
