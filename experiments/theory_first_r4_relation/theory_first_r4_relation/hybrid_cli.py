"""Authorized live entry point for R4 v0.3D."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .hybrid_evaluation import run_hybrid_live
from .semantic_provider import DeepSeekSemanticAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_HISTORICAL_RAW = (
    REPO_ROOT / "outputs/r4_provider_semantic_relation_v0_3b/raw_attempts"
)
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_hybrid_presentation_v0_3d"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--historical-raw-dir", type=Path, default=DEFAULT_HISTORICAL_RAW
    )
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    adapter = DeepSeekSemanticAdapter(output_dir)
    try:
        result = run_hybrid_live(adapter, args.historical_raw_dir.resolve())
    except Exception as error:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write(
            output_dir / "failure_execution.json",
            {
                "status": "FAIL_CONSTRUCTION_EARLY_STOP",
                "error": f"{type(error).__name__}:{error}",
                "attempt_ledger": adapter.ledger(),
                "same_version_repair_applied": False,
            },
        )
        return 1

    result_path = output_dir / "result.json"
    _write(result_path, result)
    raw_paths = sorted((output_dir / "raw_attempts").glob("*.txt"))
    inventory = {
        "inventory_version": "agentos_r4_hybrid_presentation_inventory_v0_3d",
        "files": [
            {
                "path": "result.json",
                "bytes": result_path.stat().st_size,
                "sha256": _sha(result_path),
                "role": "experiment_result",
            },
            *[
                {
                    "path": f"raw_attempts/{path.name}",
                    "bytes": path.stat().st_size,
                    "sha256": _sha(path),
                    "role": "new_provider_response",
                }
                for path in raw_paths
            ],
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    _write(
        output_dir / "closure.json",
        {
            "closure_version": "agentos_r4_hybrid_presentation_closure_v0_3d",
            "status": result["status"],
            "gate_pass_count": result["gate_pass_count"],
            "gate_count": result["gate_count"],
            "new_logical_call_count": result["new_logical_call_count"],
            "new_physical_attempt_count": result["new_physical_attempt_count"],
            "incremental_total_tokens": result["incremental_total_tokens"],
            "result_sha256": _sha(result_path),
            "hash_inventory_sha256": _sha(inventory_path),
            "promotion_authority": False,
        },
    )
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())

