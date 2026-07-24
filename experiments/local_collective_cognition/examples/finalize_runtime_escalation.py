"""Close and package v0.33 zero-token Runtime escalation."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.provider_telemetry import (  # noqa: E402
    hash_payload,
)
from local_collective_cognition.runtime_escalation_posthoc import (  # noqa: E402
    analyze_worker_uplift,
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
    output = REPO_ROOT / "outputs" / "runtime_escalation_v0_33"
    prior = read(output / "source_v0_32_analysis.json")
    prior_posthoc = read(output / "source_v0_32_posthoc.json")
    prior_closure = read(output / "source_v0_32_closure.json")
    corpus = read(output / "runtime_escalation_corpus_frozen.json")
    preregistration = read(
        output / "runtime_escalation_preregistration.json"
    )
    run = read(output / "runtime_escalation_run.json")
    analysis = read(output / "runtime_escalation_analysis.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    standard_tokens = {"A1_BASELINE": 0, "A2_RUNTIME": 0}
    worker_tokens = 0
    for call in run["task_calls"]:
        usage = call["invocation_receipt"].get("token_usage") or {}
        tokens = int(
            usage.get("total_tokens")
            or (
                int(usage.get("prompt_tokens") or 0)
                + int(usage.get("completion_tokens") or 0)
            )
        )
        if call["stage"] == "STANDARD_ONTOLOGY":
            standard_tokens[call["arm_id"]] += tokens
        else:
            worker_tokens += tokens
    diagnostics_commitment = {
        "diagnostic_version": "runtime_escalation_diagnostics_v0_33",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "trigger_receipt_count": len(run["trigger_receipts"]),
        "provisional_projection_count": len(
            run["provisional_projections"]
        ),
        "final_projection_count": len(run["final_projections"]),
        "standard_path_tokens": standard_tokens,
        "worker_tokens": worker_tokens,
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
    write(output / "runtime_escalation_diagnostics.json", diagnostics)
    posthoc = analyze_worker_uplift(
        corpus=corpus,
        run=run,
        formal_analysis=analysis,
    )
    write(output / "posthoc_worker_uplift.json", posthoc)

    metrics = analysis["pooled_contrast_metrics"]
    triggers = analysis["trigger_metrics"]
    report = "\n".join([
        "# Runtime escalation v0.33",
        "",
        "## Observed facts",
        (
            f"- Runtime-minus-A1 mean/median: {metrics['mean']:.3f}/"
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
            "- Prompt identity coverage: "
            f"{analysis['runtime_metrics']['prompt_identity_coverage']:.3f}."
        ),
        (
            "- Routes: "
            f"{json.dumps(triggers['route_distribution'], sort_keys=True)}."
        ),
        (
            "- Diagnostic flags: "
            + json.dumps(
                triggers["diagnostic_flag_distribution"],
                sort_keys=True,
            )
            + "."
        ),
        (
            "- Standard A1/A2 tokens: "
            f"{standard_tokens['A1_BASELINE']}/"
            f"{standard_tokens['A2_RUNTIME']}; "
            f"worker tokens: {worker_tokens}."
        ),
        (
            "- Counterfactual no-escalation mean/median: "
            f"{posthoc['counterfactual_no_escalation_contrast']['mean']:.3f}/"
            f"{posthoc['counterfactual_no_escalation_contrast']['median']:.3f}."
        ),
        (
            "- Triggered worker net uplift mean/median: "
            f"{posthoc['triggered_worker_net_uplift']['mean']:.3f}/"
            f"{posthoc['triggered_worker_net_uplift']['median']:.3f}."
        ),
        (
            "- Triggered worker gross candidate uplift mean/median: "
            f"{posthoc['triggered_worker_gross_candidate_uplift']['mean']:.3f}/"
            f"{posthoc['triggered_worker_gross_candidate_uplift']['median']:.3f}."
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
            "- A1 and A2 standard calls used identical Provider-visible "
            "objectives, schemas, inputs, and evidence scope."
        ),
        (
            "- Runtime derived every trigger from the ordinary receipt; no "
            "Provider-generated trigger text or trigger tokens were used."
        ),
        (
            "- Triggered cells paid for one specialized worker before final "
            "net Cbit scoring. Trigger rate was not an acceptance target."
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
        "ledger_version": "runtime_escalation_ledger_v0_33",
        "source_prior_analysis_hash": prior["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
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
        "replay_version": "runtime_escalation_replay_v0_33",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_runtime_escalation.py",
            "python examples/run_runtime_escalation.py",
            "python examples/finalize_runtime_escalation.py",
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
        "rollback_version": "runtime_escalation_rollback_v0_33",
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
        "closure_version": "runtime_escalation_closure_v0_33",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "runtime_escalation_gate": analysis["runtime_escalation_gate"],
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
        "source_v0_32_analysis.json",
        "source_v0_32_posthoc.json",
        "source_v0_32_closure.json",
        "runtime_escalation_corpus_frozen.json",
        "runtime_escalation_preregistration.json",
        "runtime_escalation_progress.json",
        "runtime_escalation_run.json",
        "runtime_escalation_analysis.json",
        "runtime_escalation_diagnostics.json",
        "posthoc_worker_uplift.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "runtime_escalation_inventory_v0_33",
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
    return_pack = output / "runtime_escalation_v0_33_return_pack.zip"
    zip_pack(
        return_pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "runtime_escalation_manifest_v0_33",
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
