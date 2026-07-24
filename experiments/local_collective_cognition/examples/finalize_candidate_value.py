"""Close and package v0.37 candidate-value composition."""
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
    output = REPO_ROOT / "outputs" / "candidate_value_v0_37"
    prior_analysis = read(output / "source_v0_36_analysis.json")
    prior_closure = read(output / "source_v0_36_closure.json")
    prior_posthoc = read(output / "source_v0_36_posthoc.json")
    corpus = read(output / "candidate_value_corpus_frozen.json")
    preregistration = read(output / "candidate_value_preregistration.json")
    run = read(output / "candidate_value_run.json")
    analysis = read(output / "candidate_value_analysis.json")
    posthoc = read(output / "posthoc_oracle_capture.json")
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
        "diagnostic_version": "candidate_value_diagnostics_v0_37",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "value_receipt_count": len(run["value_receipts"]),
        "composition_receipt_count": len(
            run["composition_receipts"]
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
    write(output / "candidate_value_diagnostics.json", diagnostics)
    report = "\n".join([
        "# Source-blind candidate value composition v0.37",
        "",
        "## Observed facts",
        (
            f"- Value-minus-A1 mean/median: {metrics['mean']:.3f}/"
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
            "- Counterproposal adoption: "
            f"{composition['counterproposal_adoption_rate']:.3f}; "
            "sources "
            f"{json.dumps(composition['selected_source_distribution'], sort_keys=True)}."
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
        f"- Total tokens: {analysis['physical_total_tokens']}.",
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Interpretation",
        (
            "- Source-blind factorized value judgments converted the prior "
            "negative gross arbitration effect into consistently positive "
            "gross candidate composition."
        ),
        (
            "- Runtime captured most available oracle uplift, but the "
            "additional value-provider call cost more Cbit than the mean "
            "gross gain and relation reproducibility declined."
        ),
        (
            "- The next bottleneck is preserving candidate-value semantics "
            "while eliminating or sharply compressing the third Provider "
            "call, not increasing proposal volume."
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
        "ledger_version": "candidate_value_ledger_v0_37",
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
        "replay_version": "candidate_value_replay_v0_37",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_candidate_value.py",
            "python examples/run_candidate_value.py",
            "python examples/analyze_candidate_value_posthoc.py",
            "python examples/finalize_candidate_value.py",
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
        "rollback_version": "candidate_value_rollback_v0_37",
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
        "closure_version": "candidate_value_closure_v0_37",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "candidate_value_gate": analysis["candidate_value_gate"],
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
        "source_v0_36_analysis.json",
        "source_v0_36_closure.json",
        "source_v0_36_posthoc.json",
        "candidate_value_corpus_frozen.json",
        "candidate_value_preregistration.json",
        "candidate_value_progress.json",
        "candidate_value_run.json",
        "candidate_value_analysis.json",
        "posthoc_oracle_capture.json",
        "candidate_value_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    recovery = output / "checkpoint_recovery.json"
    if recovery.exists():
        names.append("checkpoint_recovery.json")
    inventory_commitment = {
        "inventory_version": "candidate_value_inventory_v0_37",
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
    pack = output / "candidate_value_v0_37_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "candidate_value_manifest_v0_37",
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
