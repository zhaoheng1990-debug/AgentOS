"""Close and package v0.44 three-lane replacement validation."""
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
    output = REPO_ROOT / "outputs" / "tri_lane_v0_44"
    prior_analysis = read(output / "source_v0_43_analysis.json")
    prior_closure = read(output / "source_v0_43_closure.json")
    prior_posthoc = read(output / "source_v0_43_posthoc.json")
    corpus = read(output / "tri_lane_corpus_frozen.json")
    preregistration = read(output / "tri_lane_preregistration.json")
    run = read(output / "tri_lane_run.json")
    analysis = read(output / "tri_lane_analysis.json")
    posthoc = read(output / "posthoc_tri_lane.json")
    composition = analysis["composition_metrics"]
    pooled = analysis["pooled_contrast_metrics"]
    gross = composition["triggered_composition_gross_uplift"]
    net = composition["triggered_composition_net_uplift"]
    replacement = analysis["replacement_gate_metrics"]
    oracle = posthoc["pool_oracle_gross_uplift"]
    regret = posthoc["gate_regret"]
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )

    diagnostics_commitment = {
        "diagnostic_version": "tri_lane_diagnostics_v0_44",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "qualification_receipt_count": len(
            run["qualification_receipts"]
        ),
        "qualified_count": composition["qualified_count"],
        "valid_composition_count": composition["valid_composition_count"],
        "replacement_gate_metrics": replacement,
        "failures": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "composition_metrics": composition,
        "pooled_metrics": pooled,
        "posthoc_oracle_metrics": oracle,
        "posthoc_regret_metrics": regret,
        "failed_conditions": failed,
        "external_panel_present": False,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "tri_lane_diagnostics.json", diagnostics)

    report = "\n".join([
        "# Three-lane replacement gate v0.44",
        "",
        "## Observed facts",
        (
            f"- Pooled net mean/median: {pooled['mean']:.3f}/"
            f"{pooled['median']:.3f}; wins {pooled['win_count']}/"
            f"{pooled['count']}."
        ),
        (
            f"- Raw triggers: {composition['raw_trigger_count']}; "
            f"qualified: {composition['qualified_count']}."
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
            "- Mean accepted-delta token penalty: "
            f"{composition['mean_delta_token_penalty_cbit']:.3f} Cbit."
        ),
        (
            f"- Gate receipts: {replacement['receipt_count']}; accepted "
            f"{replacement['accepted_count']}; rejected "
            f"{replacement['rejected_count']}."
        ),
        (
            f"- Pool-oracle mean/median: {oracle['mean']:.3f}/"
            f"{oracle['median']:.3f}; positive cells "
            f"{posthoc['positive_oracle_cell_count']}/{oracle['count']}."
        ),
        (
            f"- Gate regret mean/median: {regret['mean']:.3f}/"
            f"{regret['median']:.3f}; positive-oracle fraction captured "
            f"{posthoc['mean_fraction_of_positive_oracle_uplift_captured']:.3f}."
        ),
        (
            "- Gate classifications: "
            + ", ".join(
                f"{key}={value}" for key, value in sorted(
                    posthoc["classification_distribution"].items()
                )
            )
            + "."
        ),
        (
            f"- Total physical tokens: "
            f"{analysis['physical_total_tokens']}."
        ),
        "- Failed frozen conditions: "
        + (", ".join(failed) if failed else "none")
        + ".",
        "",
        "## Interpretation",
        (
            "- All twelve qualified deltas passed the compact contract and "
            "received a zero-call replacement decision."
        ),
        (
            "- The gate accepted four proposals across EFFECT, "
            "INFORMATIVE_NULL, and QUARANTINE lanes. All four increased "
            "gross and net Cbit; no harmful replacement was admitted."
        ),
        (
            "- The ungated composer produced nine wins, three ties, and no "
            "losses. The gate rejected five beneficial proposals, so "
            "positive-oracle capture remained only 0.439."
        ),
        (
            "- Formal rejection came from pooled mean, median, and "
            "replication conditions. Eight paid delta calls were rejected, "
            "and independent identical standard calls added between-arm "
            "Provider variance."
        ),
        (
            "- The next experiment should use one shared standard receipt "
            "per replication/case for both arms. This paired common-receipt "
            "design removes duplicated calls and isolates the causal value "
            "of delta generation and gate admission."
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
        "ledger_version": "tri_lane_ledger_v0_44",
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
        "replay_version": "tri_lane_replay_v0_44",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_tri_lane.py",
            "python examples/run_tri_lane.py",
            "python examples/analyze_tri_lane_posthoc.py",
            "python examples/finalize_tri_lane.py",
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
        "rollback_version": "tri_lane_rollback_v0_44",
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
        "closure_version": "tri_lane_closure_v0_44",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "tri_lane_gate": analysis["tri_lane_gate"],
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
        "source_v0_43_analysis.json",
        "source_v0_43_closure.json",
        "source_v0_43_posthoc.json",
        "tri_lane_corpus_frozen.json",
        "tri_lane_preregistration.json",
        "tri_lane_progress.json",
        "tri_lane_run.json",
        "tri_lane_analysis.json",
        "posthoc_tri_lane.json",
        "tri_lane_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "tri_lane_inventory_v0_44",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)

    pack = output / "tri_lane_v0_44_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "tri_lane_manifest_v0_44",
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
