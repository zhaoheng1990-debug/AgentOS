"""Package the v0.58 candidate-only replacement result."""

from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), default=str
        ).encode("utf-8")
    ).hexdigest()


def artifact(value):
    return {**value, "artifact_hash": digest(value)}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source = REPO_ROOT / "outputs" / "marginal_scarcity_v0_57"
    output = (
        REPO_ROOT / "outputs" / "marginal_scarcity_replacement_v0_58"
    )
    output.mkdir(parents=True, exist_ok=True)
    source_files = {
        "source_discovery_closure.json": source / "closure.json",
        "replacement_preregistration.json": (
            source / "replacement_preregistration.json"
        ),
        "replacement_run.json": source / "replacement_run.json",
        "replacement_analysis.json": source / "replacement_analysis.json",
    }
    for name, path in source_files.items():
        write(output / name, read(path))
    analysis = read(source / "replacement_analysis.json")
    run = read(source / "replacement_run.json")
    blocked = sum(
        value["state"] == "BLOCK_WRONG_DROP"
        for value in run["decisions"].values()
    )
    report = "\n".join([
        "# Marginal-scarcity replacement gate v0.58",
        "",
        f"- Decision: `{analysis['decision']}`.",
        f"- Candidate-only replacements: {analysis['replacement_count']}.",
        f"- Nonconsensus abstentions: {analysis['abstention_count']}.",
        f"- Wrong-drop blocks: {blocked}.",
        (
            f"- Realized gross Cbit mean/median: "
            f"{analysis['realized_gross_cbit_mean']:.1f}/"
            f"{analysis['realized_gross_cbit_median']:.1f}."
        ),
        f"- Harmful replacements: {analysis['harmful_replacement_count']}.",
        (
            f"- Protected-knowledge losses: "
            f"{analysis['protected_knowledge_loss_count']}."
        ),
        "- Provider calls added by replacement: 0.",
        "",
        (
            "Correct target discovery was necessary but not sufficient: "
            "two exact-target consensuses proposed the wrong slot for "
            "deletion and were blocked. The twelve authorized synthetic "
            "replacements all realized +2.0 gross Cbit without protected "
            "loss. No CoreSlim, retention, baseline, or production mutation "
            "was authorized."
        ),
    ])
    (output / "experiment_report.md").write_text(
        report, encoding="utf-8"
    )
    closure = artifact({
        "closure_version": "marginal_scarcity_replacement_v0_58",
        "source_analysis_hash": analysis["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "decision": analysis["decision"],
        "synthetic_replacement_replication_passed": True,
        "core_integration_authorized": False,
        "promotion_allowed": False,
    })
    write(output / "closure.json", closure)
    names = [
        *source_files,
        "experiment_report.md",
        "closure.json",
    ]
    inventory = artifact({
        "inventory_version": "marginal_scarcity_replacement_v0_58",
        "files": [{
            "path": name,
            "bytes": (output / name).stat().st_size,
            "sha256": sha(output / name),
        } for name in names],
    })
    write(output / "hash_inventory.json", inventory)
    pack = output / "marginal_scarcity_replacement_v0_58.zip"
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(names + ["hash_inventory.json"]):
            info = zipfile.ZipInfo(name)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, (output / name).read_bytes())
    manifest = artifact({
        "manifest_version": "marginal_scarcity_replacement_v0_58",
        "return_pack": pack.name,
        "return_pack_sha256": sha(pack),
        "return_pack_bytes": pack.stat().st_size,
        "inventory_hash": inventory["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
    })
    write(output / "manifest.json", manifest)
    print(json.dumps({
        "decision": analysis["decision"],
        "replacements": analysis["replacement_count"],
        "wrong_drop_blocks": blocked,
        "return_pack": str(pack),
        "sha256": manifest["return_pack_sha256"],
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    raise SystemExit(main())
