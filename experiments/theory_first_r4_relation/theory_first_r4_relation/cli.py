"""Artifact writer for the deterministic v0.3A experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .evaluation import evaluate


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_relation_boundary_v0_3a"


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = evaluate()
    result_path = output_dir / "result.json"
    _write(result_path, result)
    inventory = {
        "inventory_version": "agentos_r4_relation_hash_inventory_v0_3a",
        "files": [
            {
                "path": "result.json",
                "bytes": result_path.stat().st_size,
                "sha256": _sha256(result_path),
            }
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    closure = {
        "closure_version": "agentos_r4_relation_local_closure_v0_3a",
        "status": result["status"],
        "gate_pass_count": result["gate_pass_count"],
        "gate_count": result["gate_count"],
        "provider_calls": 0,
        "result_sha256": _sha256(result_path),
        "hash_inventory_sha256": _sha256(inventory_path),
        "promotion_authority": False,
    }
    _write(output_dir / "closure.json", closure)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run(args.output_dir.resolve())
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
