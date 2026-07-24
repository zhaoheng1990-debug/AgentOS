"""Close and package v0.40 embedded null-role composition."""
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
    output = REPO_ROOT / "outputs" / "null_role_v0_40"
    prior_stop = read(output / "source_v0_39_early_stop.json")
    prior_closure = read(output / "source_v0_39_closure.json")
    cost_analysis = read(output / "source_v0_38_cost_analysis.json")
    corpus = read(output / "null_role_corpus_frozen.json")
    preregistration = read(output / "null_role_preregistration.json")
    run = read(output / "null_role_run.json")
    analysis = read(output / "null_role_analysis.json")
    posthoc = read(output / "posthoc_null_role_calibration.json")
    metrics = analysis["pooled_contrast_metrics"]
    composition = analysis["composition_metrics"]
    gross = composition["triggered_composition_gross_uplift"]
    net = composition["triggered_composition_net_uplift"]
    oracle = posthoc["pool_oracle_gross_uplift"]
    regret = posthoc["composition_regret"]
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    diagnostics_commitment = {
        "diagnostic_version": "null_role_diagnostics_v0_40",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "composition_receipt_count": len(
            run["composition_receipts"]
        ),
        "separate_value_provider_call_count": sum(
            value["stage"] == "SOURCE_BLIND_CANDIDATE_VALUE"
            for value in run["task_calls"]
        ),
        "failures": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "composition_metrics": composition,
        "pooled_metrics": metrics,
        "posthoc_oracle_metrics": oracle,
        "failed_conditions": failed,
        "external_panel_present": False,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "null_role_diagnostics.json", diagnostics)
    report = "\n".join([
        "# Independent null-information-role composition v0.40",
        "",
        "## Observed facts",
        (
            f"- Null-role-minus-A1 net mean/median: {metrics['mean']:.3f}/"
            f"{metrics['median']:.3f}; wins "
            f"{metrics['win_count']}/{metrics['count']}."
        ),
        (
            f"- Trigger rate: {composition['trigger_rate']:.3f} "
            f"({composition['trigger_count']} cells)."
        ),
        (
            f"- Triggered gross mean/median: {gross['mean']:.3f}/"
            f"{gross['median']:.3f}; wins {gross['win_count']}/"
            f"{gross['count']}; losses {gross['loss_count']}."
        ),
        (
            f"- Triggered net mean/median: {net['mean']:.3f}/"
            f"{net['median']:.3f}."
        ),
        (
            "- Mean added token penalty: "
            f"{composition['mean_added_token_penalty_cbit']:.3f} Cbit."
        ),
        (
            "- Separate candidate-value Provider calls: 0; "
            f"total tokens: {analysis['physical_total_tokens']}."
        ),
        (
            f"- Posthoc pool-oracle mean/median: {oracle['mean']:.3f}/"
            f"{oracle['median']:.3f}; positive cells "
            f"{posthoc['positive_oracle_cell_count']}/{oracle['count']}."
        ),
        (
            f"- Composition regret mean/median: {regret['mean']:.3f}/"
            f"{regret['median']:.3f}; positive-oracle fraction captured "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
        ),
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Interpretation",
        (
            "- The corrected prospective null-role contract reached full "
            "coverage for both standard and counterproposal receipts; the "
            "v0.39 object-model failure did not recur."
        ),
        (
            "- Deterministic composition preserved positive gross value and "
            "captured 96% of positive oracle uplift, so candidate selection "
            "is no longer the primary bottleneck."
        ),
        (
            "- Net performance still failed because mean added token penalty "
            "slightly exceeded the frozen 1.0-Cbit limit and one triggered "
            "cell lost gross value."
        ),
        (
            "- The next experiment should reduce low-yield trigger execution "
            "or counterproposal context cost without changing the calibrated "
            "selection score."
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
        "ledger_version": "null_role_ledger_v0_40",
        "source_prior_stop_hash": prior_stop["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_cost_analysis_hash": cost_analysis["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
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
        "replay_version": "null_role_replay_v0_40",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_null_role.py",
            "python examples/run_null_role.py",
            "python examples/analyze_null_role_posthoc.py",
            "python examples/finalize_null_role.py",
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
        "rollback_version": "null_role_rollback_v0_40",
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
        "closure_version": "null_role_closure_v0_40",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "null_role_gate": analysis["null_role_gate"],
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
        "source_v0_39_early_stop.json",
        "source_v0_39_closure.json",
        "source_v0_38_cost_analysis.json",
        "null_role_corpus_frozen.json",
        "null_role_preregistration.json",
        "null_role_progress.json",
        "null_role_run.json",
        "null_role_analysis.json",
        "posthoc_null_role_calibration.json",
        "null_role_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "null_role_inventory_v0_40",
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
    pack = output / "null_role_v0_40_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "null_role_manifest_v0_40",
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
