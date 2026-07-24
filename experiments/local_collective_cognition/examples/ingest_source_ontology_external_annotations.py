"""Validate v0.21 external lanes and build the anonymous Kimi K3 pack."""

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

from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    CRITERIA,
)
from local_collective_cognition.cognitive_action_source_ontology_holdout import (  # noqa: E402
    CASES,
)
from local_collective_cognition.cognitive_action_source_ontology_panel import (  # noqa: E402
    build_source_ontology_external_adjudication,
    validate_source_ontology_annotation_response,
    validate_source_ontology_external_adjudication,
    validate_source_ontology_external_panel,
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lane-a",
        default=(
            r"C:\Users\ZH\Downloads"
            r"\annotation_lane_a_source_ontology_results.json"
        ),
    )
    parser.add_argument(
        "--lane-b",
        default=r"C:\Users\ZH\Downloads\gemini-code-1784806107877.json",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO_ROOT / "outputs" / "source_ontology_ablation_v0_21"
        ),
    )
    args = parser.parse_args()
    output = Path(args.output_dir)
    panel_dir = output / "external_panel"
    raw_dir = panel_dir / "raw_received"
    raw_dir.mkdir(parents=True, exist_ok=True)
    corpus = read(output / "source_ontology_corpus_frozen.json")
    run = read(output / "source_ontology_run.json")
    packs = tuple(read(panel_dir / name) for name in (
        "annotation_lane_a_source_ontology_pack.json",
        "annotation_lane_b_source_ontology_pack.json",
    ))
    panel_manifest = read(
        panel_dir / "source_ontology_external_panel_manifest.json"
    )
    validate_source_ontology_external_panel(
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
        raise ValueError("source_ontology_input_lanes_invalid")

    raw_records = []
    for path, response in zip(source_paths, responses):
        validate_source_ontology_annotation_response(
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
        build_source_ontology_external_adjudication(
            packs=packs,
            panel_manifest=panel_manifest,
            responses=responses,
            corpus=corpus,
        )
    )
    validate_source_ontology_external_adjudication(
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
        panel_dir / "kimi_k3_source_ontology_adjudication_pack.json"
    )
    adjudication_manifest_path = (
        panel_dir / "source_ontology_adjudication_manifest.json"
    )
    write(adjudication_path, adjudication_pack)
    write(adjudication_manifest_path, adjudication_manifest)

    analysis = build_analysis(
        responses=responses,
        panel_manifest=panel_manifest,
        adjudication_manifest=adjudication_manifest,
        corpus=corpus,
    )
    analysis_path = panel_dir / "source_ontology_panel_analysis.json"
    report_path = panel_dir / "SOURCE_ONTOLOGY_PANEL_ANALYSIS.md"
    write(analysis_path, analysis)
    report_path.write_text(render_analysis(analysis), encoding="utf-8")

    receipt_commitment = {
        "receipt_version": "source_ontology_annotation_ingest_v0_21",
        "panel_id": panel_manifest["panel_id"],
        "raw_records": raw_records,
        "response_hashes": (
            adjudication_manifest["annotation_response_hashes"]
        ),
        "adjudication_pack_hash": adjudication_pack["pack_hash"],
        "adjudication_manifest_hash": adjudication_manifest["manifest_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "candidate_outputs_exposed": False,
        "source_ontology_policies_exposed": False,
        "reference_frozen": False,
        "state": adjudication_manifest["reference_state"],
    }
    receipt = {
        **receipt_commitment,
        "artifact_hash": hash_payload(receipt_commitment),
    }
    receipt_path = (
        panel_dir / "source_ontology_annotation_ingest_receipt.json"
    )
    write(receipt_path, receipt)

    zip_path = output / "kimi_k3_source_ontology_adjudication_v0_21.zip"
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
            "source_ontology_external_panel_hash_inventory_v0_21"
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
        panel_dir / "source_ontology_panel_hash_inventory.json",
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


def build_analysis(
    *, responses, panel_manifest, adjudication_manifest, corpus
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
    commitment = {
        "analysis_version": (
            "source_ontology_external_panel_analysis_v0_21"
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
        "source_ontology_policies_exposed": False,
        "semantic_reference_frozen": False,
        "next_required_evidence": (
            "KIMI_K3_SOURCE_ONTOLOGY_WHOLE_TUPLE_ADJUDICATION"
        ),
        "ground_truth_claim": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis):
    observations = [
        f"Both lanes validate 24/24 objects and agree on {analysis['full_tuple_agreement_count']}/24 complete tuples.",
        f"Axis agreement counts are {analysis['axis_agreement_counts']}.",
        f"Disagreement span counts are {analysis['disagreement_axis_span_counts']}.",
        f"Disagreement mechanisms are {analysis['disagreement_mechanism_counts']}.",
        f"Evidence-state distributions are {analysis['lane_evidence_state_distributions']}.",
    ]
    interpretations = [
        "Both lanes independently recover six soft and six opaque objects, sharply contradicting the decomposed source arm's zero soft and zero opaque outputs.",
        "The six opaque disputes keep evidence state fixed but disagree on whether a recognized missing specification supports a completed NONE tuple or requires an incomplete uncertain tuple.",
        "The direct-versus-compositional disputes test whether an explicit operational sentence or its multi-clause structure owns the evidence basis; whole-tuple adjudication prevents hybrid labels.",
        "The soft-default disputes concern pragmatic preference and basis rather than semantic selection.",
        "Candidate arms, source receipts, policies, object families, design strata, and previous scores remain hidden from Kimi K3.",
    ]
    unknowns = [
        "Which opaque completion convention Kimi K3 selects.",
        "Whether the baseline's six soft and six opaque outputs survive full-tuple scoring.",
        "Whether any decomposed-source corrections offset its apparent systematic over-composition.",
    ]
    intuition = [
        "If Kimi preserves six soft and six opaque objects, the decomposed source representation has likely induced evidence fabrication rather than merely shifted conventions.",
        "If direct-versus-compositional rulings vary by wording, future receipts should record support spans and derivation steps rather than ask for more independent labels.",
        "Do not tune against these 24 objects after adjudication; use the result only to choose the next fresh mechanism test.",
    ]
    lines = ["# Source Ontology External Panel Analysis v0.21", ""]
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
        "State: `AWAITING_KIMI_K3_SOURCE_ONTOLOGY_FULL_TUPLE_ADJUDICATION`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
