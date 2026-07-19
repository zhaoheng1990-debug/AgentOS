"""Deterministic end-to-end smoke for Anti-Additive Methodology control."""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any


CORE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CORE_ROOT))

from agentos_kernel import (  # noqa: E402
    ANTI_ADDITIVE_TRIGGER_IDS,
    AntiAdditiveChangeCandidate,
    AutonomousICMEvolutionPolicy,
    ProjectScopedDurableStore,
    ProviderCapabilityProfile,
    ProviderTaskRouter,
    methodology_candidate_commitment,
)
from agentos_runtime import AntiAdditiveMethodologyRuntime  # noqa: E402


RETURN_PACK_NAME = "AgentOS_AntiAdditiveMethodology_ReturnPack_v0_1.zip"
EVIDENCE = ("evidence://repeated-patch-failure", "evidence://object-upgrade-audit")


def _hash_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return sha256(encoded).hexdigest()


class SmokeProvider:
    profile = ProviderCapabilityProfile(
        provider_id="provider-anti-additive-smoke",
        model_id="deterministic-methodology-model",
        task_kinds=("anti_additive_methodology_assessment",),
        max_timeout_seconds=120,
    )

    def invoke(self, task):
        return {
            "result": {
                "current_object_adequacy": "UNDERPOWERED",
                "trigger_assessments": [
                    {
                        "trigger_id": trigger_id,
                        "triggered": trigger_id
                        in {
                            "PATCH_PRESERVES_OBJECT_WITHOUT_CBIT_GAIN",
                            "EDGE_CONTROL_WITH_CENTRAL_FAILURE",
                        },
                        "rationale": f"frozen smoke assessment for {trigger_id}",
                        "evidence_refs": list(EVIDENCE),
                    }
                    for trigger_id in ANTI_ADDITIVE_TRIGGER_IDS
                ],
                "expected_effective_cbit_gain": 0.82,
                "complexity_cost": 0.24,
                "object_upgrade_gain": 0.75,
                "abstraction_cost": 0.20,
                "uncertainty": 0.18,
                "recommended_action": "UPGRADE_OBJECT",
                "rationale": "one higher-level object replaces repeated same-level patches",
                "evidence_refs": list(EVIDENCE),
            },
            "usage": {"input_tokens": 20, "output_tokens": 20},
            "provenance_refs": list(EVIDENCE),
        }


def _evolution_candidate() -> dict[str, Any]:
    return {
        "candidate_id": "anti-additive-object-upgrade",
        "research_line": "UtilityPolicySelector",
        "status": "ACCEPT_READY_WITH_EVIDENCE",
        "evidence_refs": list(EVIDENCE),
        "accept_decision_ref": "decision://anti-additive-smoke",
        "scope": "project_scoped",
        "project_scope_ref": "project://anti-additive-smoke",
        "target_type": "OperatorMemory",
        "negative_transfer_risk": "bounded",
        "future_cbit_gain": "positive",
        "replayable_evidence": True,
    }


def _manifest(output_dir: Path) -> dict[str, Any]:
    excluded = {output_dir / "manifest.json", output_dir / RETURN_PACK_NAME}
    files = [
        {
            "path": path.relative_to(output_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256(path.read_bytes()).hexdigest(),
        }
        for path in sorted(output_dir.rglob("*"))
        if path.is_file() and path not in excluded
    ]
    payload = {"status": "PASS", "files": files}
    payload["manifest_hash"] = _hash_payload(payload)
    (output_dir / "manifest.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    return payload


def run_smoke(output_dir: str | Path) -> dict[str, Any]:
    output = Path(output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)
    evolution_candidate = _evolution_candidate()
    candidate = AntiAdditiveChangeCandidate.create(
        audit_id="audit-anti-additive-smoke",
        candidate_id=evolution_candidate["candidate_id"],
        project_scope=evolution_candidate["project_scope_ref"],
        change_kind="MEMORY",
        target_type="OperatorMemory",
        current_object_ref="object://patch-score-proxy",
        proposed_object_ref="object://contextual-policy-control",
        current_object_level="PROXY",
        proposed_object_level="ONTOLOGY_OBJECT",
        prior_failure_count=3,
        prior_patch_count=4,
        candidate_payload_hash=methodology_candidate_commitment(evolution_candidate),
        evidence_refs=EVIDENCE,
    )
    runtime = AntiAdditiveMethodologyRuntime(
        runtime_id="anti-additive-smoke",
        project_scope=candidate.project_scope,
        provider_router=ProviderTaskRouter([SmokeProvider()]),
        workspace_root=output / "runtime",
    )
    methodology_receipt = runtime.review_change(
        candidate=candidate,
        kernel_authorization_ref="kernel://anti-additive-smoke-review",
    )
    evolution = AutonomousICMEvolutionPolicy()
    review = evolution.review(evolution_candidate, methodology_receipt)
    store = ProjectScopedDurableStore(output / "icm-store")
    write_receipt = store.write(evolution.build_envelope(evolution_candidate, review, store))
    runtime_replay = runtime.verify_replay()
    write_replay = store.replay(write_receipt)
    if (
        methodology_receipt.decision.state != "ALLOW_BOUNDED_CHANGE"
        or review.eligible is not True
        or not runtime_replay["valid"]
        or write_replay["replay_status"] != "PASS"
    ):
        raise RuntimeError("anti_additive_methodology_smoke_failed")
    result = {
        "status": "PASS",
        "methodology_receipt": methodology_receipt.as_dict(),
        "evolution_review": dict(review.__dict__),
        "write_receipt": write_receipt,
        "runtime_replay": runtime_replay,
        "write_replay": write_replay,
    }
    (output / "anti_additive_methodology_smoke_result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    manifest = _manifest(output)
    pack = output / RETURN_PACK_NAME
    with zipfile.ZipFile(pack, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(output.rglob("*")):
            if path.is_file() and path != pack:
                archive.write(path, path.relative_to(output).as_posix())
    return {
        "status": "PASS",
        "output_dir": str(output),
        "manifest_file_count": len(manifest["files"]),
        "return_pack": str(pack),
        "return_pack_sha256": sha256(pack.read_bytes()).hexdigest(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    print(json.dumps(run_smoke(args.output_dir), indent=2, sort_keys=True))
