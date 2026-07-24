"""Close and package the v0.27 frontier-gray fresh holdout."""

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
    output = REPO_ROOT / "outputs" / "frontier_fresh_v0_27"
    preflight = read(output / "source_preflight_analysis.json")
    corpus = read(output / "frontier_corpus_frozen.json")
    prereg = read(output / "frontier_preregistration.json")
    run = read(output / "frontier_run.json")
    analysis = read(output / "frontier_analysis.json")
    ledger = analysis["realized_cbit_ledger"]
    runtime = analysis["arm_runtime_metrics"]
    cbit = ledger["arm_metrics"]
    lane_summaries = {}
    for arm_id in ("A0_DIRECT", "A1_ONTOLOGY"):
        for lane in ("CORE", "FRONTIER"):
            entries = [
                value for value in ledger["entries"]
                if value["arm_id"] == arm_id and value["lane"] == lane
            ]
            lane_summaries[f"{arm_id}:{lane}"] = {
                "candidate_count": len(entries),
                "supported_target_count": sum(
                    value["outcome_state"] == "SUPPORTED_TARGET"
                    for value in entries
                ),
                "informative_null_count": sum(
                    value["outcome_state"] == "INFORMATIVE_NULL"
                    for value in entries
                ),
                "unresolved_count": sum(
                    value["outcome_state"] == "UNRESOLVED"
                    for value in entries
                ),
                "mean_realized_effective_cbit": round(
                    sum(
                        value["realized_effective_cbit"]
                        for value in entries
                    ) / len(entries),
                    6,
                ) if entries else 0.0,
            }

    diagnostics = {
        "diagnostic_version": "frontier_gray_diagnostics_v0_27",
        "source_run_hash": run["run_hash"],
        "raw_receipt_count": len(run["raw_receipts"]),
        "projection_count": len(run["projections"]),
        "provider_failure_records": run["failures"],
        "raw_receipts_preserved": (
            run["raw_receipts_preserved_before_projection"] is True
        ),
        "receipt_state_counts": {
            arm_id: cbit[arm_id]["receipt_state_counts"]
            for arm_id in cbit
        },
        "quarantined_component_counts": {
            arm_id: runtime[arm_id]["quarantined_component_count"]
            for arm_id in runtime
        },
        "frontier_candidate_counts": {
            arm_id: cbit[arm_id]["frontier_candidate_count"]
            for arm_id in cbit
        },
        "lane_summaries": lane_summaries,
        "lane_specific_score_weights_present": False,
        "external_semantic_panel_present": False,
        "synthetic_outcomes_are_real_world_truth": False,
    }
    diagnostics["artifact_hash"] = hash_payload(diagnostics)
    write(output / "frontier_diagnostics.json", diagnostics)

    table = [
        "| Arm | Complete | Nonblock | Eligible | Frontier | Supported | Informative null | Cbit/case | Cbit/1k tokens |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm_id in ("A0_DIRECT", "A1_ONTOLOGY"):
        table.append(
            f"| {arm_id} | "
            f"{runtime[arm_id]['provider_completion_coverage']:.3f} | "
            f"{runtime[arm_id]['nonblock_projection_coverage']:.3f} | "
            f"{cbit[arm_id]['eligible_candidate_count']} | "
            f"{cbit[arm_id]['frontier_candidate_count']} | "
            f"{cbit[arm_id]['supported_target_count']} | "
            f"{cbit[arm_id]['informative_null_count']} | "
            f"{cbit[arm_id]['mean_effective_cbit_per_case']:.3f} | "
            f"{cbit[arm_id]['realized_cbit_per_1k_tokens']:.3f} |"
        )
    observations = [
        (
            f"{len(run['raw_receipts'])}/{len(run['task_calls'])} Provider "
            "receipts were preserved before projection."
        ),
        (
            f"A0/A1 nonblock coverage was "
            f"{runtime['A0_DIRECT']['nonblock_projection_coverage']:.3f}/"
            f"{runtime['A1_ONTOLOGY']['nonblock_projection_coverage']:.3f}."
        ),
        (
            f"The A1 realized Cbit gain per case was "
            f"{analysis['a1_cbit_gain_per_case']} and its efficiency ratio "
            f"to A0 was {analysis['a1_cbit_efficiency_ratio_to_a0']}."
        ),
        (
            f"The run consumed {analysis['total_tokens']} tokens against a "
            f"frozen budget of "
            f"{prereg['success_gate']['maximum_total_tokens']}."
        ),
        (
            "A1 FRONTIER candidates produced "
            f"{lane_summaries['A1_ONTOLOGY:FRONTIER']['supported_target_count']} "
            "supported targets, "
            f"{lane_summaries['A1_ONTOLOGY:FRONTIER']['informative_null_count']} "
            "informative nulls, and "
            f"{lane_summaries['A1_ONTOLOGY:FRONTIER']['unresolved_count']} "
            "unresolved outcomes."
        ),
    ]
    if analysis["frontier_holdout_gate"] == "PASS":
        phenomena = [
            "Arm-native schemas restored a valid A0/A1 comparison while field-level gray admission preserved usable candidates.",
            "Ontology-first cognition improved realized Cbit without requiring a lane-specific reward for frontier candidates.",
        ]
        interpretation = [
            "Inference: compact object expansion is useful when it feeds a common problem projection instead of forcing every arm through one large schema.",
            "Inference: bounded speculative candidates can coexist with core candidates when falsifiability and outcome accounting remain shared.",
        ]
        next_step = (
            "Generate an independent external semantic panel for question "
            "quality and edge-value before any A2 graph experiment."
        )
    elif (
        analysis["comparison_valid"]
        and all(
            value for key, value in analysis["conditions"].items()
            if key != "maximum_total_tokens"
        )
        and analysis["conditions"]["maximum_total_tokens"] is False
    ):
        phenomena = [
            "A1 increased realized Cbit per case and won on nine of twelve objects, but the run exceeded the frozen budget.",
            "A1 and A0 had nearly identical Cbit per token, so ontology increased cognitive quantity without demonstrating higher cognitive productivity.",
            "A1 frontier candidates were as productive as its core candidates under identical score weights, supporting bounded edge exploration rather than a frontier bonus.",
        ]
        interpretation = [
            "Inference: compact object structure helps the Provider generate fewer unresolved and more informative edge hypotheses.",
            "Inference: the next bottleneck is representation compression; the ontology benefit currently costs approximately proportional extra tokens.",
        ]
        next_step = (
            "Stop v0.27 under its frozen budget. Preserve the positive mechanism "
            "signal and test a compact ontology projection on another fresh "
            "holdout before any graph or multi-agent expansion."
        )
    else:
        phenomena = [
            "The gray-admission experiment did not clear all preregistered comparison, Cbit, efficiency, coverage, and budget gates.",
            "Partial admission preserved negative evidence, but no mechanism promotion is authorized.",
        ]
        interpretation = [
            "Inference: either ontology-first expansion did not improve effective cognition, or remaining receipt and cost friction masked its value.",
            "Inference: frontier tolerance alone cannot substitute for a stronger problem-selection policy.",
        ]
        next_step = (
            "Stop v0.27 and diagnose the frozen receipts without tuning on "
            "these twelve outcomes; any repair requires another fresh holdout."
        )
    report = "\n".join([
        "# Frontier gray admission and realized Cbit v0.27",
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
        "## Boundaries",
        "- CORE and FRONTIER candidates used exactly the same realized Cbit weights.",
        "- An informative null can earn positive Cbit by pruning problem space.",
        "- Weak evidence was tolerated only as an explicit speculative component with a falsifier and required observation.",
        "- Synthetic outcome metadata is not real-world truth and cannot enter retention or baseline.",
        "",
        "## Intuition prompts",
        "- Did the frontier lane identify a genuinely different object relation or merely relabel a weak core question?",
        "- Did partial admission recover useful cognition that whole-receipt validation would have destroyed?",
        "- Is the ontology gain caused by better object choice, better constraint recall, or compression of the search space?",
        "",
        "## Next step",
        next_step,
        "",
        f"Candidate state: `{analysis['candidate_state']}`.",
        "Core integration remains unauthorized.",
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )

    ledger_commitment = {
        "ledger_version": "frontier_gray_closure_ledger_v0_27",
        "source_preflight_analysis_hash": preflight["artifact_hash"],
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_realized_cbit_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "frontier_holdout_gate": analysis["frontier_holdout_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    closure_ledger = {
        **ledger_commitment,
        "artifact_hash": hash_payload(ledger_commitment),
    }
    write(output / "ledger.json", closure_ledger)

    replay_commitment = {
        "replay_version": "frontier_gray_replay_v0_27",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/run_frontier_preflight.py",
            "python examples/prepare_frontier_fresh_holdout.py",
            "python examples/run_frontier_fresh_holdout.py",
            "python examples/finalize_frontier_fresh_holdout.py",
            "pytest -q tests/test_frontier_gray_experiment.py",
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
        "rollback_version": "frontier_gray_rollback_v0_27",
        "isolated_output_directory": str(output),
        "rollback_action": (
            "Remove only this isolated experiment output directory."
        ),
        "agentos_core_files_touched": False,
        "retention_or_baseline_mutation_performed": False,
        "previous_candidate_state": "STRUCTURE_FIRST_SMOKE_REJECTED_STOP",
    }
    rollback = {
        **rollback_commitment,
        "artifact_hash": hash_payload(rollback_commitment),
    }
    write(output / "rollback_pointer.json", rollback)

    closure_commitment = {
        "closure_version": "frontier_gray_closure_v0_27",
        "source_ledger_hash": closure_ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "frontier_holdout_gate": analysis["frontier_holdout_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
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
        "source_preflight_analysis.json",
        "frontier_corpus_frozen.json",
        "frontier_preregistration.json",
        "frontier_progress.json",
        "frontier_run.json",
        "frontier_analysis.json",
        "frontier_diagnostics.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "frontier_gray_inventory_v0_27",
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
    return_pack = output / "frontier_gray_v0_27_return_pack.zip"
    deterministic_zip(
        return_pack,
        [output / name for name in [*inventory_names, "hash_inventory.json"]],
    )
    manifest_commitment = {
        "manifest_version": "frontier_gray_manifest_v0_27",
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
        "frontier_holdout_gate": analysis["frontier_holdout_gate"],
        "external_semantic_panel_authorized": analysis[
            "external_semantic_panel_authorized"
        ],
        "core_integration_authorized": False,
        "return_pack": str(return_pack),
        "return_pack_sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
