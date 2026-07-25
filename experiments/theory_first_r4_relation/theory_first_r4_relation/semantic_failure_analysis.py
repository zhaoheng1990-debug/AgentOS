"""Post-hoc diagnostic for the early-stopped v0.3B batch call."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .semantic_cases import CASES
from .semantic_schemas import parse_semantic_receipts
from .semantic_scoring import score_relation_predictions


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(output_dir: Path) -> dict[str, Any]:
    raw_dir = output_dir / "raw_attempts"
    attempts = []
    predictions = []
    for attempt in (1, 2):
        path = raw_dir / f"batch_A_attempt_{attempt}.json.txt"
        root = json.loads(path.read_text(encoding="utf-8"))
        items = root.get("cases") if isinstance(root, dict) else None
        if not isinstance(items, list):
            raise ValueError("post-hoc expected the observed cases array")
        parsed = parse_semantic_receipts(
            json.dumps({"receipts": items}, ensure_ascii=True), CASES
        )
        states = {
            receipt.case_id: receipt.relation_state for receipt in parsed.receipts
        }
        metrics = score_relation_predictions(states)
        predictions.append(states)
        attempts.append(
            {
                "attempt": attempt,
                "observed_root_type": "object",
                "observed_array_key": "cases",
                "relation_accuracy": metrics["relation_accuracy"],
                "macro_state_recall": metrics["macro_state_recall"],
                "action_accuracy": metrics["action_accuracy"],
                "false_combine_case_ids": metrics["false_combine_case_ids"],
                "false_deduplicate_case_ids": metrics[
                    "false_deduplicate_case_ids"
                ],
                "false_block_case_ids": metrics["false_block_case_ids"],
                "confusion": metrics["confusion"],
                "response_sha256": _sha(path),
                "scoring_authority": False,
            }
        )
    ledger = json.loads(
        (output_dir / "attempt_ledger_checkpoint.json").read_text(encoding="utf-8")
    )
    return {
        "analysis_version": "agentos_r4_v0_3b_early_stop_analysis_v0_1",
        "experiment_status": "FAIL_EARLY_STOP",
        "failure_class": "MECHANICAL_ROOT_ALIAS_MISMATCH",
        "attempts": attempts,
        "attempt_relation_agreement": sum(
            predictions[0][case.case_id] == predictions[1][case.case_id]
            for case in CASES
        )
        / len(CASES),
        "total_tokens": sum(
            int(receipt["usage"]["total_tokens"]) for receipt in ledger
        ),
        "cache_hit_tokens": sum(
            int(receipt["usage"]["cache_hit_tokens"]) for receipt in ledger
        ),
        "private_reference_exposed": False,
        "same_version_repair_applied": False,
        "provider_decision_authority": False,
        "core_writes": 0,
        "retention_writes": 0,
        "baseline_writes": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    result = analyze(output_dir)
    analysis_path = output_dir / "failure_analysis.json"
    analysis_path.write_text(
        json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    paths = [
        output_dir / "attempt_ledger_checkpoint.json",
        output_dir / "failure_execution.json",
        analysis_path,
        *sorted((output_dir / "raw_attempts").glob("*.txt")),
    ]
    inventory = {
        "inventory_version": "agentos_r4_v0_3b_failure_inventory_v0_1",
        "files": [
            {
                "path": str(path.relative_to(output_dir)),
                "bytes": path.stat().st_size,
                "sha256": _sha(path),
            }
            for path in paths
        ],
    }
    (output_dir / "hash_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
