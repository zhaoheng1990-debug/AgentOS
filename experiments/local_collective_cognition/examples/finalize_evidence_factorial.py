"""Freeze v0.20 structural analysis and blinded external panel packs."""

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

from local_collective_cognition.cognitive_action_evidence_factorial import (  # noqa: E402
    CELLS,
    LEGACY_SOURCE_PROMPT,
    REPAIRED_SOURCE_PROMPT,
)
from local_collective_cognition.cognitive_action_evidence_factorial_holdout import (  # noqa: E402
    CASES,
)
from local_collective_cognition.cognitive_action_evidence_factorial_panel import (  # noqa: E402
    build_factorial_external_panel,
    validate_factorial_external_panel,
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
    output = REPO_ROOT / "outputs" / "evidence_factorial_calibration_v0_20"
    corpus = read(output / "evidence_factorial_corpus_frozen.json")
    preregistration = read(
        output / "evidence_factorial_preregistration.json"
    )
    run = read(output / "evidence_factorial_run.json")
    analysis = read(output / "evidence_factorial_analysis.json")
    telemetry = read(output / "evidence_factorial_telemetry.json")
    diagnostics = build_diagnostics(
        corpus=corpus,
        run=run,
        analysis=analysis,
    )
    diagnostics_path = output / "evidence_factorial_structural_diagnostics.json"
    write(diagnostics_path, diagnostics)
    report_path = output / "EVIDENCE_FACTORIAL_CANDIDATE_ANALYSIS.md"
    report_path.write_text(
        render_analysis(analysis, diagnostics),
        encoding="utf-8",
    )

    packs, panel_manifest = build_factorial_external_panel(
        corpus=corpus,
        run=run,
    )
    validate_factorial_external_panel(
        packs=packs,
        manifest=panel_manifest,
        source_inputs={"corpus": corpus, "run": run},
    )
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in packs:
        name = f"{pack['lane_id'].lower()}_factorial_annotation_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    panel_manifest_path = panel_dir / "factorial_external_panel_manifest.json"
    write(panel_manifest_path, panel_manifest)

    ledger_commitment = {
        "ledger_version": "evidence_factorial_phase_ledger_v0_20",
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
                "phase": "G2_FACTORIAL_CANDIDATE_RUN",
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
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "phase_ledger.json", ledger)

    replay_commitment = {
        "pointer_version": "evidence_factorial_replay_v0_20",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_evidence_factorial.py",
            "python examples/run_evidence_factorial.py",
            "python examples/finalize_evidence_factorial.py",
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
        "pointer_version": "evidence_factorial_rollback_v0_20",
        "scope": "experiment-only; AgentOS CoreSlim excluded",
        "rollback_action": (
            "quarantine v0.20 code and outputs after hash verification"
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
        "evidence_factorial_preregistration.json",
        "evidence_factorial_corpus_frozen.json",
        "evidence_factorial_run.json",
        "evidence_factorial_analysis.json",
        "evidence_factorial_telemetry.json",
        diagnostics_path.name,
        report_path.name,
        "phase_ledger.json",
        "replay_pointer.json",
        "rollback_pointer.json",
        *[f"external_panel/{name}" for name in lane_names],
        "external_panel/factorial_external_panel_manifest.json",
    ]
    inventory_commitment = {
        "inventory_version": "evidence_factorial_hash_inventory_v0_20",
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
        "manifest_version": "evidence_factorial_manifest_v0_20",
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

    pack_path = output / "evidence_factorial_external_panel_v0_20.zip"
    pack_members = [
        *[
            (panel_dir / name, name)
            for name in lane_names
        ],
        (
            panel_manifest_path,
            "PRIVATE_factorial_external_panel_manifest.json",
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
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
        "source_call_coverage": analysis["source_call_coverage"],
        "cell_coverage": analysis["cell_coverage"],
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def build_diagnostics(*, corpus, run, analysis):
    case_by_id = {case.case_id: case for case in CASES}
    bindings = corpus["private_provenance"]["bindings"]
    by_cell = {cell: Counter() for cell in CELLS}
    observed_by_cell = {cell: set() for cell in CELLS}
    for output in run["outputs"]:
        binding = bindings[output["conflict_id"]]
        case = case_by_id[binding["case_id"]]
        observed_by_cell[output["cell"]].add(output["conflict_id"])
        by_cell[output["cell"]][(
            case.design_stratum,
            output["payload"]["evidence_state"],
        )] += 1
    missing_by_cell = {cell: Counter() for cell in CELLS}
    for cell in CELLS:
        for conflict_id, binding in bindings.items():
            if conflict_id not in observed_by_cell[cell]:
                missing_by_cell[cell][
                    case_by_id[binding["case_id"]].design_stratum
                ] += 1
    source_calls = {}
    for call in run["source_calls"]:
        if call["status"] == "COMPLETED":
            source_calls[(
                call["conflict_id"],
                call["source_prompt_policy"],
            )] = call["source_receipt"]
    difference_records = []
    compared_fields = (
        "definition_source",
        "selected_object",
        "pragmatic_preference",
        "assessment_process_state",
    )
    for conflict_id, binding in sorted(bindings.items()):
        legacy = source_calls.get((conflict_id, LEGACY_SOURCE_PROMPT))
        repaired = source_calls.get((conflict_id, REPAIRED_SOURCE_PROMPT))
        if legacy is None or repaired is None:
            continue
        changed = [
            field
            for field in compared_fields
            if legacy[field] != repaired[field]
        ]
        if not changed:
            continue
        case = case_by_id[binding["case_id"]]
        difference_records.append({
            "conflict_id": conflict_id,
            "case_id": case.case_id,
            "object_family": case.object_family,
            "design_stratum": case.design_stratum,
            "changed_fields": changed,
            "legacy": {
                field: legacy[field] for field in compared_fields
            },
            "repaired": {
                field: repaired[field] for field in compared_fields
            },
        })
    commitment = {
        "diagnostic_version": "evidence_factorial_structural_diagnostics_v0_20",
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
            cell: dict(values) for cell, values in missing_by_cell.items()
        },
        "source_prompt_difference_records": difference_records,
        "source_prompt_difference_count": len(difference_records),
        "post_hoc_diagnostic_only": True,
        "gate_effect": False,
        "reference_revision_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_analysis(analysis, diagnostics):
    legacy_gate_gain = analysis["structural_factor_effects"][
        "gate_coverage_gain_under_legacy_source"
    ]
    design = diagnostics["design_diagnostics_not_reference_truth"]
    missing = diagnostics["missing_outputs_by_design_stratum"]
    observations = [
        f"Source-call coverage is {analysis['source_call_coverage']}.",
        f"Factorial cell coverage is {analysis['cell_coverage']}.",
        f"Evidence-state distributions are {analysis['evidence_state_distributions']}.",
        f"Definition-source distributions are {analysis['definition_source_distributions']}.",
        f"Runtime gate transforms are {analysis['gate_transform_distributions']}.",
        f"Failure counts are {analysis['failure_counts']}.",
        f"Structural factor effects are {analysis['structural_factor_effects']}.",
        f"Repaired/legacy source-prompt token ratio is {analysis['repaired_to_legacy_source_token_ratio']}.",
        f"The two source prompts differ on {diagnostics['source_prompt_difference_count']} of 24 objects.",
        f"Under the repaired source plus repaired gate, construction diagnostics are {design['REPAIRED_SOURCE_REPAIRED_GATE']} with missing outputs {missing['REPAIRED_SOURCE_REPAIRED_GATE']}.",
        f"Under the legacy source plus repaired gate, construction diagnostics are {design['LEGACY_SOURCE_REPAIRED_GATE']} with missing outputs {missing['LEGACY_SOURCE_REPAIRED_GATE']}.",
    ]
    interpretations = [
        "Each Provider source receipt is reused across both Runtime gates, so gate effects do not duplicate Provider work.",
        f"The repaired gate recovers {round(legacy_gate_gain * 24)} legacy-source outputs and reaches complete coverage; this is a real availability repair but not yet semantic correctness evidence.",
        "The repaired source prompt overcorrects structurally: all six compositional-design objects become soft, while only three direct-design objects remain direct and two direct outputs are fail-closed.",
        "The combined cell therefore does not dominate the legacy-source/repaired-gate cell even before external scoring.",
        "Differences between source prompts identify Provider sensitivity to the source ontology; output diversity alone is not gain.",
        "Construction-stratum diagnostics are preserved only to localize behavior and are not treated as reference labels.",
    ]
    unknowns = [
        "External model-panel tuples are required for admission precision, soft recall, evidence-state accuracy, and selected-object preservation.",
        "The independent contributions and interaction of source repair and gate repair cannot be scored before the frozen reference exists.",
        "No downstream specialist-collaboration Cbit follows from admission behavior alone.",
    ]
    intuition = [
        "The next source representation should make COMPOSED_CONSTRAINTS a first-class contrast rather than treating the problem as direct versus undefined.",
        "External labels should determine whether the full-coverage gate repair preserves precision or merely admits more coherent-looking errors.",
        "Do not tune a new prompt on these 24 objects; use the current panel to decide which factor survives, then move to another fresh holdout.",
        "A positive combined cell still requires a later fresh downstream collaboration test.",
    ]
    lines = ["# Evidence Factorial v0.20 Candidate Analysis", ""]
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
        "State: `EVIDENCE_FACTORIAL_ARMS_FROZEN_AWAITING_EXTERNAL_PANEL`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
