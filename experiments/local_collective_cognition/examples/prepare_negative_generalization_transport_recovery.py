"""Freeze transport-only v0.2.1 recovery before rerunning all semantic lanes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.negative_evidence_generalization_calibration import (  # noqa: E402
    FROZEN_GATES,
)
from local_collective_cognition.negative_evidence_generalization_holdout import (  # noqa: E402
    validate_generalization_corpus_artifact,
)
from local_collective_cognition.negative_evidence_generalization_runtime import (  # noqa: E402
    validate_generalization_candidate_run,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def _resolve(path):
    candidate = Path(path)
    return candidate if candidate.is_absolute() else REPO_ROOT / candidate


def main():
    parser = argparse.ArgumentParser()
    base = "outputs/negative_evidence_generalization_v0_2"
    parser.add_argument(
        "--corpus", default=f"{base}/private_negative_generalization_corpus.json",
    )
    parser.add_argument(
        "--failed-run", default=f"{base}/four_arm_candidate_run.json",
    )
    parser.add_argument(
        "--output", default=f"{base}/transport_recovery_contract_v0_2_1.json",
    )
    args = parser.parse_args()
    corpus = json.loads(_resolve(args.corpus).read_text(encoding="utf-8"))
    failed = json.loads(_resolve(args.failed_run).read_text(encoding="utf-8"))
    validate_generalization_corpus_artifact(corpus)
    validate_generalization_candidate_run(failed, corpus_artifact=corpus)
    failure_surface = {
        lane: [
            {"batch_id": item["batch_id"], "status": item["status"]}
            for item in record["failures"]
        ]
        for lane, record in failed["lanes"].items() if record["failures"]
    }
    commitment = {
        "recovery_version": "negative_generalization_transport_recovery_v0_2_1",
        "corpus_artifact_hash": corpus["artifact_hash"],
        "predecessor_candidate_run_hash": failed["candidate_run_hash"],
        "predecessor_failure_surface": failure_surface,
        "allowed_changes": {
            "rerun_all_lanes_from_scratch": True,
            "maximum_same_contract_transport_attempts": 2,
            "heterogeneous_live_provider": "ollama-local",
            "heterogeneous_live_model": "deepseek-r1:32b",
            "reason": "kimi-k2.5 lane returned 12/12 PROVIDER_UNAVAILABLE with zero tokens",
        },
        "deepseek_model": "deepseek-v4-flash",
        "frozen_gates": FROZEN_GATES,
        "panel_labels_available": False,
        "predecessor_semantic_payloads_used_for_prompt_or_gate_adaptation": False,
        "corpus_prompt_or_packet_changes_allowed": False,
        "gate_changes_allowed": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    contract = {**commitment, "contract_hash": hash_payload(commitment)}
    output = _resolve(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        existing = json.loads(output.read_text(encoding="utf-8"))
        if existing != contract:
            raise ValueError("negative_generalization_recovery_contract_conflict")
    else:
        output.write_text(json.dumps(contract, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({
        "contract_hash": contract["contract_hash"],
        "predecessor_candidate_run_hash": failed["candidate_run_hash"],
        "failure_surface": failure_surface,
        "output": str(output),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
