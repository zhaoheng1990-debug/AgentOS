"""Bounded matched Provider experiment entry point for R4 v0.3K."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .role_audit import audit_role_experiment
from .role_prompts import SYSTEM_PROMPT, role_prompt
from .role_schemas import parse_role_receipts
from .role_scoring import score_role_experiment
from .semantic_provider import DeepSeekSemanticAdapter


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = REPO_ROOT / "outputs/r4_role_decomposition_v0_3k"
CALLS = (
    ("wide_source_p_forward", "wide", False),
    ("split_provenance_forward", "provenance", False),
    ("split_effect_forward", "effect", False),
    ("wide_source_e_forward", "wide", False),
    ("wide_source_e_reverse", "wide", True),
    ("split_effect_reverse", "effect", True),
    ("split_provenance_reverse", "provenance", True),
    ("wide_source_p_reverse", "wide", True),
)


def _write(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    audit = audit_role_experiment()
    if audit["status"] != "PASS":
        raise RuntimeError("v0.3K role-decomposition preflight failed")

    adapter = DeepSeekSemanticAdapter(output_dir, max_completion_tokens=8000)
    parsed_calls = {}
    try:
        for call_id, scope, reverse in CALLS:
            _, parsed_calls[call_id] = adapter.call_json(
                call_id,
                SYSTEM_PROMPT,
                role_prompt(scope, reverse),
                lambda value, selected_scope=scope: parse_role_receipts(
                    value, selected_scope
                ),
            )
        preliminary_a = score_role_experiment(
            parsed_calls,
            adapter.ledger(),
            preflight_ok=True,
            replay_identical=False,
        )
        preliminary_b = score_role_experiment(
            parsed_calls,
            adapter.ledger(),
            preflight_ok=True,
            replay_identical=False,
        )
        replay_identical = _canonical_bytes(preliminary_a) == _canonical_bytes(
            preliminary_b
        )
        result = score_role_experiment(
            parsed_calls,
            adapter.ledger(),
            preflight_ok=True,
            replay_identical=replay_identical,
        )
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
    checkpoint = output_dir / "attempt_ledger_checkpoint.json"
    inventory_files = [
        {
            "path": "result.json",
            "bytes": result_path.stat().st_size,
            "sha256": _sha(result_path),
            "role": "experiment_result",
        },
        {
            "path": "attempt_ledger_checkpoint.json",
            "bytes": checkpoint.stat().st_size,
            "sha256": _sha(checkpoint),
            "role": "attempt_ledger",
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
    ]
    inventory = {
        "inventory_version": "agentos_r4_role_decomposition_inventory_v0_3k",
        "files": inventory_files,
    }
    inventory_path = output_dir / "hash_inventory.json"
    _write(inventory_path, inventory)
    _write(
        output_dir / "closure.json",
        {
            "closure_version": "agentos_r4_role_decomposition_closure_v0_3k",
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
    return 0 if result["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
