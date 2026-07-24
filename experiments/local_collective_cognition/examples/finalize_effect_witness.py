"""Close and package v0.56 negative result."""

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


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def zip_pack(path, files):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(files, key=lambda value: value.name):
            info = zipfile.ZipInfo(source.name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, source.read_bytes())


def main():
    output = REPO_ROOT / "outputs" / "effect_witness_v0_56"
    corpus = read(output / "effect_witness_corpus_frozen.json")
    audit = read(output / "reference_completeness_audit.json")
    prereg = read(output / "effect_witness_preregistration.json")
    run = read(output / "effect_witness_run.json")
    analysis = read(output / "effect_witness_analysis.json")
    posthoc = read(output / "posthoc_effect_witness.json")
    failed = sorted(
        key for key, value in analysis["conditions"].items()
        if not value
    )
    report = "\n".join([
        "# EFFECT witness dual-axis experiment v0.56",
        "",
        "## Observed result",
        (
            f"- Reference audit: {audit['valid_receipt_count']}/"
            f"{audit['required_receipt_count']} valid, with zero mismatch "
            "and zero cross-role disagreement."
        ),
        (
            f"- Formal decision: `{analysis['decision']}`; tokens "
            f"{analysis['physical_total_tokens']}."
        ),
        (
            f"- Valid proposals: "
            f"{analysis['replacement_gate_metrics']['receipt_count']}; "
            f"accepted: "
            f"{analysis['replacement_gate_metrics']['accepted_count']}."
        ),
        (
            f"- EFFECT proposals: 11; EFFECT accepted: "
            f"{analysis['effect_witness_metrics']['effect_lane_accepted_count']}."
        ),
        (
            "- Private posthoc: "
            + ", ".join(
                f"{key}={value}" for key, value in sorted(
                    posthoc["classification_distribution"].items()
                )
            )
            + "."
        ),
        (
            "- Failed frozen conditions: "
            + ", ".join(failed)
            + "."
        ),
        "",
        "## Analysis",
        (
            "- The EFFECT-rich construction succeeded at eliciting EFFECT "
            "proposals, so proposal scarcity is not the bottleneck."
        ),
        (
            "- Every EFFECT proposal was a realized-Cbit tie against the "
            "active base portfolio. The holdout made effects abundant but "
            "did not create omitted, higher-value effects under capacity."
        ),
        (
            "- Five supported-null protections blocked only ties. The guard "
            "caused no observed beneficial miss on this surface."
        ),
        (
            "- Independent witness organization added no Provider calls, but "
            "there was no beneficial EFFECT candidate for it to recover. "
            "The experiment therefore cannot validate or falsify witness "
            "utility; it rejects this holdout construction as an informative "
            "test of marginal EFFECT admission."
        ),
        (
            "- One unsupported base relation occurrence also violated the "
            "frozen zero-drift gate. No thresholds or prompts may be retuned "
            "on these revealed cases."
        ),
        (
            "- The next holdout must freeze portfolio scarcity explicitly: "
            "the base surface should contain more valid relations than its "
            "three-slot capacity, while hiding which omitted relation has "
            "higher marginal Cbit. That object is different from merely "
            "increasing EFFECT prevalence."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    ledger = artifact({
        "ledger_version": "effect_witness_ledger_v0_56",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_reference_audit_hash": audit["artifact_hash"],
        "source_preregistration_hash": prereg["artifact_hash"],
        "source_run_hash": run["run_hash"],
        "source_analysis_hash": analysis["artifact_hash"],
        "source_posthoc_hash": posthoc["artifact_hash"],
        "decision": analysis["decision"],
        "candidate_state": analysis["candidate_state"],
        "failed_attempt_record": "failed_attempts.json",
        "core_integration_authorized": False,
    })
    write(output / "ledger.json", ledger)
    replay = artifact({
        "replay_version": "effect_witness_replay_v0_56",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python examples/prepare_effect_witness.py",
            "python examples/run_effect_witness_audit.py",
            "python examples/freeze_effect_witness.py",
            "python examples/run_effect_witness.py",
            "python examples/analyze_effect_witness_posthoc.py",
            "python examples/finalize_effect_witness.py",
        ],
        "provider_model": run["model_id"],
        "warning": "Replay creates new Provider evidence.",
    })
    write(output / "replay.json", replay)
    rollback = artifact({
        "rollback_version": "effect_witness_rollback_v0_56",
        "isolated_output_directory": str(output),
        "rollback_action": "Remove only this isolated output directory.",
        "agentos_core_files_touched": False,
    })
    write(output / "rollback_pointer.json", rollback)
    closure = artifact({
        "closure_version": "effect_witness_closure_v0_56",
        "source_ledger_hash": ledger["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "diagnosis": "EFFECT_PREVALENCE_WITHOUT_MARGINAL_SCARCITY",
        "witness_utility_resolved": False,
        "promotion_allowed": False,
        "core_integration_authorized": False,
    })
    write(output / "closure.json", closure)
    names = [
        "source_v0_54_preregistration.json",
        "source_v0_54_analysis.json",
        "source_v0_54_closure.json",
        "source_v0_54_posthoc.json",
        "source_v0_55_closure.json",
        "source_dual_axis_gate_candidate.json",
        "effect_witness_corpus_frozen.json",
        "reference_completeness_audit.json",
        "effect_witness_preregistration.json",
        "failed_attempts.json",
        "effect_witness_run.json",
        "effect_witness_analysis.json",
        "posthoc_effect_witness.json",
        "experiment_report.md",
        "ledger.json",
        "replay.json",
        "rollback_pointer.json",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "effect_witness_inventory_v0_56",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "effect_witness_v0_56_return_pack.zip"
    zip_pack(
        pack,
        [output / name for name in names + ["hash_inventory.json"]],
    )
    manifest = artifact({
        "manifest_version": "effect_witness_manifest_v0_56",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "diagnosis": closure["diagnosis"],
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
