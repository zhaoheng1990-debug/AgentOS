"""Bounded L-F-F-L Provider comparison entry point for R4 v0.3J."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .comparison_audit import audit_comparison
from .comparison_prompts import SYSTEM_PROMPT, comparison_prompt
from .comparison_schemas import parse_comparison_receipts
from .comparison_scoring import score_comparison
from .semantic_provider import DeepSeekSemanticAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_factorization_causal_benefit_v0_3j"
CALLS = (
    ("legacy_forward", "legacy", False),
    ("factor_forward", "factorized", False),
    ("factor_reverse", "factorized", True),
    ("legacy_reverse", "legacy", True),
)


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
    if audit_comparison()["status"] != "PASS":
        raise RuntimeError("v0.3J comparison preflight failed")
    adapter = DeepSeekSemanticAdapter(output_dir, max_completion_tokens=7000)
    parsed_calls = {}
    try:
        for call_id, arm, reverse in CALLS:
            _, parsed_calls[call_id] = adapter.call_json(
                call_id,
                SYSTEM_PROMPT,
                comparison_prompt(arm, reverse),
                lambda value, selected_arm=arm: parse_comparison_receipts(
                    value, selected_arm
                ),
            )
        result = score_comparison(parsed_calls, adapter.ledger())
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
        "inventory_version": "agentos_r4_factorization_causal_benefit_inventory_v0_3j",
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
            "closure_version": "agentos_r4_factorization_causal_benefit_closure_v0_3j",
            "status": result["status"],
            "gate_pass_count": result["gate_pass_count"],
            "gate_count": result["gate_count"],
            "physical_attempt_count": result["physical_attempt_count"],
            "total_tokens": result["total_tokens"],
            "result_sha256": _sha(result_path),
            "hash_inventory_sha256": _sha(inventory_path),
            "promotion_authority": False,
        },
    )
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
