"""Write deterministic R3 local artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .experiment import run_experiment


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "outputs/r3_minimal_synthetic_v0_1"


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()

    result = run_experiment()
    result_path = output_dir / "result.json"
    write_json(result_path, result)
    result_bytes = result_path.read_bytes()

    inventory = {
        "inventory_version": "agentos_r3_hash_inventory_v0_1",
        "files": [
            {
                "path": str(result_path),
                "bytes": len(result_bytes),
                "sha256": sha256_bytes(result_bytes),
            }
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    write_json(inventory_path, inventory)
    inventory_bytes = inventory_path.read_bytes()

    closure = {
        "closure_version": "agentos_r3_local_closure_v0_1",
        "status": result["status"],
        "gate_pass_count": result["gate_pass_count"],
        "gate_count": result["gate_count"],
        "provider_calls": 0,
        "fresh_holdout_consumed": False,
        "runtime_imported": False,
        "result_sha256": sha256_bytes(result_bytes),
        "hash_inventory_sha256": sha256_bytes(inventory_bytes),
        "promotion_authority": False,
    }
    write_json(output_dir / "closure.json", closure)
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
