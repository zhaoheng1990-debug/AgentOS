"""Freeze v0.18 candidate artifacts and build external annotation packs."""

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

from local_collective_cognition.cognitive_action_selective_panel import (  # noqa: E402
    build_selective_external_panel,
    validate_selective_external_panel,
)
from local_collective_cognition.cognitive_action_selective_runtime import analyze_selective_run  # noqa: E402
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
    output = REPO_ROOT / "outputs" / "selective_escalation_v0_18"
    corpus = read(output / "selective_fresh_corpus_frozen.json")
    preregistration = read(output / "selective_preregistration.json")
    baseline = read(output / "selective_baseline_run.json")
    plan = read(output / "selective_admission_plan.json")
    local = read(output / "selective_local_role_run.json")
    run = read(output / "selective_adjudication_run.json")
    analysis = analyze_selective_run(
        corpus=corpus,
        baseline_run=baseline,
        admission_plan=plan,
        local_role_run=local,
        run=run,
    )
    write(output / "selective_analysis.json", analysis)
    report_path = output / "SELECTIVE_ESCALATION_ANALYSIS.md"
    report_path.write_text(render_analysis(corpus=corpus, baseline=baseline, plan=plan, local=local, run=run, analysis=analysis), encoding="utf-8")
    packs, panel_manifest = build_selective_external_panel(
        corpus=corpus,
        baseline_run=baseline,
        selective_run=run,
    )
    validate_selective_external_panel(packs=packs, manifest=panel_manifest)
    panel_dir = output / "external_panel"
    panel_dir.mkdir(exist_ok=True)
    lane_names = []
    for pack in packs:
        name = f"{pack['lane_id'].lower()}_selective_annotation_pack.json"
        write(panel_dir / name, pack)
        lane_names.append(name)
    write(panel_dir / "selective_external_panel_manifest.json", panel_manifest)
    ledger_commitment = {
        "ledger_version": "selective_escalation_phase_ledger_v0_18",
        "methodology_kernel": "v1.1",
        "phases": [
            {"phase": "G0_PREREGISTRATION", "status": "PASS", "hash": preregistration["artifact_hash"]},
            {"phase": "G1_FRESH_HOLDOUT", "status": "PASS", "hash": corpus["artifact_hash"], "case_count": corpus["case_count"]},
            {"phase": "G2_PROVIDER_BASELINE_AND_ADMISSION", "status": "PASS" if len(baseline["outputs"]) == corpus["case_count"] else "PARTIAL", "baseline_outputs": len(baseline["outputs"]), "admitted_count": len(plan["admitted_conflict_ids"])},
            {"phase": "G3_SELECTIVE_COLLABORATION", "status": "PASS_STRUCTURAL_PENDING_EXTERNAL_PANEL", "routed_coverage": analysis["routed_coverage"], "selected_object_preserved": analysis["selected_object_preservation_count"]},
            {"phase": "G4_EXTERNAL_REFERENCE", "status": "PENDING", "panel_id": panel_manifest["panel_id"]},
        ],
        "observed_objects": ["provider evidence-state classification", "mechanical admission", "localized pragmatic collaboration", "baseline-preserving failure fallback"],
        "pending_objects": ["admission precision and recall", "fresh correction-harm balance", "preference gain", "Cbit per token"],
        "baseline_insertion": "No Baseline Object Update; experiment candidate only",
    }
    ledger = {**ledger_commitment, "artifact_hash": hash_payload(ledger_commitment)}
    write(output / "phase_ledger.json", ledger)
    replay_commitment = {
        "pointer_version": "selective_escalation_replay_v0_18",
        "working_directory": str(PACK_ROOT),
        "commands": [
            "python -m pytest -q --basetemp=.pytest_tmp_selective_replay",
            "python examples/prepare_selective_escalation.py",
            "python examples/run_selective_baseline.py",
            "conda run -n dhrf_4080s python examples/run_selective_local_role.py",
            "python examples/run_selective_adjudication.py",
            "python examples/finalize_selective_escalation.py",
        ],
        "external_panel_next": "Submit the two lane packs independently to GPT-5.6 and Gemini 3.1; adjudicate disagreements with Kimi K3.",
        "reference_revision_allowed": False,
    }
    replay = {**replay_commitment, "artifact_hash": hash_payload(replay_commitment)}
    write(output / "replay_pointer.json", replay)
    rollback_commitment = {
        "pointer_version": "selective_escalation_rollback_v0_18",
        "scope": "experiment-only; AgentOS CoreSlim is outside the change boundary",
        "output_directory": str(output),
        "rollback_action": "quarantine v0.18 experiment files and outputs after hash verification; do not alter CoreSlim or v0.17",
        "automatic_rollback_executed": False,
        "retention_authority": False,
    }
    rollback = {**rollback_commitment, "artifact_hash": hash_payload(rollback_commitment)}
    write(output / "rollback_pointer.json", rollback)
    inventory_names = [
        "selective_preregistration.json", "selective_fresh_corpus_frozen.json",
        "selective_baseline_run.json", "selective_admission_plan.json",
        "selective_baseline_telemetry.json", "selective_local_role_run.json",
        "selective_adjudication_run.json", "selective_adjudication_telemetry.json",
        "selective_analysis.json", "SELECTIVE_ESCALATION_ANALYSIS.md",
        "phase_ledger.json", "replay_pointer.json", "rollback_pointer.json",
    ] + [f"external_panel/{name}" for name in lane_names] + ["external_panel/selective_external_panel_manifest.json"]
    inventory_commitment = {
        "inventory_version": "selective_escalation_hash_inventory_v0_18",
        "items": [
            {"path": name, "size_bytes": (output / name).stat().st_size, "sha256": sha256_file(output / name)}
            for name in inventory_names
        ],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(output / "hash_inventory.json", inventory)
    manifest_commitment = {
        "manifest_version": "selective_escalation_manifest_v0_18",
        "preregistration_hash": preregistration["artifact_hash"],
        "corpus_hash": corpus["artifact_hash"],
        "baseline_run_hash": baseline["run_hash"],
        "admission_plan_hash": plan["plan_hash"],
        "selective_run_hash": run["run_hash"],
        "analysis_hash": analysis["artifact_hash"],
        "panel_manifest_hash": panel_manifest["manifest_hash"],
        "hash_inventory_hash": inventory["artifact_hash"],
        "candidate_state": analysis["candidate_state"],
        "collective_gain_claim_allowed": False,
        "baseline_promotion_allowed": False,
        "retention_write_allowed": False,
    }
    manifest = {**manifest_commitment, "artifact_hash": hash_payload(manifest_commitment)}
    write(output / "manifest.json", manifest)
    pack_path = output / "selective_escalation_external_panel_v0_18_return_pack.zip"
    with zipfile.ZipFile(pack_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in lane_names:
            archive.write(panel_dir / name, arcname=name)
        archive.write(panel_dir / "selective_external_panel_manifest.json", arcname="PRIVATE_selective_external_panel_manifest.json")
        archive.write(output / "selective_preregistration.json", arcname="selective_preregistration.json")
        archive.write(report_path, arcname=report_path.name)
        archive.write(output / "manifest.json", arcname="manifest.json")
        archive.write(output / "hash_inventory.json", arcname="hash_inventory.json")
    print(json.dumps({
        "manifest_hash": manifest["artifact_hash"],
        "inventory_hash": inventory["artifact_hash"],
        "panel_id": panel_manifest["panel_id"],
        "lane_pack_hashes": panel_manifest["lane_pack_hashes"],
        "return_pack": str(pack_path),
        "return_pack_sha256": sha256_file(pack_path),
        "candidate_state": analysis["candidate_state"],
    }, indent=2, sort_keys=True))


def render_analysis(*, corpus, baseline, plan, local, run, analysis):
    evidence = Counter(output["payload"]["evidence_state"] for output in baseline["outputs"])
    basis = Counter(output["payload"]["selection_basis"] for output in baseline["outputs"])
    local_preferences = Counter(
        output["action_receipt"]["result"]["pragmatic_preference"] for output in local["outputs"]
    )
    adjudicated_preferences = Counter(
        output["payload"]["pragmatic_preference"] for output in run["adjudications"]
    )
    from local_collective_cognition.cognitive_action_selective_holdout import CASES
    stratum_by_case = {case.case_id: case.design_stratum for case in CASES}
    stratum_by_conflict = {
        conflict_id: stratum_by_case[binding["case_id"]]
        for conflict_id, binding in corpus["private_provenance"]["bindings"].items()
    }
    design_diagnostics = {}
    for output in baseline["outputs"]:
        design_diagnostics.setdefault(stratum_by_conflict[output["conflict_id"]], Counter())
        design_diagnostics[stratum_by_conflict[output["conflict_id"]]][output["payload"]["evidence_state"]] += 1
    observations = [
        f"Provider baseline coverage is {analysis['baseline_coverage']:.3f}; routed coverage over frozen baseline outputs is {analysis['routed_coverage']:.3f}.",
        f"Baseline evidence-state distribution is {dict(evidence)}; basis distribution is {dict(basis)}.",
        f"Posthoc design-stratum diagnostics, which are construction commitments rather than truth labels, are { {key: dict(value) for key, value in design_diagnostics.items()} }.",
        f"The mechanical rule found {analysis['eligible_count']} eligible objects and admitted {analysis['admitted_count']} under the cap of 8.",
        f"The local pragmatic role returned {len(local['outputs'])}/{local['requested_count']} receipts with distribution {dict(local_preferences)}.",
        f"The baseline retained {len(baseline['outputs'])}/24 valid outputs and rejected {len(baseline['failures'])} semantically incoherent tuples.",
        f"The focused adjudicator returned {len(run['adjudications'])} valid receipts with distribution {dict(adjudicated_preferences)}; {len(run['failures'])} selective-stage failures were recorded.",
        f"Selected object was preserved on {analysis['selected_object_preservation_count']} baseline-covered objects.",
        f"The routed path used {analysis['routed_path_total_tokens']} tokens versus {analysis['baseline_total_tokens']} baseline tokens, ratio {analysis['routed_to_baseline_token_ratio']}.",
    ]
    interpretations = [
        "The experiment tests whether the runtime can recognize when collaboration is worth buying, rather than assigning permanent ownership of semantic axes.",
        "Evidence-state classification is a provider-backed cognitive judgment; admission, caps, fallback, hashing, and state transitions remain runtime decisions.",
        "The basis critic from v0.17 is absent. Any open-object basis change is a mechanical consequence of the focused pragmatic-preference result.",
        "Coverage cannot decline through selective collaboration because non-admitted and failed objects retain the already-frozen baseline tuple.",
    ]
    unknowns = [
        "External labels are required before claiming that admitted objects were truly soft-ambiguous.",
        "External labels are required before measuring preference correction, basis side effects, or net primary-cell gain.",
        "The current cost ratio is descriptive until net corrected cells are known.",
        "The six hidden construction examples per stratum are design commitments, not reference truth.",
    ]
    triggers = [
        "If admission precision is high but recall is low, the bottleneck is conservative evidence-state detection rather than collaboration quality.",
        "If precision is low, the runtime is buying collaboration for direct or opaque objects and the gate itself is the main failure.",
        "If preference improves only in one object family, the next unit of routing may be object-structure features rather than model identity.",
        "If correct preferences rise without enough net cell gain, the token budget should be spent on question generation or evidence acquisition instead.",
    ]
    lines = [
        "# Selective Escalation v0.18 Candidate Analysis",
        "",
        "Status: frozen candidate; external semantic reference pending. No baseline promotion or retention write is authorized.",
        "",
        "## Observations",
        *[f"- {item}" for item in observations],
        "",
        "## Interpretations",
        *[f"- {item}" for item in interpretations],
        "",
        "## Unknowns",
        *[f"- {item}" for item in unknowns],
        "",
        "## Intuition Triggers",
        *[f"- {item}" for item in triggers],
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
