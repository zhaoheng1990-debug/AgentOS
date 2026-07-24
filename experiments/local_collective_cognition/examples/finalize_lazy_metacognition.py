"""Close and package v0.32 receipt-native lazy metacognition."""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
import zipfile
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def sha256(path):
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
    output = REPO_ROOT / "outputs" / "lazy_metacognition_v0_32"
    prior = read(output / "source_v0_31_analysis.json")
    prior_closure = read(output / "source_v0_31_closure.json")
    corpus = read(output / "lazy_metacognition_corpus_frozen.json")
    preregistration = read(
        output / "lazy_metacognition_preregistration.json"
    )
    run = read(output / "lazy_metacognition_run.json")
    analysis = read(output / "lazy_metacognition_analysis.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    diagnostics_commitment = {
        "diagnostic_version": "lazy_metacognition_diagnostics_v0_32",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "provisional_projection_count": len(
            run["provisional_projections"]
        ),
        "final_projection_count": len(run["final_projections"]),
        "failures": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "trigger_metrics": analysis["trigger_metrics"],
        "pooled_metrics": analysis["pooled_contrast_metrics"],
        "failed_conditions": failed,
        "external_panel_present": False,
        "core_integration_authorized": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "lazy_metacognition_diagnostics.json", diagnostics)
    gross_deltas = []
    token_penalties = []
    for replication_id, ledger in analysis[
        "replication_ledgers"
    ].items():
        entries = ledger["entries"]
        for case_id in analysis["case_deltas"][replication_id]:
            arm_values = {}
            for arm_id in ("A1_BASELINE", "A2_LAZY"):
                selected = [
                    value for value in entries
                    if value["case_id"] == case_id
                    and value["arm_id"] == arm_id
                ]
                arm_values[arm_id] = {
                    "gross": sum(
                        value["realized_effective_cbit"]
                        + value["token_cost"]
                        for value in selected
                    ),
                    "token_cost": sum(
                        value["token_cost"] for value in selected
                    ),
                }
            gross_deltas.append(
                arm_values["A2_LAZY"]["gross"]
                - arm_values["A1_BASELINE"]["gross"]
            )
            token_penalties.append(
                arm_values["A2_LAZY"]["token_cost"]
                - arm_values["A1_BASELINE"]["token_cost"]
            )
    posthoc_commitment = {
        "posthoc_version": (
            "lazy_metacognition_cost_quality_decomposition_v0_32"
        ),
        "source_analysis_hash": analysis["artifact_hash"],
        "status": "POSTHOC_DECOMPOSITION_NOT_FROZEN_GATE",
        "gross_candidate_delta": {
            "count": len(gross_deltas),
            "mean": round(statistics.fmean(gross_deltas), 6),
            "median": round(statistics.median(gross_deltas), 6),
            "win_count": sum(value > 0 for value in gross_deltas),
        },
        "incremental_token_penalty": {
            "mean_cbit_per_cell": round(
                statistics.fmean(token_penalties),
                6,
            ),
            "median_cbit_per_cell": round(
                statistics.median(token_penalties),
                6,
            ),
        },
        "frozen_decision_changed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    posthoc = {
        **posthoc_commitment,
        "artifact_hash": hash_payload(posthoc_commitment),
    }
    write(
        output / "posthoc_cost_quality_decomposition.json",
        posthoc,
    )

    metrics = analysis["pooled_contrast_metrics"]
    triggers = analysis["trigger_metrics"]
    triggered = triggers["triggered_contrast"]
    untriggered = triggers["untriggered_contrast"]
    report = "\n".join([
        "# Lazy metacognition v0.32",
        "",
        "## Observed facts",
        (
            f"- Lazy-minus-A1 mean/median: {metrics['mean']:.3f}/"
            f"{metrics['median']:.3f}; wins {metrics['win_count']}/"
            f"{metrics['count']}."
        ),
        (
            "- Majority-positive case rate: "
            f"{analysis['majority_positive_case_rate']:.3f}."
        ),
        (
            f"- Trigger rate: {triggers['trigger_rate']:.3f} "
            f"({triggers['trigger_count']} triggered cells)."
        ),
        (
            "- Triggered win precision: "
            f"{triggers['triggered_win_precision']:.3f}."
        ),
        (
            "- Triggered mean/median: "
            + (
                f"{triggered['mean']:.3f}/{triggered['median']:.3f}."
                if triggered
                else "not observed."
            )
        ),
        (
            "- Untriggered mean/median: "
            + (
                f"{untriggered['mean']:.3f}/{untriggered['median']:.3f}."
                if untriggered
                else "not observed."
            )
        ),
        (
            "- Post-hoc gross candidate mean/median before token cost: "
            f"{posthoc['gross_candidate_delta']['mean']:.3f}/"
            f"{posthoc['gross_candidate_delta']['median']:.3f}."
        ),
        (
            "- Mean incremental trigger token penalty per cell: "
            f"{posthoc['incremental_token_penalty']['mean_cbit_per_cell']:.3f} "
            "Cbit."
        ),
        (
            "- Routes: "
            f"{json.dumps(triggers['route_distribution'], sort_keys=True)}."
        ),
        f"- Total physical tokens: {analysis['physical_total_tokens']}.",
        (
            "- Failed frozen conditions: "
            + (", ".join(failed) if failed else "none")
            + "."
        ),
        "",
        "## Interpretation",
        (
            "- The ordinary A2 receipt generated three usable candidates "
            "before making a compact escalation decision."
        ),
        (
            "- A specialized role was called only for triggered cells; its "
            "tokens were combined with the first call before Cbit scoring."
        ),
        (
            "- Trigger rate is diagnostic, not an acceptance target. Net "
            "outcome, reproducibility, failures, and runaway cost govern the "
            "frozen decision."
        ),
        (
            "- Synthetic outcomes remain candidate-only and do not authorize "
            "CoreSlim, retention, baseline, selection, or production writes."
        ),
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report,
        encoding="utf-8",
    )

    ledger_commitment = {
        "ledger_version": "lazy_metacognition_ledger_v0_32",
        "source_prior_analysis_hash": prior["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
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
        "replay_version": "lazy_metacognition_replay_v0_32",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_lazy_metacognition.py",
            "python examples/run_lazy_metacognition.py",
            "python examples/finalize_lazy_metacognition.py",
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
        "rollback_version": "lazy_metacognition_rollback_v0_32",
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
        "closure_version": "lazy_metacognition_closure_v0_32",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "lazy_metacognition_gate": analysis["lazy_metacognition_gate"],
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
        "source_v0_31_analysis.json",
        "source_v0_31_closure.json",
        "lazy_metacognition_corpus_frozen.json",
        "lazy_metacognition_preregistration.json",
        "lazy_metacognition_progress.json",
        "lazy_metacognition_run.json",
        "lazy_metacognition_analysis.json",
        "lazy_metacognition_diagnostics.json",
        "posthoc_cost_quality_decomposition.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "lazy_metacognition_inventory_v0_32",
        "files": [
            {
                "path": name,
                "bytes": (output / name).stat().st_size,
                "sha256": sha256(output / name),
            }
            for name in names
        ],
    }
    inventory = {
        **inventory_commitment,
        "artifact_hash": hash_payload(inventory_commitment),
    }
    write(output / "hash_inventory.json", inventory)
    return_pack = output / "lazy_metacognition_v0_32_return_pack.zip"
    zip_pack(
        return_pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "lazy_metacognition_manifest_v0_32",
        "return_pack": return_pack.name,
        "return_pack_sha256": sha256(return_pack),
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
        "decision": analysis["decision"],
        "state": analysis["candidate_state"],
        "return_pack": str(return_pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
