"""Freeze v0.21 diagnostics and blinded external annotation packs."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_source_ontology import (  # noqa: E402
    AXIS_SOURCE,
    BASELINE_CELL,
    BASELINE_SOURCE,
    CELLS,
    COLLAPSED_CELL,
    NATIVE_CELL,
)
from local_collective_cognition.cognitive_action_source_ontology_holdout import (  # noqa: E402
    CASES,
)
from local_collective_cognition.cognitive_action_source_ontology_panel import (  # noqa: E402
    build_source_ontology_external_panel,
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


def write_deterministic_zip(path, members):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source, member_name in members:
            info = zipfile.ZipInfo(
                member_name,
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "source_ontology_ablation_v0_21"
    corpus = read(output / "source_ontology_corpus_frozen.json")
    preregistration = read(
        output / "source_ontology_preregistration.json"
    )
    run = read(output / "source_ontology_run.json")
    analysis = read(output / "source_ontology_analysis.json")
    telemetry = read(output / "source_ontology_telemetry.json")
    diagnostics = build_diagnostics(
        corpus=corpus,
        run=run,
        analysis=analysis,
    )
    diagnostics_path = output / "source_ontology_structural_diagnostics.json"
    write(diagnostics_path, diagnostics)
    report_path = output / "SOURCE_ONTOLOGY_CANDIDATE_ANALYSIS.md"
    report_path.write_text(
        render_analysis(analysis, diagnostics),
        encoding="utf-8",
    )

    packs, panel_manifest = build_source_ontology_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_source_ontology_external_panel(
        packs=packs,
        manifest=panel_manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in packs:
        name = f"{pack['lane_id'].lower()}_source_ontology_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    panel_manifest_path = (
        panel_dir / "source_ontology_external_panel_manifest.json"
    )
    write(panel_manifest_path, panel_manifest)

    ledger_commitment = {
        "ledger_version": "source_ontology_phase_ledger_v0_21",
        "phases": [
            {
                "phase": "G0_PREREGISTRATION",
                "status": "PASS",
                "hash": preregistration["artifact_hash"],
            },
            {
                "phase": "G1_FRESH_HOLDOUT",
                "status": "PASS",
                "hash": corpus["artifact_hash"],
            },
            {
                "phase": "G2_CANDIDATE_RUN",
                "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL",
                "source_call_coverage": analysis["source_call_coverage"],
                "cell_coverage": analysis["cell_coverage"],
                "failures": len(run["failures"]),
            },
            {
                "phase": "G3_EXTERNAL_REFERENCE",
                "status": "PENDING",
                "panel_id": panel_manifest["panel_id"],
            },
        ],
        "baseline_insertion": (
            "No Baseline Object Update; experiment candidate only"
        ),
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "phase_ledger.json", ledger)

    replay_commitment = {
        "pointer_version": "source_ontology_replay_v0_21",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_source_ontology_ablation.py",
            "python examples/run_source_ontology_ablation.py",
            "python examples/finalize_source_ontology_ablation.py",
        ],
        "frozen_preregistration_hash": preregistration["artifact_hash"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "reference_revision_allowed": False,
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay_pointer.json", replay)

    rollback_commitment = {
        "pointer_version": "source_ontology_rollback_v0_21",
        "scope": "experiment-only; AgentOS CoreSlim excluded",
        "rollback_action": (
            "quarantine v0.21 code and outputs after hash verification"
        ),
        "automatic_rollback_executed": False,
        "baseline_mutation_to_reverse": False,
        "retention_mutation_to_reverse": False,
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    names = [
        "source_ontology_preregistration.json",
        "source_ontology_corpus_frozen.json",
        "source_ontology_run.json",
        "source_ontology_analysis.json",
        "source_ontology_telemetry.json",
        diagnostics_path.name,
        report_path.name,
        "phase_ledger.json",
        "replay_pointer.json",
        "rollback_pointer.json",
        *[f"external_panel/{name}" for name in lane_names],
        "external_panel/source_ontology_external_panel_manifest.json",
    ]
    inventory_commitment = {
        "inventory_version": "source_ontology_hash_inventory_v0_21",
        "items": [{
            "path": name,
            "size_bytes": (output / name).stat().st_size,
            "sha256": sha256_file(output / name),
        } for name in names],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    inventory_path = output / "hash_inventory.json"
    write(inventory_path, inventory)

    manifest_commitment = {
        "manifest_version": "source_ontology_manifest_v0_21",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "telemetry_hash": telemetry["artifact_hash"],
        "diagnostics_hash": diagnostics["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "external_reference_available": False,
        "baseline_promotion_allowed": False,
        "selection_authority": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    manifest_path = output / "manifest.json"
    write(manifest_path, manifest)

    pack_path = output / "source_ontology_external_panel_v0_21.zip"
    pack_members = [
        *[(panel_dir / name, name) for name in lane_names],
        (
            panel_manifest_path,
            "PRIVATE_source_ontology_external_panel_manifest.json",
        ),
        (report_path, report_path.name),
        (diagnostics_path, diagnostics_path.name),
        (inventory_path, inventory_path.name),
        (manifest_path, manifest_path.name),
    ]
    write_deterministic_zip(pack_path, pack_members)
    print(json.dumps({
        "panel_id": panel_manifest["panel_id"],
        "lane_pack_hashes": panel_manifest["lane_pack_hashes"],
        "manifest_hash": manifest["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "external_panel_pack": str(pack_path),
        "external_panel_pack_sha256": sha256_file(pack_path),
        "source_call_coverage": analysis["source_call_coverage"],
        "cell_coverage": analysis["cell_coverage"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def build_diagnostics(*, corpus, run, analysis):
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    by_cell = {cell: Counter() for cell in CELLS}
    observed = {cell: set() for cell in CELLS}
    for output in run["outputs"]:
        case = case_by_id[bindings[output["conflict_id"]]["case_id"]]
        observed[output["cell"]].add(output["conflict_id"])
        by_cell[output["cell"]][(
            case.design_stratum,
            output["payload"]["evidence_state"],
        )] += 1
    missing = {cell: Counter() for cell in CELLS}
    for cell in CELLS:
        for conflict_id, binding in bindings.items():
            if conflict_id not in observed[cell]:
                case = case_by_id[binding["case_id"]]
                missing[cell][case.design_stratum] += 1

    source_calls = {
        (call["conflict_id"], call["source_policy"]): call["source_receipt"]
        for call in run["source_calls"]
        if call["status"] == "COMPLETED"
    }
    axis_records = []
    for conflict_id, binding in sorted(bindings.items()):
        receipt = source_calls.get((conflict_id, AXIS_SOURCE))
        if receipt is None:
            continue
        case = case_by_id[binding["case_id"]]
        axis_records.append({
            "conflict_id": conflict_id,
            "case_id": case.case_id,
            "object_family": case.object_family,
            "design_stratum": case.design_stratum,
            "lexical_definition": receipt["lexical_definition"],
            "compositional_derivation": (
                receipt["compositional_derivation"]
            ),
            "external_spec_dependency": (
                receipt["external_spec_dependency"]
            ),
        })
    commitment = {
        "diagnostic_version": (
            "source_ontology_structural_diagnostics_v0_21"
        ),
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "design_diagnostics_not_reference_truth": {
            cell: {
                f"{stratum}|{state}": count
                for (stratum, state), count in sorted(values.items())
            }
            for cell, values in by_cell.items()
        },
        "missing_outputs_by_design_stratum": {
            cell: dict(values) for cell, values in missing.items()
        },
        "axis_source_records": axis_records,
        "post_hoc_diagnostic_only": True,
        "gate_effect": False,
        "reference_revision_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis, diagnostics):
    design = diagnostics["design_diagnostics_not_reference_truth"]
    disagreements = analysis["pairwise_axis_disagreement_counts"]
    observations = [
        f"Source-call coverage is {analysis['source_call_coverage']}.",
        f"Cell coverage is {analysis['cell_coverage']}.",
        f"Evidence-state distributions are {analysis['evidence_state_distributions']}.",
        f"Independent source-axis distributions are {analysis['axis_source_distributions']}.",
        f"Pairwise five-axis disagreements are {disagreements}.",
        f"Failure counts are {analysis['failure_counts']}.",
        f"Axis/baseline source-token ratio is {analysis['axis_to_baseline_source_token_ratio']}.",
        f"Native-gate construction diagnostics are {design[NATIVE_CELL]}.",
    ]
    interpretations = [
        "The baseline is the surviving v0.20 legacy-source plus repaired-gate cell, not the rejected combined intervention.",
        "The collapsed and native paths reuse the same axis Provider receipt, so their difference is attributable to Runtime synthesis rather than another Provider call.",
        "Coverage and structural coherence establish executability only; they do not establish semantic correctness.",
        "Private design strata localize failures but are not reference labels and cannot authorize promotion.",
    ]
    unknowns = [
        "GPT-5.6 and Gemini-3.1 whole-tuple labels are required before precision, recall, evidence accuracy, or correction gain can be scored.",
        "The decomposed receipt may improve composition recognition while still introducing cross-axis Provider inconsistency.",
        "No downstream collaboration Cbit or transfer value follows from this admission-layer experiment.",
    ]
    intuition = [
        "If native beats collapsed, explicit Runtime conflict synthesis contributes beyond richer Provider elicitation.",
        "If collapsed and native tie, the representation helps mainly by eliciting better evidence rather than by adding a new gate.",
        "If both axis paths lose to baseline, independent questioning may fragment a judgment that the Provider handles better holistically.",
        "Do not tune against these 24 objects after the panel returns; use them only to choose the next fresh experiment.",
    ]
    lines = ["# Source Ontology v0.21 Candidate Analysis", ""]
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
        "State: `SOURCE_ONTOLOGY_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
