"""Validate v0.22 external lanes and build the anonymous Kimi K3 pack."""

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

from local_collective_cognition.cognitive_action_evidence_first_holdout import (  # noqa: E402
    CASES,
)
from local_collective_cognition.cognitive_action_evidence_first_panel import (  # noqa: E402
    build_evidence_first_external_adjudication,
    validate_evidence_first_annotation_response,
    validate_evidence_first_external_adjudication,
    validate_evidence_first_external_panel,
)
from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    CRITERIA,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_deterministic_zip(path, source, member_name):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        info = zipfile.ZipInfo(
            member_name,
            date_time=(1980, 1, 1, 0, 0, 0),
        )
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        archive.writestr(info, source.read_bytes())


def build_analysis(
    *, responses, panel_manifest, adjudication_manifest, corpus, run
):
    response_index = {
        response["lane_id"]: response for response in responses
    }
    labels = {
        lane: {
            panel_manifest["private_lane_bindings"][lane][
                label["annotation_id"]
            ]: label
            for label in response["labels"]
        }
        for lane, response in response_index.items()
    }
    lanes = sorted(labels)
    axis_agreement, spans, mechanisms = Counter(), Counter(), Counter()
    distributions = {
        lane: {axis: Counter() for axis in CRITERIA}
        for lane in lanes
    }
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    case_id_by_conflict = {
        conflict_id: binding["case_id"]
        for conflict_id, binding in bindings.items()
    }
    outputs = {
        (item["conflict_id"], item["cell"]): item["payload"]
        for item in run["outputs"]
    }
    runtime_axes = {
        "SELECTED_OBJECT": "selected_object",
        "SELECTION_BASIS": "selection_basis",
        "PRAGMATIC_PREFERENCE": "pragmatic_preference",
        "EVIDENCE_STATE": "evidence_state",
        "ASSESSMENT_PROCESS_STATE": "assessment_process_state",
    }
    records = []
    for conflict_id in sorted(labels[lanes[0]]):
        differing = []
        for axis in CRITERIA:
            values = [
                labels[lane][conflict_id]["criteria"][axis]
                for lane in lanes
            ]
            axis_agreement[axis] += int(len(set(values)) == 1)
            if len(set(values)) != 1:
                differing.append(axis)
            for lane in lanes:
                distributions[lane][axis][
                    labels[lane][conflict_id]["criteria"][axis]
                ] += 1
        if differing:
            spans[len(differing)] += 1
            states = {
                labels[lane][conflict_id]["criteria"]["EVIDENCE_STATE"]
                for lane in lanes
            }
            if states == {"OPAQUE_REFERENCE"}:
                mechanism = "OPAQUE_COMPLETION_CONVENTION"
            elif states == {"SOFT_AMBIGUITY"}:
                mechanism = "SOFT_DEFAULT_CONVENTION"
            elif states == {
                "DIRECTLY_DEFINED",
                "COMPOSITIONALLY_DETERMINED",
            }:
                mechanism = "DIRECT_VS_COMPOSITIONAL"
            else:
                mechanism = "OTHER"
            mechanisms[mechanism] += 1
            case = case_by_id[bindings[conflict_id]["case_id"]]
            records.append({
                "case_id": case.case_id,
                "object_family": case.object_family,
                "design_stratum": case.design_stratum,
                "differing_axes": differing,
                "mechanism": mechanism,
            })
    changed_records = []
    for conflict_id in sorted(labels[lanes[0]]):
        baseline = outputs[
            (conflict_id, "BASELINE_LEGACY_SOURCE_REPAIRED_GATE")
        ]
        challenge = outputs[
            (conflict_id, "EVIDENCE_FIRST_SELECTIVE_CHALLENGE")
        ]
        changed_axes = [
            axis for axis, key in runtime_axes.items()
            if baseline[key] != challenge[key]
        ]
        if not changed_axes:
            continue
        lane_positions = {
            lane: labels[lane][conflict_id]["criteria"]
            for lane in lanes
        }
        changed_records.append({
            "case_id": case_id_by_conflict[conflict_id],
            "changed_axes": changed_axes,
            "baseline_values": {
                axis: baseline[runtime_axes[axis]]
                for axis in changed_axes
            },
            "challenge_values": {
                axis: challenge[runtime_axes[axis]]
                for axis in changed_axes
            },
            "lane_position_values": {
                lane: {
                    axis: lane_positions[lane][axis]
                    for axis in changed_axes
                }
                for lane in lanes
            },
            "baseline_lane_support_counts": {
                axis: sum(
                    lane_positions[lane][axis]
                    == baseline[runtime_axes[axis]]
                    for lane in lanes
                )
                for axis in changed_axes
            },
            "challenge_lane_support_counts": {
                axis: sum(
                    lane_positions[lane][axis]
                    == challenge[runtime_axes[axis]]
                    for lane in lanes
                )
                for axis in changed_axes
            },
        })
    challenge_supported_changed_axis_count = sum(
        count > 0
        for record in changed_records
        for count in record["challenge_lane_support_counts"].values()
    )
    commitment = {
        "analysis_version": (
            "evidence_first_external_panel_analysis_v0_22"
        ),
        "full_tuple_agreement_count": (
            adjudication_manifest["agreement_object_count"]
        ),
        "full_tuple_disagreement_count": (
            adjudication_manifest["disagreement_object_count"]
        ),
        "axis_agreement_counts": dict(axis_agreement),
        "disagreement_axis_span_counts": {
            str(key): value for key, value in sorted(spans.items())
        },
        "disagreement_mechanism_counts": dict(mechanisms),
        "disagreement_records": records,
        "changed_object_position_support": changed_records,
        "changed_object_count": len(changed_records),
        "changed_axis_count": sum(
            len(record["changed_axes"]) for record in changed_records
        ),
        "challenge_supported_changed_axis_count": (
            challenge_supported_changed_axis_count
        ),
        "lane_state_distributions": {
            lane: {
                axis: dict(values) for axis, values in axes.items()
            }
            for lane, axes in distributions.items()
        },
        "lane_evidence_state_distributions": {
            lane: dict(axes["EVIDENCE_STATE"])
            for lane, axes in distributions.items()
        },
        "candidate_outputs_exposed": False,
        "challenge_plan_exposed": False,
        "witness_receipts_exposed": False,
        "semantic_reference_frozen": False,
        "next_required_evidence": (
            "KIMI_K3_EVIDENCE_FIRST_WHOLE_TUPLE_ADJUDICATION"
        ),
        "ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis):
    observations = [
        f"Both lanes validate 16/16 objects and agree on {analysis['full_tuple_agreement_count']}/16 complete tuples.",
        f"Axis agreement counts are {analysis['axis_agreement_counts']}.",
        f"Disagreement span counts are {analysis['disagreement_axis_span_counts']}.",
        f"Disagreement mechanisms are {analysis['disagreement_mechanism_counts']}.",
        f"Evidence-state distributions are {analysis['lane_evidence_state_distributions']}.",
    ]
    interpretations = [
        "Both lanes independently recover four soft and four opaque objects, preserving the balanced private construction rather than collapsing open evidence into positive definition.",
        "Opaque and soft disagreements primarily test completion and default conventions; direct-versus-compositional disagreements test how much derivation may be attributed to displayed language.",
        f"The two changed missing-specification cases contribute {analysis['changed_axis_count']} changed axes, and none of those challenge values is supported by either validated lane position.",
        "Both changed objects are opaque under both lanes and neither lane selects Candidate A, while the challenge witnesses claimed positive definition and selected Candidate A.",
        "Candidate arms, challenge plans, witness receipts, object families, design strata, and previous scores remain hidden from Kimi K3.",
    ]
    unknowns = [
        "Which complete tuple Kimi K3 selects for each of the eight disputes.",
        "Whether Kimi K3 independently overturns both lane positions; selecting either supplied position leaves every challenge change unsupported.",
        "Whether the selective arm earns enough corrected Cbit to justify its 1.733 token ratio after full-tuple scoring.",
    ]
    intuition = [
        "If Kimi preserves opaque status for the changed missing-specification objects, witness generation needs an explicit named-request-versus-displayed-definition contradiction gate.",
        "If direct-versus-compositional rulings split by wording, future witnesses should expose derivation topology rather than add more prose rationale.",
        "Do not tune against these 16 objects after adjudication; use them only to choose the next fresh mechanism test.",
    ]
    lines = ["# Evidence-First External Panel Analysis v0.22", ""]
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
        "State: `AWAITING_KIMI_K3_EVIDENCE_FIRST_FULL_TUPLE_ADJUDICATION`",
        "",
    ))
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lane-a",
        default=(
            r"C:\Users\ZH\Downloads"
            r"\annotation_lane_a_evidence_first_results.json"
        ),
    )
    parser.add_argument(
        "--lane-b",
        default=r"C:\Users\ZH\Downloads\gemini-code-1784809837034.json",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO_ROOT / "outputs" / "evidence_first_selective_v0_22"
        ),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    panel_dir = output / "external_panel"
    raw_dir = panel_dir / "raw_received"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corpus = read(output / "evidence_first_corpus_frozen.json")
    run = read(output / "evidence_first_run.json")
    packs = tuple(read(panel_dir / name) for name in (
        "annotation_lane_a_evidence_first_pack.json",
        "annotation_lane_b_evidence_first_pack.json",
    ))
    panel_manifest = read(
        panel_dir / "evidence_first_external_panel_manifest.json"
    )
    validate_evidence_first_external_panel(
        packs=packs,
        manifest=panel_manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    source_paths = (Path(args.lane_a), Path(args.lane_b))
    responses = tuple(read(path) for path in source_paths)
    pack_index = {pack["lane_id"]: pack for pack in packs}
    response_index = {
        response["lane_id"]: response for response in responses
    }
    if set(response_index) != set(pack_index):
        raise ValueError("evidence_first_input_lanes_invalid")

    raw_records = []
    for path, response in zip(source_paths, responses):
        validate_evidence_first_annotation_response(
            response,
            pack=pack_index[response["lane_id"]],
        )
        raw_path = raw_dir / f"{response['lane_id']}_{path.name}"
        shutil.copyfile(path, raw_path)
        raw_records.append({
            "lane_id": response["lane_id"],
            "path": str(raw_path.relative_to(output)).replace("\\", "/"),
            "sha256": sha256_file(raw_path),
            "size_bytes": raw_path.stat().st_size,
            "payload_hash": hash_payload(response),
        })
        write(
            panel_dir / f"{response['lane_id']}_validated_response.json",
            response,
        )

    adjudication_pack, adjudication_manifest = (
        build_evidence_first_external_adjudication(
            packs=packs,
            panel_manifest=panel_manifest,
            responses=responses,
            corpus=corpus,
        )
    )
    validate_evidence_first_external_adjudication(
        pack=adjudication_pack,
        manifest=adjudication_manifest,
        source_inputs={
            "packs": packs,
            "panel_manifest": panel_manifest,
            "responses": responses,
            "corpus": corpus,
        },
    )
    adjudication_path = (
        panel_dir / "kimi_k3_evidence_first_adjudication_pack.json"
    )
    adjudication_manifest_path = (
        panel_dir / "evidence_first_adjudication_manifest.json"
    )
    write(adjudication_path, adjudication_pack)
    write(adjudication_manifest_path, adjudication_manifest)

    analysis = build_analysis(
        responses=responses,
        panel_manifest=panel_manifest,
        adjudication_manifest=adjudication_manifest,
        corpus=corpus,
        run=run,
    )
    analysis_path = panel_dir / "evidence_first_panel_analysis.json"
    report_path = panel_dir / "EVIDENCE_FIRST_PANEL_ANALYSIS.md"
    write(analysis_path, analysis)
    report_path.write_text(render_analysis(analysis), encoding="utf-8")

    receipt_commitment = {
        "receipt_version": "evidence_first_annotation_ingest_v0_22",
        "panel_id": panel_manifest["panel_id"],
        "raw_records": raw_records,
        "response_hashes": (
            adjudication_manifest["annotation_response_hashes"]
        ),
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "candidate_outputs_exposed": False,
        "challenge_plan_exposed": False,
        "witness_receipts_exposed": False,
        "reference_frozen": False,
        "state": adjudication_manifest["reference_state"],
    }
    receipt = {
        **receipt_commitment,
        "artifact_hash": hash_payload(receipt_commitment),
    }
    receipt_path = (
        panel_dir / "evidence_first_annotation_ingest_receipt.json"
    )
    write(receipt_path, receipt)

    zip_path = output / "kimi_k3_evidence_first_adjudication_v0_22.zip"
    write_deterministic_zip(
        zip_path,
        adjudication_path,
        adjudication_path.name,
    )
    paths = [
        panel_dir / "ANNOTATION_LANE_A_validated_response.json",
        panel_dir / "ANNOTATION_LANE_B_validated_response.json",
        adjudication_path,
        adjudication_manifest_path,
        analysis_path,
        report_path,
        receipt_path,
        zip_path,
        *[output / record["path"] for record in raw_records],
    ]
    inventory_commitment = {
        "inventory_version": (
            "evidence_first_external_panel_hash_inventory_v0_22"
        ),
        "items": [{
            "path": str(path.relative_to(output)).replace("\\", "/"),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        } for path in paths],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(
        panel_dir / "evidence_first_panel_hash_inventory.json",
        inventory,
    )
    print(json.dumps({
        "agreement_objects": (
            adjudication_manifest["agreement_object_count"]
        ),
        "disagreement_objects": (
            adjudication_manifest["disagreement_object_count"]
        ),
        "axis_agreement_counts": analysis["axis_agreement_counts"],
        "disagreement_axis_span_counts": (
            analysis["disagreement_axis_span_counts"]
        ),
        "disagreement_mechanism_counts": (
            analysis["disagreement_mechanism_counts"]
        ),
        "lane_evidence_state_distributions": (
            analysis["lane_evidence_state_distributions"]
        ),
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "k3_zip": str(zip_path),
        "k3_zip_sha256": sha256_file(zip_path),
        "state": adjudication_manifest["reference_state"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
