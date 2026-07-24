"""Close and package v0.36 independent candidate arbitration."""
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
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            digest.update(block)
    return digest.hexdigest()


def zip_pack(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "independent_arbitration_v0_36"
    prior_analysis = read(output / "source_v0_35_analysis.json")
    prior_closure = read(output / "source_v0_35_closure.json")
    prior_recovery = read(output / "source_v0_35_recovery.json")
    corpus = read(output / "independent_arbitration_corpus_frozen.json")
    preregistration = read(
        output / "independent_arbitration_preregistration.json"
    )
    run = read(output / "independent_arbitration_run.json")
    analysis = read(output / "independent_arbitration_analysis.json")
    posthoc = read(
        output / "posthoc_candidate_value_decomposition.json"
    )
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    arbitration = analysis["arbitration_metrics"]
    gross = arbitration["triggered_arbitration_gross_uplift"]
    net = arbitration["triggered_arbitration_net_uplift"]
    metrics = analysis["pooled_contrast_metrics"]
    counter_posthoc = posthoc["counterproposal_gross_uplift"]
    oracle_posthoc = posthoc["pool_oracle_gross_uplift"]
    regret_posthoc = posthoc["arbitration_regret"]
    diagnostics_commitment = {
        "diagnostic_version": (
            "independent_arbitration_diagnostics_v0_36"
        ),
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "candidate_pool_count": len(run["candidate_pools"]),
        "arbitration_receipt_count": len(
            run["arbitration_receipts"]
        ),
        "failures": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "arbitration_metrics": arbitration,
        "pooled_metrics": metrics,
        "failed_conditions": failed,
        "external_panel_present": False,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "independent_arbitration_diagnostics.json", diagnostics)
    report = "\n".join([
        "# Independent candidate arbitration v0.36",
        "",
        "## Observed facts",
        (
            f"- Arbitrated-minus-A1 mean/median: {metrics['mean']:.3f}/"
            f"{metrics['median']:.3f}; wins "
            f"{metrics['win_count']}/{metrics['count']}."
        ),
        (
            "- Majority-positive case rate: "
            f"{analysis['majority_positive_case_rate']:.3f}."
        ),
        (
            f"- Trigger rate: {arbitration['trigger_rate']:.3f} "
            f"({arbitration['trigger_count']} cells)."
        ),
        (
            "- Selected source distribution: "
            f"{json.dumps(arbitration['selected_source_distribution'], sort_keys=True)}; "
            "counterproposal adoption "
            f"{arbitration['counterproposal_adoption_rate']:.3f}."
        ),
        (
            "- Gross arbitration mean/median: "
            + (
                f"{gross['mean']:.3f}/{gross['median']:.3f}."
                if gross else "not observed."
            )
        ),
        (
            "- Net arbitration mean/median: "
            + (
                f"{net['mean']:.3f}/{net['median']:.3f}."
                if net else "not observed."
            )
        ),
        (
            "- Mean added token penalty: "
            f"{arbitration['mean_added_token_penalty_cbit']:.3f} Cbit."
        ),
        (
            "- Posthoc counterproposal-only gross mean/median: "
            f"{counter_posthoc['mean']:.3f}/"
            f"{counter_posthoc['median']:.3f}."
        ),
        (
            "- Posthoc pool-oracle gross mean/median: "
            f"{oracle_posthoc['mean']:.3f}/"
            f"{oracle_posthoc['median']:.3f}; positive cells "
            f"{posthoc['positive_oracle_cell_count']}/"
            f"{oracle_posthoc['count']}."
        ),
        (
            "- Posthoc arbitration regret mean/median: "
            f"{regret_posthoc['mean']:.3f}/"
            f"{regret_posthoc['median']:.3f}; mean positive-oracle "
            "fraction captured "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
        ),
        (
            "- Prompt/arbitration coverage: "
            f"{analysis['runtime_metrics']['prompt_identity_coverage']:.3f}/"
            f"{analysis['runtime_metrics']['arbitration_contract_coverage']:.3f}."
        ),
        f"- Total tokens: {analysis['physical_total_tokens']}.",
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Interpretation",
        (
            "- The counterproposer saw the public case and selected route, "
            "but no provisional candidates or trigger diagnostics."
        ),
        (
            "- The arbiter could only select pool entries; Runtime bound "
            "pool IDs to canonical relations and materialized final IDs."
        ),
        (
            "- Baseline fallback remained available when an additional "
            "Provider stage failed, while frozen execution gates still "
            "recorded the failure."
        ),
        (
            "- The pool contained privately measurable value that the "
            "one-shot arbiter mostly failed to identify. The next bottleneck "
            "is candidate-level semantic value judgment and composition, "
            "not additional proposal volume."
        ),
        (
            "- All outcomes remain synthetic, external, candidate-only, and "
            "unable to write CoreSlim, retention, baseline, selection, or "
            "production state."
        ),
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger_commitment = {
        "ledger_version": "independent_arbitration_ledger_v0_36",
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_recovery_hash": prior_recovery["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "retention_authority": False,
        "production_authority": False,
    }
    ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "ledger.json", ledger)
    replay_commitment = {
        "replay_version": "independent_arbitration_replay_v0_36",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_independent_arbitration.py",
            "python examples/run_independent_arbitration.py",
            "python examples/analyze_independent_arbitration_posthoc.py",
            "python examples/finalize_independent_arbitration.py",
        ],
        "provider_model": run["model_id"],
        "frozen_corpus_hash": corpus["artifact_hash"],
        "warning": "Replay creates new Provider evidence.",
    }
    replay = {
        **replay_commitment,
        "artifact_hash": hash_payload(replay_commitment),
    }
    write(output / "replay.json", replay)
    rollback_commitment = {
        "rollback_version": (
            "independent_arbitration_rollback_v0_36"
        ),
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)
    closure_commitment = {
        "closure_version": "independent_arbitration_closure_v0_36",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "independent_arbitration_gate": analysis[
            "independent_arbitration_gate"
        ],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "promotion_allowed": False,
    }
    closure = {
        **closure_commitment,
        "artifact_hash": hash_payload(closure_commitment),
    }
    write(output / "closure.json", closure)
    names = [
        "source_v0_35_analysis.json",
        "source_v0_35_closure.json",
        "source_v0_35_recovery.json",
        "independent_arbitration_corpus_frozen.json",
        "independent_arbitration_preregistration.json",
        "independent_arbitration_progress.json",
        "independent_arbitration_run.json",
        "independent_arbitration_analysis.json",
        "independent_arbitration_diagnostics.json",
        "posthoc_candidate_value_decomposition.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    recovery_path = output / "checkpoint_recovery.json"
    if recovery_path.exists():
        names.append("checkpoint_recovery.json")
    inventory_commitment = {
        "inventory_version": (
            "independent_arbitration_inventory_v0_36"
        ),
        "files": [
            {
                "path": name,
                "bytes": (output / name).stat().st_size,
                "sha256": sha(output / name),
            }
            for name in names
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)
    pack = output / "independent_arbitration_v0_36_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": (
            "independent_arbitration_manifest_v0_36"
        ),
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    }
    manifest = {
        **manifest_commitment,
        "artifact_hash": hash_payload(manifest_commitment),
    }
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
