"""Ingest the exact K3 member, freeze reference, and score all frozen arms."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.cognitive_action_external_evaluation import (  # noqa: E402
    build_external_evaluation,
    build_external_reference,
    render_external_evaluation,
    validate_external_evaluation,
)
from local_collective_cognition.cognitive_action_external_panel import validate_adjudication_response  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--k3-bundle", default=r"C:\Users\ZH\Downloads\Kimi_Agent_裁定结果摘要 (11).zip")
    parser.add_argument("--source-dir", default=str(REPO_ROOT / "outputs" / "cognitive_action_overnight_v0_16"))
    args = parser.parse_args()
    source, bundle = Path(args.source_dir), Path(args.k3_bundle)
    panel = source / "external_panel"
    pack = read(panel / "kimi_k3_cognitive_action_adjudication_pack.json")
    adjudication_manifest = read(panel / "private_external_adjudication_manifest.json")
    bundle_hash = file_hash(bundle)
    matches = []
    with ZipFile(bundle) as archive:
        for info in archive.infolist():
            try:
                value = json.loads(archive.read(info).decode("utf-8-sig"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            if value.get("panel_id") == pack["panel_id"] and value.get("adjudication_pack_hash") == pack["pack_hash"]:
                matches.append((info.filename, value))
    if len(matches) != 1:
        raise ValueError(f"cognitive_action_k3_exact_member_count:{len(matches)}")
    member, response = matches[0]
    validate_adjudication_response(response, pack=pack)
    write(panel / "kimi_k3_cognitive_action_adjudication_response.json", response)
    reference = build_external_reference(
        adjudication_pack=pack, adjudication_manifest=adjudication_manifest, response=response,
        source_bundle_hash=bundle_hash, source_member=member,
    )
    write(panel / "cognitive_action_external_reference_candidate.json", reference)
    role_run = read(source / "fresh_action_role_run.json")
    role_analysis = read(source / "fresh_action_role_analysis.json")
    coordinator_run = read(source / "blind_coordinator_arms_run.json")
    coordinator_analysis = read(source / "blind_coordinator_arms_analysis.json")
    evaluation = build_external_evaluation(
        reference=reference, role_run=role_run, role_analysis=role_analysis,
        coordinator_run=coordinator_run, coordinator_analysis=coordinator_analysis,
    )
    validate_external_evaluation(
        evaluation, reference=reference, role_run=role_run, role_analysis=role_analysis,
        coordinator_run=coordinator_run, coordinator_analysis=coordinator_analysis,
    )
    write(panel / "cognitive_action_external_evaluation.json", evaluation)
    (panel / "COGNITIVE_ACTION_EXTERNAL_EVALUATION.md").write_text(render_external_evaluation(evaluation), encoding="utf-8")
    decision_basis = Counter(decision["decision_basis"] for decision in response["decisions"])
    confidence = [decision["confidence"] for decision in response["decisions"]]
    closure_commitment = {
        "closure_version": "cognitive_action_external_closure_v0_16",
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "k3_bundle_sha256": bundle_hash,
        "k3_bundle_member": member,
        "k3_decision_basis_counts": dict(decision_basis),
        "k3_mean_confidence": round(sum(confidence) / len(confidence), 6),
        "collective_gain_status": evaluation["collective_gain_status"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "baseline_promotion_allowed": False,
        "retention_write_allowed": False,
        "next_required_evidence": "FRESH_AXIS_SPECIFIC_CREDIBILITY_ROUTING_HOLDOUT",
        "candidate_state": evaluation["candidate_state"],
    }
    closure = {**closure_commitment, "artifact_hash": hash_payload(closure_commitment)}
    write(panel / "cognitive_action_external_closure.json", closure)
    artifacts = [
        panel / "kimi_k3_cognitive_action_adjudication_response.json",
        panel / "cognitive_action_external_reference_candidate.json",
        panel / "cognitive_action_external_evaluation.json",
        panel / "COGNITIVE_ACTION_EXTERNAL_EVALUATION.md",
        panel / "cognitive_action_external_closure.json",
    ]
    inventory_commitment = {
        "inventory_version": "cognitive_action_external_final_inventory_v0_16",
        "items": [{"path": path.name, "size_bytes": path.stat().st_size, "sha256": file_hash(path)} for path in artifacts],
    }
    inventory = {**inventory_commitment, "artifact_hash": hash_payload(inventory_commitment)}
    write(panel / "final_hash_inventory.json", inventory)
    return_pack = source / "cognitive_action_external_evaluation_v0_16_return_pack.zip"
    with ZipFile(return_pack, "w", compression=ZIP_DEFLATED) as archive:
        for path in (*artifacts, panel / "final_hash_inventory.json"):
            archive.write(path, arcname=f"external_panel/{path.name}")
    print(json.dumps({
        "source_bundle_sha256": bundle_hash,
        "selected_member": member,
        "reference_hash": reference["artifact_hash"],
        "evaluation_hash": evaluation["artifact_hash"],
        "arm_metrics": evaluation["arm_metrics"],
        "correction_counts": evaluation["correction_counts"],
        "collective_gain_status": evaluation["collective_gain_status"],
        "anti_additive_gate": evaluation["anti_additive_gate"],
        "return_pack": str(return_pack),
        "return_pack_sha256": file_hash(return_pack),
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

