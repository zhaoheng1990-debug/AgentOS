"""Finalize blind v0.17 artifacts without claiming semantic gain."""

from __future__ import annotations

import hashlib
import json
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_axis_panel import build_axis_external_panel, validate_axis_external_panel  # noqa: E402
from local_collective_cognition.cognitive_action_axis_routing import analyze_axis_routing_run, build_axis_external_annotation_pack  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    output = REPO_ROOT / "outputs" / "axis_credibility_routing_v0_17"
    corpus = read(output / "axis_fresh_corpus_frozen.json")
    preregistration = read(output / "axis_routing_preregistration.json")
    role_run = read(output / "axis_role_run.json")
    role_analysis = read(output / "axis_role_analysis.json")
    run = read(output / "axis_routing_run.json")
    analysis = analyze_axis_routing_run(corpus=corpus, role_analysis=role_analysis, run=run)
    write(output / "axis_routing_analysis.json", analysis)
    annotation_pack = build_axis_external_annotation_pack(corpus=corpus, run=run)
    write(output / "axis_external_annotation_pack.json", annotation_pack)
    lane_packs, panel_manifest = build_axis_external_panel(corpus=corpus, run=run)
    validate_axis_external_panel(packs=lane_packs, manifest=panel_manifest, corpus=corpus, run=run)
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in lane_packs:
        name = f"{pack['lane_id']}_axis_routing_annotation_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    write(panel_dir / "axis_routing_external_panel_manifest.json", panel_manifest)

    report = render_analysis(role_analysis=role_analysis, analysis=analysis, run=run)
    (output / "AXIS_CREDIBILITY_ROUTING_ANALYSIS.md").write_text(report, encoding="utf-8")
    ledger_commitment = {
        "ledger_version": "axis_credibility_routing_phase_ledger_v0_17",
        "methodology_kernel": "v1.1",
        "phases": [
            {"phase": "G0_PREREGISTRATION", "status": "PASS", "hash": preregistration["artifact_hash"]},
            {"phase": "G1_FRESH_HOLDOUT", "status": "PASS", "hash": corpus["artifact_hash"], "case_count": corpus["case_count"]},
            {"phase": "G2_LOCAL_ROLES", "status": "PASS" if role_analysis["tuple_inference_allowed"] else "FAIL", "coverage": role_analysis["strict_receipt_coverage"]},
            {"phase": "G3_BLIND_AXIS_ROUTING", "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL" if "AWAITING_EXTERNAL_PANEL" in analysis["candidate_state"] else "FAIL", "coverage": analysis["coverage"]},
            {"phase": "G4_EXTERNAL_REFERENCE", "status": "PENDING", "panel_id": panel_manifest["panel_id"]},
        ],
        "observed_objects": ["axis-specific source assignment", "contrastive basis classification", "mechanical tuple-coherence fusion"],
        "pending_objects": ["fresh semantic correctness", "primary-axis correction/harm balance", "Cbit per token", "anti-additive gate"],
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {**ledger_commitment, "artifact_hash": hash_payload(ledger_commitment)}
    write(output / "phase_ledger.json", ledger)
    replay_commitment = {
        "pointer_version": "axis_credibility_routing_replay_v0_17",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python -m pytest -q --basetemp=.pytest_tmp_axis_replay",
            "python examples/prepare_axis_credibility_routing.py",
            "conda run -n dhrf_4080s python examples/run_axis_credibility_roles.py",
            "python examples/run_axis_credibility_routing.py",
            "python examples/finalize_axis_credibility_routing.py",
        ],
        "external_panel_next": "Submit the two lane-specific packs independently to GPT-5.6 and Gemini 3.1, then use Kimi K3 for whole-tuple disagreements.",
        "reference_revision_allowed": False,
    }
    replay = {**replay_commitment, "artifact_hash": hash_payload(replay_commitment)}
    write(output / "replay_pointer.json", replay)
    rollback_commitment = {
        "pointer_version": "axis_credibility_routing_rollback_v0_17",
        "scope": "experiment-only; AgentOS CoreSlim is outside the change boundary",
        "output_directory": str(output),
        "code_prefixes": ["cognitive_action_axis_", "prepare_axis_credibility_", "run_axis_credibility_", "finalize_axis_credibility_"],
        "rollback_action": "quarantine the v0.17 experiment files and output directory after verifying hashes; do not alter CoreSlim or earlier experiments",
        "automatic_rollback_executed": False,
        "retention_authority": False,
    }
    rollback = {**rollback_commitment, "artifact_hash": hash_payload(rollback_commitment)}
    write(output / "rollback_pointer.json", rollback)

    inventory_names = [
        "axis_routing_preregistration.json", "axis_fresh_corpus_frozen.json", "axis_role_plan.json",
        "axis_role_run.json", "axis_role_analysis.json", "axis_routing_run.json", "axis_routing_analysis.json",
        "axis_routing_telemetry.json", "axis_external_annotation_pack.json", "AXIS_CREDIBILITY_ROUTING_ANALYSIS.md",
        "phase_ledger.json", "replay_pointer.json", "rollback_pointer.json",
    ] + [f"external_panel/{name}" for name in lane_names] + ["external_panel/axis_routing_external_panel_manifest.json"]
    for optional in ("axis_routing_run_pre_recovery.json", "axis_routing_recovery_telemetry.json"):
        if (output / optional).is_file():
            inventory_names.append(optional)
    inventory_commitment = {
        "inventory_version": "axis_credibility_routing_hash_inventory_v0_17",
        "items": [
            {"path": name, "size_bytes": (output / name).stat().st_size, "sha256": sha256_file(output / name)}
            for name in inventory_names
        ],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(output / "hash_inventory.json", inventory)
    manifest_commitment = {
        "manifest_version": "axis_credibility_routing_manifest_v0_17",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "role_run_hash": role_run["run_hash"],
        "axis_run_hash": run["run_hash"],
        "axis_analysis_hash": analysis["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "hash_inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "collective_gain_claim_allowed": False,
        "baseline_promotion_allowed": False,
        "retention_write_allowed": False,
    }
    manifest = {**manifest_commitment, "artifact_hash": hash_payload(manifest_commitment)}
    write(output / "manifest.json", manifest)

    pack_path = output / "axis_credibility_routing_external_panel_v0_17_return_pack.zip"
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in lane_names:
            archive.write(panel_dir / name, arcname=name)
        archive.write(panel_dir / "axis_routing_external_panel_manifest.json", arcname="PRIVATE_axis_routing_external_panel_manifest.json")
        archive.write(output / "axis_routing_preregistration.json", arcname="axis_routing_preregistration.json")
        archive.write(output / "AXIS_CREDIBILITY_ROUTING_ANALYSIS.md", arcname="AXIS_CREDIBILITY_ROUTING_ANALYSIS.md")
        archive.write(output / "manifest.json", arcname="manifest.json")
        archive.write(output / "hash_inventory.json", arcname="hash_inventory.json")
    print(json.dumps({
        "manifest_hash": manifest["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "panel_id": panel_manifest["panel_id"],
        "panel_pack_hashes": panel_manifest["lane_pack_hashes"],
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def render_analysis(*, role_analysis, analysis, run):
    disagreements = analysis["baseline_coordinator_axis_disagreements"]
    basis_sources = analysis["basis_source_counts"]
    tuple_outputs = {(output["arm"], output["conflict_id"]): output["payload"] for output in run["tuple_outputs"]}
    baseline = [payload for (arm, _), payload in tuple_outputs.items() if arm == "SINGLE_MODEL_BASELINE"]
    coordinator = [payload for (arm, _), payload in tuple_outputs.items() if arm == "ROLE_INFORMED_COORDINATOR"]
    routed = [output["payload"] for output in run["routed_outputs"]]
    baseline_selected = dict(Counter(payload["selected_object"] for payload in baseline))
    coordinator_selected = dict(Counter(payload["selected_object"] for payload in coordinator))
    baseline_preference = dict(Counter(payload["pragmatic_preference"] for payload in baseline))
    coordinator_preference = dict(Counter(payload["pragmatic_preference"] for payload in coordinator))
    critic_basis = dict(Counter(
        output["selection_basis"] for output in run["basis_outputs"]
        if output["basis_source"] == "CONTRASTIVE_BASIS_CRITIC"
    ))
    routed_basis = dict(Counter(payload["selection_basis"] for payload in routed))
    observations = [
        f"Local role receipt coverage is {role_analysis['strict_receipt_coverage']:.3f} across 72 assignments.",
        f"Blind arm coverage is {analysis['coverage']} with {len(run['failures'])} recorded failures.",
        f"Baseline and coordinator disagree on selected object {disagreements['selected_object']}/24, basis {disagreements['selection_basis']}/24, preference {disagreements['pragmatic_preference']}/24, and completeness {disagreements['assessment_completeness']}/24.",
        f"Basis sources are {basis_sources}; provider calls are skipped when coherence follows mechanically from open or uncertain states.",
        f"Baseline selected-object distribution is {baseline_selected}; coordinator distribution is {coordinator_selected}.",
        f"Baseline preference distribution is {baseline_preference}; coordinator distribution is {coordinator_preference}.",
        f"The contrastive basis critic distribution is {critic_basis}; routed basis distribution is {routed_basis}.",
        f"Tuple fusion applied {analysis['fusion_override_count']} explicit fail-closed coherence overrides.",
        f"The Runtime rejected {analysis['failed_invocation_receipt_count']} provider invocations; their work remains charged as {analysis['failed_invocation_accounting']}.",
        f"The full routed path accounts for {analysis['routed_path_total_tokens']} tokens versus {analysis['baseline_total_tokens']} for baseline, ratio {analysis['routed_to_baseline_token_ratio']:.3f}.",
    ]
    interpretations = [
        "The experiment now tests source credibility at the semantic-axis level rather than asking one coordinator to average all receipts.",
        "A focused basis critic is isolated from object selection, so any basis change cannot silently rewrite the cognitive object.",
        "The coordinator creates substantial preference diversity but also strongly reorients object selection, supporting axis separation rather than whole-tuple trust.",
        "The focused basis critic collapses all observed hard selections to LEXICAL_EXACT; this is a transport or ontology warning, not evidence of basis improvement.",
        "Structural completion and disagreement do not establish correctness; no Cbit or collective-gain claim is available before the external panel.",
    ]
    unknowns = [
        "Whether the v0.16 source ranking transfers to these new structural families.",
        "Whether focused basis classification improves enough to offset the extra provider work.",
        "Whether the all-LEXICAL critic distribution reflects the fresh corpus, label semantics, or a renewed menu-label prior.",
        "Whether static axis ownership is sufficient or credibility must be conditioned on each object's structure.",
    ]
    intuition = [
        "If routed preference improves while object accuracy is preserved, role complementarity has become actionable rather than merely observable.",
        "If basis remains weak, the current basis ontology may be harder than the object decision itself or may not be the right decomposition.",
        "A source can be relatively best on one burned set yet still collapse on a new set; credibility may need object-conditional calibration rather than static ownership.",
        "If semantic gain is positive but fails the token gate, the next target is selective invocation rather than more roles.",
    ]
    lines = ["# Axis Credibility Routing v0.17 Analysis", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        "Semantic state: `PENDING_EXTERNAL_MODEL_PANEL`",
        "Collective gain claim: `NOT_ALLOWED`",
        f"Candidate state: `{analysis['candidate_state']}`",
        f"Artifact hash: `{analysis['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
