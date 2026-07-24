"""Close and package v0.38 embedded self-value composition."""
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
    output = REPO_ROOT / "outputs" / "self_value_v0_38"
    prior_analysis = read(output / "source_v0_37_analysis.json")
    prior_closure = read(output / "source_v0_37_closure.json")
    prior_posthoc = read(output / "source_v0_37_posthoc.json")
    corpus = read(output / "self_value_corpus_frozen.json")
    preregistration = read(output / "self_value_preregistration.json")
    run = read(output / "self_value_run.json")
    analysis = read(output / "self_value_analysis.json")
    posthoc = read(output / "posthoc_self_value_calibration.json")
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
        "diagnostic_version": "self_value_diagnostics_v0_38",
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
    write(output / "self_value_diagnostics.json", diagnostics)
    report = "\n".join([
        "# Embedded self-value composition v0.38",
        "",
        "## Observed facts",
        (
            f"- Self-value-minus-A1 mean/median: {metrics['mean']:.3f}/"
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
            "- Eliminating the third Provider call reduced mean added cost "
            "from 1.727 to 0.953 Cbit and moved pooled net performance from "
            "-0.549 to approximately break-even."
        ),
        (
            "- Embedded self-value retained positive gross composition but "
            "captured less oracle uplift than the independent v0.37 judge."
        ),
        (
            "- Supported-effect self-evaluation was well calibrated. The "
            "remaining semantic error conflates an absent effect with a "
            "low-value research candidate: informative-null candidates were "
            "rejected despite positive Cbit."
        ),
        (
            "- The next interface must separate relation truth state from "
            "research disposition before any numeric calibration change."
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
        "ledger_version": "self_value_ledger_v0_38",
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
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
        "replay_version": "self_value_replay_v0_38",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_self_value.py",
            "python examples/run_self_value.py",
            "python examples/analyze_self_value_posthoc.py",
            "python examples/finalize_self_value.py",
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
        "rollback_version": "self_value_rollback_v0_38",
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
        "closure_version": "self_value_closure_v0_38",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "self_value_gate": analysis["self_value_gate"],
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
        "source_v0_37_analysis.json",
        "source_v0_37_closure.json",
        "source_v0_37_posthoc.json",
        "self_value_corpus_frozen.json",
        "self_value_preregistration.json",
        "self_value_progress.json",
        "self_value_run.json",
        "self_value_analysis.json",
        "posthoc_self_value_calibration.json",
        "self_value_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "self_value_inventory_v0_38",
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
    pack = output / "self_value_v0_38_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "self_value_manifest_v0_38",
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
