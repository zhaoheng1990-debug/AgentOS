"""Artifact writer for the deterministic R4 v0.3C experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .envelope_evaluation import evaluate


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_RAW_DIR = (
    REPO_ROOT
    / "outputs/r4_provider_semantic_relation_v0_3b/raw_attempts"
)
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_receipt_envelope_v0_3c"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output_dir: Path, raw_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = evaluate(raw_dir)
    result_path = output_dir / "result.json"
    _write(result_path, result)

    source_paths = [
        raw_dir / "batch_A_attempt_1.json.txt",
        raw_dir / "batch_A_attempt_2.json.txt",
    ]
    inventory = {
        "inventory_version": "agentos_r4_receipt_envelope_inventory_v0_3c",
        "files": [
            {
                "path": "result.json",
                "bytes": result_path.stat().st_size,
                "sha256": _sha(result_path),
                "role": "experiment_result",
            },
            *[
                {
                    "path": f"source/{path.name}",
                    "bytes": path.stat().st_size,
                    "sha256": _sha(path),
                    "role": "read_only_preserved_input",
                }
                for path in source_paths
            ],
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    closure = {
        "closure_version": "agentos_r4_receipt_envelope_closure_v0_3c",
        "status": result["status"],
        "gate_pass_count": result["gate_pass_count"],
        "gate_count": result["gate_count"],
        "provider_calls": 0,
        "result_sha256": _sha(result_path),
        "hash_inventory_sha256": _sha(inventory_path),
        "v0_3b_status_changed": False,
        "promotion_authority": False,
    }
    _write(output_dir / "closure.json", closure)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    args = parser.parse_args()
    result = run(args.output_dir.resolve(), args.raw_dir.resolve())
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

