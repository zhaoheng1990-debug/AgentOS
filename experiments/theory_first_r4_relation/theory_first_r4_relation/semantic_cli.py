"""Authorized live entry point for R4 v0.3B."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .semantic_evaluation import run_live
from .semantic_provider import DeepSeekSemanticAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_provider_semantic_relation_v0_3b"


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
    adapter = DeepSeekSemanticAdapter(output_dir)
    try:
        result = run_live(adapter)
    except Exception as error:
        output_dir.mkdir(parents=True, exist_ok=True)
        _write(
            output_dir / "failure_execution.json",
            {
                "status": "FAIL_EARLY_STOP",
                "error": f"{type(error).__name__}:{error}",
                "attempt_ledger": adapter.ledger(),
                "same_version_repair_applied": False,
            },
        )
        return 1
    result_path = output_dir / "result.json"
    _write(result_path, result)
    inventory = {
        "inventory_version": "agentos_r4_provider_relation_inventory_v0_3b",
        "files": [
            {
                "path": "result.json",
                "bytes": result_path.stat().st_size,
                "sha256": _sha(result_path),
            }
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    _write(
        output_dir / "closure.json",
        {
            "closure_version": "agentos_r4_provider_relation_closure_v0_3b",
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
    return 0 if result["status"] in {"PASS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
