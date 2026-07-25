"""Authorized R4 live entry point."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .experiment import run_live_experiment, write_result
from .provider import DeepSeekAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--protocol-version", choices=("v0_1", "v0_2"), default="v0_1"
    )
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    output_dir = (
        args.output_dir
        or REPO_ROOT / f"outputs/r4_provider_adequacy_{args.protocol_version}"
    ).resolve()

    adapter = DeepSeekAdapter(
        checkpoint_path=output_dir / "attempt_ledger_checkpoint.json",
        response_checkpoint_dir=output_dir / "raw_attempts",
    )
    result = run_live_experiment(adapter, protocol_version=args.protocol_version)
    write_result(output_dir, result)
    result_path = output_dir / "result.json"
    inventory = {
        "inventory_version": f"agentos_r4_hash_inventory_{args.protocol_version}",
        "files": [
            {
                "path": str(result_path),
                "bytes": result_path.stat().st_size,
                "sha256": _sha256(result_path),
            }
        ],
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    closure = {
        "closure_version": f"agentos_r4_local_closure_{args.protocol_version}",
        "status": result["status"],
        "gate_pass_count": result["gate_pass_count"],
        "gate_count": result["gate_count"],
        "logical_call_count": result["logical_call_count"],
        "physical_attempt_count": result["physical_attempt_count"],
        "total_tokens": result["total_tokens"],
        "result_sha256": _sha256(result_path),
        "hash_inventory_sha256": _sha256(inventory_path),
        "provider_authority": False,
        "promotion_authority": False,
    }
    _write(output_dir / "closure.json", closure)
    return 0 if result["status"] in {"PASS", "PARTIAL"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
