"""Artifact writer for the deterministic R4 v0.3F grid."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .transform_evaluation import evaluate_transform_grid


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_transform_equivalence_v0_3f"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = evaluate_transform_grid()
    result_path = output_dir / "result.json"
    _write(result_path, result)
    inventory = {
        "inventory_version": "agentos_r4_transform_equivalence_inventory_v0_3f",
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
            "closure_version": "agentos_r4_transform_equivalence_closure_v0_3f",
            "status": result["status"],
            "gate_pass_count": result["gate_pass_count"],
            "gate_count": result["gate_count"],
            "provider_calls": 0,
            "result_sha256": _sha(result_path),
            "hash_inventory_sha256": _sha(inventory_path),
            "promotion_authority": False,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir.resolve())
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
