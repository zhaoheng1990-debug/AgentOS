"""Freeze a full-run recovery after a pre-reference semantic-shape failure."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_precision_runtime import RUNTIME_VERSION  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_precision_v0_3"
    parser.add_argument("--candidate-run", default=f"{base}/four_arm_candidate_run_initial.json")
    parser.add_argument("--protocol-contract", default=f"{base}/precision_calibration_contract.json")
    parser.add_argument("--output", default=f"{base}/precision_recovery_contract_v0_3_1.json")
    args = parser.parse_args()
    predecessor = json.loads(_resolve(args.candidate_run).read_text(encoding="utf-8"))
    protocol = json.loads(_resolve(args.protocol_contract).read_text(encoding="utf-8"))
    commitment = {
        "recovery_version": "negative_evidence_precision_recovery_v0_3_1",
        "runtime_version": RUNTIME_VERSION,
        "protocol_contract_hash": protocol["contract_hash"],
        "corpus_artifact_hash": protocol["corpus_artifact_hash"],
        "predecessor_candidate_run_hash": predecessor["candidate_run_hash"],
        "failure_class": "PROVIDER_OUTPUT_SEMANTIC_SHAPE_INVALID",
        "failed_lane": "FABRICATION",
        "failed_batch": "negative-precision-batch-07",
        "allowed_changes": {
            "full_run_from_scratch": True,
            "runtime_failure_receipt_accounting_only": True,
            "individual_batch_patch": False,
            "prompt_changes": False,
            "fusion_changes": False,
            "gate_changes": False,
            "corpus_changes": False,
            "panel_changes": False,
        },
        "current_reference_labels_available": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    artifact = {**commitment, "contract_hash": hash_payload(commitment)}
    output = _resolve(args.output)
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "contract_hash": artifact["contract_hash"],
        "predecessor_candidate_run_hash": predecessor["candidate_run_hash"],
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
