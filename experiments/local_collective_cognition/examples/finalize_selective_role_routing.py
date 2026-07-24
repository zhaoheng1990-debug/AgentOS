"""Close and package the v0.30 selective role-routing experiment."""

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
from local_collective_cognition.selective_role_routing_posthoc import (  # noqa: E402
    analyze_routing_posthoc,
)


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
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "selective_role_routing_v0_30"
    prior_analysis = read(output / "source_v0_29_analysis.json")
    prior_posthoc = read(output / "source_v0_29_posthoc.json")
    prior_closure = read(output / "source_v0_29_closure.json")
    corpus = read(
        output / "selective_role_routing_corpus_frozen.json"
    )
    prereg = read(
        output / "selective_role_routing_preregistration.json"
    )
    run = read(output / "selective_role_routing_run.json")
    analysis = read(output / "selective_role_routing_analysis.json")
    posthoc = analyze_routing_posthoc(run=run, analysis=analysis)
    write(output / "posthoc_cost_route_decomposition.json", posthoc)
    failed_conditions = sorted(
        key for key, value in analysis["conditions"].items()
        if value is False
    )
    diagnostics_commitment = {
        "diagnostic_version": "selective_role_routing_diagnostics_v0_30",
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "route_receipt_count": len(run["route_receipts"]),
        "expected_route_receipt_count": (
            corpus["case_count"] * len(corpus["replication_ids"])
        ),
        "provider_failure_records": run["failures"],
        "runtime_metrics": analysis["runtime_metrics"],
        "pooled_contrast_metrics": analysis[
            "pooled_contrast_metrics"
        ],
        "majority_positive_case_rate": analysis[
            "majority_positive_case_rate"
        ],
        "relation_reproducibility": analysis[
            "relation_reproducibility"
        ],
        "route_distribution": analysis["route_distribution"],
        "shadow_regret_audit": analysis["shadow_regret_audit"],
        "posthoc_cost_route_decomposition_hash": posthoc[
            "artifact_hash"
        ],
        "failed_frozen_conditions": failed_conditions,
        "cost": {
            "formal_path_tokens": analysis["formal_path_tokens"],
            "shadow_audit_tokens": analysis["shadow_audit_tokens"],
            "physical_total_tokens": analysis[
                "physical_total_tokens"
            ],
            "soft_cost_warning": analysis["soft_cost_warning"],
            "formal_path_cost_accounting_complete": analysis[
                "conditions"
            ]["formal_path_cost_accounting_complete"],
        },
        "external_semantic_panel_present": False,
        "cross_provider_stability_established": False,
        "synthetic_outcomes_are_real_world_truth": False,
    }
    diagnostics = {
        **diagnostics_commitment,
        "artifact_hash": hash_payload(diagnostics_commitment),
    }
    write(output / "selective_role_routing_diagnostics.json", diagnostics)

    rows = [
        "| Rep | A1 Cbit/case | Routed Cbit/case | Mean gain | Median gain | Wins | A1 tokens | Routed tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for replication_id, metric in analysis[
        "replication_metrics"
    ].items():
        contrast = metric["contrast"]
        rows.append(
            f"| {replication_id} | {metric['a1_cbit_per_case']:.3f} | "
            f"{metric['a2_cbit_per_case']:.3f} | "
            f"{contrast['mean']:.3f} | {contrast['median']:.3f} | "
            f"{contrast['win_count']}/{contrast['count']} | "
            f"{metric['a1_total_tokens']} | "
            f"{metric['a2_total_tokens']} |"
        )
    pooled = analysis["pooled_contrast_metrics"]
    shadow = analysis["shadow_regret_audit"]
    if analysis["selective_routing_gate"] == "PASS":
        phenomena = [
            "Provider-backed routing converted role specialization into majority-stable net Cbit using one selected worker.",
            "The gain survived router-token charging and relation-reproducibility gates.",
            "Shadow regret identifies remaining route-selection headroom without changing the formal pass.",
        ]
        next_step = (
            "Generate an independent external semantic panel for route "
            "rationales and candidate quality before any CoreSlim candidate."
        )
    elif analysis["decision"] == "STOP_RESOURCE_RUNAWAY":
        phenomena = [
            "The run crossed the frozen physical resource cap.",
            "No routing claim is authorized.",
        ]
        next_step = "Stop and inspect transport and response-length tails."
    else:
        phenomena = [
            "Selective routing failed at least one frozen net-Cbit or stability condition.",
            "Shadow regret separates route-selection error from worker capability and cost.",
            "No route criteria or thresholds were changed after freeze.",
        ]
        next_step = (
            "Stop v0.30 and use fresh-data shadow regret to choose between "
            "router calibration, route-native contracts, or a no-escalation "
            "confidence gate."
        )
    report = "\n".join([
        "# Provider-backed selective role routing v0.30",
        "",
        "## Observed facts",
        (
            f"- {len(run['route_receipts'])}/"
            f"{diagnostics['expected_route_receipt_count']} routing "
            "receipts were valid."
        ),
        (
            f"- Routed-minus-A1 mean/median: {pooled['mean']:.3f}/"
            f"{pooled['median']:.3f}; win rate {pooled['win_rate']:.3f}."
        ),
        (
            "- Majority-positive case rate: "
            f"{analysis['majority_positive_case_rate']:.3f}."
        ),
        (
            "- Baseline/routed relation Jaccard: "
            f"{analysis['relation_reproducibility']['A1_BASELINE']['mean_pairwise_relation_jaccard']:.3f}/"
            f"{analysis['relation_reproducibility']['A2_ROUTED']['mean_pairwise_relation_jaccard']:.3f}."
        ),
        (
            f"- Shadow top-1 route accuracy: "
            f"{shadow['top1_or_tied_accuracy']:.3f}; mean/median regret "
            f"{shadow['mean_regret']:.3f}/{shadow['median_regret']:.3f}."
        ),
        (
            f"- Formal/shadow/physical tokens: "
            f"{analysis['formal_path_tokens']}/"
            f"{analysis['shadow_audit_tokens']}/"
            f"{analysis['physical_total_tokens']}."
        ),
        (
            "- Posthoc router cost and worker-only mean delta: "
            f"{posthoc['router_token_cost_per_case']['mean']:.3f}/"
            f"{posthoc['selected_worker_delta_excluding_router_cost']['mean']:.3f}."
        ),
        (
            "- Posthoc R3 best-route oracle mean gain versus baseline: "
            f"{posthoc['shadow_oracle_mean_gain_vs_baseline']:.3f}."
        ),
        (
            "- Failed frozen conditions: "
            + (", ".join(failed_conditions) if failed_conditions else "none")
            + "."
        ),
        "",
        *rows,
        "",
        "## Phenomena",
        *[f"- {value}" for value in phenomena],
        "",
        "## Interpretation boundary",
        "- Posthoc cost decomposition and shadow oracle do not change the frozen decision.",
        "- Router and selected-worker tokens are both charged to A2.",
        "- Shadow counterfactual calls are excluded from deployment-path Cbit but included in the physical resource cap.",
        "- Shadow best-route labels use private synthetic outcomes posthoc and cannot train or promote a runtime policy in this round.",
        "- Synthetic outcomes are not real-world truth or cross-provider validation.",
        "- No CoreSlim, retention, baseline, selection, or production write occurred.",
        "",
        "## Intuition prompts",
        "- Does the router select a specialized role only when its expected gain exceeds router cost?",
        "- Are errors caused by route choice or by a role-native worker contract?",
        "- Can a confidence gate preserve A1 when route regret is likely to be high?",
        "",
        "## Next step",
        next_step,
        "",
        f"Decision: `{analysis['decision']}`.",
        f"Candidate state: `{analysis['candidate_state']}`.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    ledger_commitment = {
        "ledger_version": "selective_role_routing_closure_ledger_v0_30",
        "source_prior_analysis_hash": prior_analysis["artifact_hash"],
        "source_prior_posthoc_hash": prior_posthoc["artifact_hash"],
        "source_prior_closure_hash": prior_closure["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_replication_ledger_hashes": {
            key: value["artifact_hash"]
            for key, value in analysis["replication_ledgers"].items()
        },
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
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
        "replay_version": "selective_role_routing_replay_v0_30",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_selective_role_routing.py",
            "python examples/run_selective_role_routing.py",
            "python examples/finalize_selective_role_routing.py",
            "pytest -q tests/test_selective_role_routing_experiment.py",
        ],
        "provider_model": run["model_id"],
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
        "rollback_version": "selective_role_routing_rollback_v0_30",
        "isolated_output_directory": str(output),
        "rollback_action": (
            "Remove only this isolated experiment output directory."
        ),
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
        "previous_candidate_state": prior_closure["candidate_state"],
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "selective_role_routing_closure_v0_30",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "selective_routing_gate": analysis["selective_routing_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "cross_provider_stability_established": False,
        "core_integration_authorized": False,
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
        "source_v0_29_analysis.json",
        "source_v0_29_posthoc.json",
        "source_v0_29_closure.json",
        "selective_role_routing_corpus_frozen.json",
        "selective_role_routing_preregistration.json",
        "selective_role_routing_progress.json",
        "selective_role_routing_run.json",
        "selective_role_routing_analysis.json",
        "selective_role_routing_diagnostics.json",
        "posthoc_cost_route_decomposition.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "selective_role_routing_inventory_v0_30",
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
    return_pack = (
        output / "selective_role_routing_v0_30_return_pack.zip"
    )
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "selective_role_routing_manifest_v0_30",
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
        "decision": analysis["decision"],
        "selective_routing_gate": analysis["selective_routing_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
