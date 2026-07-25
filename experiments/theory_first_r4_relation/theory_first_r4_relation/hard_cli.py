"""Authorized live entry point for R4 v0.3E."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .hard_evaluation import run_hard_live
from .semantic_provider import DeepSeekSemanticAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_fresh_hard_relation_v0_3e"


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
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    adapter = DeepSeekSemanticAdapter(output_dir, max_completion_tokens=7000)
    try:
        result = run_hard_live(adapter)
    except Exception as error:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write(
            output_dir / "failure_execution.json",
            {
                "status": "FAIL_PROVIDER_CONSTRUCTION_EARLY_STOP",
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
        "inventory_version": "agentos_r4_fresh_hard_inventory_v0_3e",
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
                    "role": "provider_response",
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
            "closure_version": "agentos_r4_fresh_hard_closure_v0_3e",
            "status": result["status"],
            "gate_pass_count": result["gate_pass_count"],
            "gate_count": result["gate_count"],
            "logical_call_count": result["logical_call_count"],
            "physical_attempt_count": result["physical_attempt_count"],
            "total_tokens": result["total_tokens"],
            "result_sha256": _sha(result_path),
            "hash_inventory_sha256": _sha(inventory_path),
            "promotion_authority": False,
        },
    )
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())

