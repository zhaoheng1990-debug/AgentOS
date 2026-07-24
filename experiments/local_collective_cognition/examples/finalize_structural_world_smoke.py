"""Close and package the v0.26 structure-first problem-emergence smoke."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

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
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def deterministic_zip(path, files):
    with zipfile.ZipFile(
        path, "w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "structural_world_v0_26"
    constraints = read(output / "science_constraints_frozen.json")
    corpus = read(output / "structural_world_corpus_frozen.json")
    prereg = read(output / "structural_world_preregistration.json")
    run = read(output / "structural_world_run.json")
    analysis = read(output / "structural_world_analysis.json")
    metrics = analysis["arm_metrics"]
    best = analysis["best_structural_arm"]

    diagnostics = {
        "diagnostic_version": "structural_world_diagnostics_v0_26",
        "source_run_hash": run["run_hash"],
        "arm_order": [
            "A0_DIRECT", "A1_ONTOLOGY", "A2_GRAPH", "A3_INTERVENTION"
        ],
        "primary_metric": "mean_problem_target_f1",
        "best_structural_arm": best,
        "direct_primary_metric": analysis["direct_problem_target_f1"],
        "best_structural_primary_metric": analysis[
            "best_structural_problem_target_f1"
        ],
        "gain_over_direct": analysis[
            "problem_target_f1_gain_over_direct"
        ],
        "failure_records": run["failures"],
        "rejected_payloads_preserved": all(
            failure.get("stage") != "RUNTIME_VALIDATION"
            or "rejected_output" in failure
            for failure in run["failures"]
        ),
        "external_semantic_panel_present": False,
        "construction_truth_is_real_world_truth": False,
    }
    diagnostics["artifact_hash"] = hash_payload(diagnostics)
    write(output / "structural_world_diagnostics.json", diagnostics)

    table = [
        "| Arm | Coverage | Target F1 | Primary object | Constraints | Relations | Counterevidence | Tokens/Cbit |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm_id, value in metrics.items():
        table.append(
            f"| {arm_id} | {value['receipt_coverage']:.3f} | "
            f"{value['mean_problem_target_f1']:.3f} | "
            f"{value['mean_primary_object_recall']:.3f} | "
            f"{value['mean_hidden_constraint_recall']:.3f} | "
            f"{value['mean_critical_relation_recall']:.3f} | "
            f"{value['mean_counterevidence_recall']:.3f} | "
            f"{value['tokens_per_valid_cbit_event']:.1f} |"
        )
    observations = [
        (
            f"{analysis['valid_receipt_count']}/{analysis['task_call_count']} "
            "task receipts passed Runtime validation."
        ),
        (
            "The direct arm produced no valid receipts, so its target F1 and "
            "the preregistered structural gain are not estimable."
            if not analysis["primary_comparison_valid"] else
            f"The direct arm mean problem-target F1 was "
            f"{analysis['direct_problem_target_f1']:.3f}; the best structural "
            f"arm was {best} at "
            f"{analysis['best_structural_problem_target_f1']:.3f}."
        ),
        (
            "The preregistered primary comparison is invalid."
            if not analysis["primary_comparison_valid"] else
            f"The preregistered primary gain was "
            f"{analysis['problem_target_f1_gain_over_direct']:+.3f}."
        ),
        (
            f"The run used {analysis['total_tokens']} tokens and produced "
            f"{analysis['failure_count']} terminal failures."
        ),
    ]
    if analysis["structure_first_smoke_gate"] == "PASS":
        phenomena = [
            "At least one structure-first arm improved targeting of frozen unresolved relations over direct question expansion.",
            "The result supports a fresh independent replication and semantic panel, not recursive multi-agent organization.",
        ]
        interpretation = [
            "Inference: explicit object-world expansion may reduce premature commitment to the first salient causal story.",
            "Inference: graph position and intervention should be separated in the next replication to estimate their marginal contributions.",
        ]
        next_step = (
            "Freeze a second fresh holdout and obtain independent semantic "
            "quality judgments before testing structure-driven sub-society formation."
        )
    else:
        phenomena = [
            "The preregistered structure-first mechanism did not clear all gain, quality, coverage, and cost gates.",
            "No recursive multi-agent architecture is authorized from this result.",
        ]
        interpretation = [
            "Inference: the current structure scaffold may add representational work without improving problem selection.",
            "Inference: any useful effect may be domain-specific or hidden by receipt-quality failures.",
        ]
        next_step = (
            "Stop this mechanism version. Diagnose arm-level failures without "
            "tuning on these twelve labels; any repair requires a new holdout."
        )
    report = "\n".join([
        "# Structure-first problem emergence v0.26",
        "",
        "## Observed facts",
        *[f"- {value}" for value in observations],
        "",
        *table,
        "",
        "## Phenomena",
        *[f"- {value}" for value in phenomena],
        "",
        "## Interpretations",
        *[f"- {value}" for value in interpretation],
        "",
        "## Competing explanations",
        "- Method prompts differ in length, so additional context rather than structural organization may explain part of any gain.",
        "- Synthetic construction truth measures target recovery but not whether question wording is scientifically deep or practically valuable.",
        "- One Provider model cannot establish role diversity or group cognition.",
        "",
        "## Still unknown",
        "- Transfer to natural project evidence and longer documents.",
        "- Stability across Providers and independently generated object registries.",
        "- Downstream answer quality after the selected problem is investigated.",
        "",
        "## Questions for intuition",
        "- Did the best arm discover a better object, or merely restate more of the packet?",
        "- Which intervention exposes a genuinely new uncertainty rather than a cosmetic alternative?",
        "- At what point should an emerging problem justify spawning a specialized cognitive sub-society?",
        "",
        "## Next step",
        next_step,
        "",
        f"Candidate state: `{analysis['candidate_state']}`.",
        "No retention, baseline, selection, or production authority is granted.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    ledger_commitment = {
        "ledger_version": "structural_world_ledger_v0_26",
        "science_constraint_hash": constraints["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "structure_first_smoke_gate": analysis[
            "structure_first_smoke_gate"
        ],
        "fresh_replication_authorized": analysis[
            "fresh_replication_authorized"
        ],
        "recursive_society_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "ledger.json", ledger)

    replay_commitment = {
        "replay_version": "structural_world_replay_v0_26",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_structural_world_smoke.py",
            "python examples/run_structural_world_smoke.py",
            "python examples/finalize_structural_world_smoke.py",
            "pytest -q tests/test_structural_world_expansion.py",
        ],
        "provider_model": run["model_id"],
        "frozen_constraint_hash": constraints["artifact_hash"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "frozen_preregistration_hash": prereg["artifact_hash"],
        "warning": (
            "Replay creates new Provider evidence and is not the original run."
        ),
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay.json", replay)

    rollback_commitment = {
        "rollback_version": "structural_world_rollback_v0_26",
        "isolated_output_directory": str(output),
        "rollback_action": (
            "Remove only this isolated experiment output directory."
        ),
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
        "previous_candidate_state": (
            "SPAN_ID_FUNNEL_SMOKE_REJECTED_STOP"
        ),
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "structural_world_closure_v0_26",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "structure_first_smoke_gate": analysis[
            "structure_first_smoke_gate"
        ],
        "fresh_replication_authorized": analysis[
            "fresh_replication_authorized"
        ],
        "recursive_society_authorized": False,
        "external_panel_generated": False,
        "promotion_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)

    inventory_names = [
        "science_constraints_frozen.json",
        "structural_world_corpus_frozen.json",
        "structural_world_preregistration.json",
        "structural_world_run.json",
        "structural_world_analysis.json",
        "structural_world_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "structural_world_inventory_v0_26",
        "files": [
            {
                "path": name,
                "bytes": (output / name).stat().st_size,
                "sha256": sha256_file(output / name),
            }
            for name in inventory_names
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)

    return_pack = output / "structural_world_v0_26_return_pack.zip"
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "structural_world_manifest_v0_26",
        "return_pack": return_pack.name,
        "return_pack_sha256": sha256_file(return_pack),
        "return_pack_bytes": return_pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "candidate_state": analysis["candidate_state"],
        "structure_first_smoke_gate": analysis[
            "structure_first_smoke_gate"
        ],
        "fresh_replication_authorized": analysis[
            "fresh_replication_authorized"
        ],
        "recursive_society_authorized": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
