"""Validate Kimi K3, freeze v0.17 reference, and score all candidate arms."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import zipfile
from collections import Counter
from pathlib import Path

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_axis_evaluation import (  # noqa: E402
    build_axis_external_evaluation,
    build_axis_external_reference,
    render_axis_external_evaluation,
    validate_axis_external_evaluation,
)
from local_collective_cognition.cognitive_action_axis_panel import validate_axis_adjudication_response  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


K3_SOURCE = Path(r"C:\Users\ZH\.codex\attachments\448ad8ab-dbcd-4cee-b8ec-ea4d7b19abfa\pasted-text.txt")


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
    panel = output / "external_panel"
    raw = panel / "raw_received"
    raw.mkdir(parents=True, exist_ok=True)
    pack = read(panel / "kimi_k3_axis_routing_adjudication_pack.json")
    manifest = read(panel / "axis_routing_adjudication_manifest.json")
    response = read(K3_SOURCE)
    validate_axis_adjudication_response(response, pack=pack)
    raw_copy = raw / "kimi_k3_axis_routing_pasted_response.txt"
    shutil.copyfile(K3_SOURCE, raw_copy)
    write(panel / "kimi_k3_axis_routing_validated_response.json", response)
    reference = build_axis_external_reference(
        adjudication_pack=pack,
        adjudication_manifest=manifest,
        adjudication_response=response,
    )
    run = read(output / "axis_routing_run.json")
    routing_analysis = read(output / "axis_routing_analysis.json")
    preregistration = read(output / "axis_routing_preregistration.json")
    evaluation = build_axis_external_evaluation(
        reference=reference,
        run=run,
        routing_analysis=routing_analysis,
        preregistration=preregistration,
    )
    validate_axis_external_evaluation(
        evaluation,
        reference=reference,
        run=run,
        routing_analysis=routing_analysis,
        preregistration=preregistration,
    )
    write(panel / "axis_routing_external_reference_candidate.json", reference)
    write(panel / "axis_routing_external_evaluation.json", evaluation)
    (panel / "AXIS_ROUTING_EXTERNAL_EVALUATION.md").write_text(render_axis_external_evaluation(evaluation), encoding="utf-8")
    corpus = read(output / "axis_fresh_corpus_frozen.json")
    diagnostics = build_posthoc_diagnostics(
        evaluation=evaluation,
        reference=reference,
        run=run,
        corpus=corpus,
        preregistration=preregistration,
    )
    write(panel / "axis_routing_posthoc_diagnostics.json", diagnostics)
    (panel / "AXIS_ROUTING_POSTHOC_DIAGNOSTICS.md").write_text(render_posthoc_diagnostics(diagnostics), encoding="utf-8")
    decision_bases = Counter(decision["decision_basis"] for decision in response["decisions"])
    mean_confidence = round(sum(decision["confidence"] for decision in response["decisions"]) / len(response["decisions"]), 6)
    closure_commitment = {
        "closure_version": "axis_routing_external_evaluation_closure_v0_17",
        "panel_id": manifest["panel_id"],
        "adjudication_pack_hash": pack["pack_hash"],
        "adjudication_manifest_hash": manifest["manifest_hash"],
        "adjudication_response_hash": hash_payload(response),
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "posthoc_diagnostics_hash": diagnostics["artifact_hash"],
        "k3_decision_basis_counts": dict(decision_bases),
        "k3_mean_confidence": mean_confidence,
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "preregistered_gate_conditions": evaluation["preregistered_gate_conditions"],
        "baseline_promotion_allowed": evaluation["baseline_promotion_allowed"],
        "retention_write_allowed": False,
        "candidate_state": evaluation["candidate_state"],
        "next_required_evidence": (
            "SEPARATE_BASELINE_PROMOTION_AUDIT_AND_NEW_TRANSFER_HOLDOUT"
            if evaluation["anti_additive_gate"] == "PASS"
            else "NEW_FRESH_CONDITIONAL_SELECTIVE_ROUTING_HOLDOUT_AFTER_BASIS_AND_EVIDENCE_STATE_REVISION"
        ),
        "ground_truth_claim": False,
        "production_authority": False,
    }
    closure = {**closure_commitment, "artifact_hash": hash_payload(closure_commitment)}
    write(panel / "axis_routing_external_closure.json", closure)
    artifact_paths = [
        raw_copy,
        panel / "kimi_k3_axis_routing_validated_response.json",
        panel / "axis_routing_external_reference_candidate.json",
        panel / "axis_routing_external_evaluation.json",
        panel / "AXIS_ROUTING_EXTERNAL_EVALUATION.md",
        panel / "axis_routing_posthoc_diagnostics.json",
        panel / "AXIS_ROUTING_POSTHOC_DIAGNOSTICS.md",
        panel / "axis_routing_external_closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "axis_routing_external_evaluation_hash_inventory_v0_17",
        "items": [
            {"path": str(path.relative_to(output)).replace("\\", "/"), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
            for path in artifact_paths
        ],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(panel / "axis_routing_external_evaluation_hash_inventory.json", inventory)
    return_pack = output / "axis_routing_external_evaluation_v0_17_return_pack.zip"
    members = [
        panel / "axis_routing_external_reference_candidate.json",
        panel / "axis_routing_external_evaluation.json",
        panel / "AXIS_ROUTING_EXTERNAL_EVALUATION.md",
        panel / "axis_routing_posthoc_diagnostics.json",
        panel / "AXIS_ROUTING_POSTHOC_DIAGNOSTICS.md",
        panel / "axis_routing_external_closure.json",
        panel / "axis_routing_external_evaluation_hash_inventory.json",
    ]
    with zipfile.ZipFile(return_pack, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in members:
            info = zipfile.ZipInfo(path.name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, path.read_bytes())
    print(json.dumps({
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "closure_hash": closure["artifact_hash"],
        "k3_decision_basis_counts": dict(decision_bases),
        "k3_mean_confidence": mean_confidence,
        "arm_metrics": evaluation["arm_metrics"],
        "primary_axis_deltas": evaluation["primary_axis_deltas"],
        "primary_transition_counts": evaluation["primary_transition_counts"],
        "primary_transition_counts_by_axis": evaluation["primary_transition_counts_by_axis"],
        "posthoc_diagnostics_hash": diagnostics["artifact_hash"],
        "cost_accounting": evaluation["cost_accounting"],
        "gate_conditions": evaluation["preregistered_gate_conditions"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "candidate_state": evaluation["candidate_state"],
        "return_pack": str(return_pack),
        "return_pack_sha256": sha256_file(return_pack),
    }, indent=2, sort_keys=True))
    return 0


def build_posthoc_diagnostics(*, evaluation, reference, run, corpus, preregistration):
    truth = {label["conflict_id"]: label["criteria"] for label in reference["labels"]}
    families = {
        conflict_id: binding["object_family"]
        for conflict_id, binding in corpus["private_provenance"]["bindings"].items()
    }
    outputs = {"SINGLE_MODEL_BASELINE": {}, "ROLE_INFORMED_COORDINATOR": {}, "AXIS_ROUTED": {}}
    for output in run["tuple_outputs"]:
        outputs[output["arm"]][output["conflict_id"]] = output["payload"]
    for output in run["routed_outputs"]:
        outputs["AXIS_ROUTED"][output["conflict_id"]] = output["payload"]
    axes = (
        ("selected_object", "SELECTED_OBJECT"),
        ("selection_basis", "SELECTION_BASIS"),
        ("pragmatic_preference", "PRAGMATIC_PREFERENCE"),
    )
    family_metrics = {}
    for family in sorted(set(families.values())):
        ids = [conflict_id for conflict_id, value in families.items() if value == family]
        family_metrics[family] = {}
        for arm, values in outputs.items():
            axis_correct = {
                reference_field: sum(
                    conflict_id in values and values[conflict_id][arm_field] == truth[conflict_id][reference_field]
                    for conflict_id in ids
                )
                for arm_field, reference_field in axes
            }
            family_metrics[family][arm] = {
                "axis_correct": axis_correct,
                "primary_correct_cells": sum(axis_correct.values()),
                "possible_primary_cells": len(ids) * len(axes),
            }
    v16 = preregistration["source_axis_correct"]
    v17_metrics = evaluation["arm_metrics"]
    current_scores = {
        arm: {
            axis: v17_metrics[arm]["axis_correct"][axis]
            for axis in ("SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE")
        }
        for arm in ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR", "AXIS_ROUTED")
    }
    best_by_axis = {
        axis: max(
            ("SINGLE_MODEL_BASELINE", "ROLE_INFORMED_COORDINATOR"),
            key=lambda arm: current_scores[arm][axis],
        )
        for axis in ("SELECTED_OBJECT", "SELECTION_BASIS", "PRAGMATIC_PREFERENCE")
    }
    commitment = {
        "diagnostic_version": "axis_routing_posthoc_diagnostics_v0_17",
        "evaluation_hash": evaluation["artifact_hash"],
        "reference_hash": reference["artifact_hash"],
        "v0_16_calibration_source_axis_correct": v16,
        "v0_17_source_axis_correct": current_scores,
        "source_ranking_reversal": {
            "selected_object": "v0.16 favored baseline by 7; v0.17 favors coordinator by 1",
            "selection_basis": "v0.17 baseline beats coordinator and routed critic by 2",
            "pragmatic_preference": "coordinator advantage contracts from 7 to 1",
        },
        "family_primary_metrics": family_metrics,
        "posthoc_best_observed_source_by_axis": best_by_axis,
        "posthoc_best_observed_primary_cells": sum(current_scores[source][axis] for axis, source in best_by_axis.items()),
        "posthoc_route_is_confirmatory_evidence": False,
        "completeness_reference_distribution": evaluation["reference_state_distributions"]["AXIS_ASSESSMENT_COMPLETE"],
        "basis_critic_state": "RETIRE_CURRENT_CONFIGURATION",
        "next_hypothesis": "OBJECT_CONDITIONAL_SELECTIVE_ESCALATION_WITHOUT_CURRENT_BASIS_CRITIC",
        "next_test_must_use_new_holdout": True,
        "baseline_promotion_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def render_posthoc_diagnostics(diagnostics):
    observations = [
        f"v0.16 calibration source scores were {diagnostics['v0_16_calibration_source_axis_correct']}.",
        f"v0.17 source scores are {diagnostics['v0_17_source_axis_correct']}.",
        f"Source ranking reversals are {diagnostics['source_ranking_reversal']}.",
        f"Family-level primary metrics are {diagnostics['family_primary_metrics']}.",
        f"The post-hoc best observed source assignment scores {diagnostics['posthoc_best_observed_primary_cells']}/72 primary cells, but is not confirmatory evidence.",
    ]
    interpretations = [
        "Static axis ownership does not transfer across the two fresh holdouts.",
        "The current basis critic should be retired because it introduces harms without correcting a baseline basis error.",
        "Preference collaboration has local value but needs object-conditional admission to avoid nearly symmetric harms.",
        "The all-COMPLETE final reference leaves assessment completeness non-discriminating despite the informative panel dispute.",
    ]
    unknowns = [
        "Whether family-level source differences reproduce on a new holdout rather than reflecting four cases per family.",
        "Which structural features can predict a beneficial escalation before observing outcomes.",
        "Whether selection basis should remain a decision axis or be downgraded to explanatory metadata until inter-panel stability improves.",
    ]
    intuition = [
        "The next organization should decide when to collaborate, not merely who owns an axis globally.",
        "A useful route may be sparse: baseline first, then provider-backed escalation only for structurally ambiguous objects with positive expected correction value.",
        "Known evidence absence and incomplete assessment should be represented as separate states before completeness is reused as a capability signal.",
    ]
    lines = ["# Axis Routing Post-Hoc Diagnostics v0.17", ""]
    for title, values in (("Observations", observations), ("Interpretations", interpretations), ("Unknowns", unknowns), ("Intuition Triggers", intuition)):
        lines.extend((f"## {title}", ""))
        lines.extend(f"- {value}" for value in values)
        lines.append("")
    lines.extend((
        "State: `DIAGNOSTIC_ONLY_NOT_A_NEW_ROUTE`",
        f"Artifact hash: `{diagnostics['artifact_hash']}`",
        "",
    ))
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
