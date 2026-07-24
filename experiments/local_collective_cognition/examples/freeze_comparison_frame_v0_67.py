"""Freeze v0.67 on the v0.66 calibration and untouched holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.comparison_frame_protocol import (  # noqa: E402
    build_calibration_preregistration,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    source = REPO_ROOT / "outputs" / "semantic_basis_v0_66"
    output = REPO_ROOT / "outputs" / "comparison_frame_v0_67"
    output.mkdir(parents=True, exist_ok=True)
    calibration = read(source / "calibration_private.json")
    holdout = read(source / "holdout_private.json")
    preregistration = build_calibration_preregistration(
        panel=calibration, frozen_holdout=holdout
    )
    for name in (
        "calibration_private.json",
        "calibration_public.json",
        "holdout_private.json",
        "holdout_public.json",
    ):
        write(output / name, read(source / name))
    write(output / "calibration_preregistration.json", preregistration)
    print(json.dumps({
        "calibration_hash": calibration["artifact_hash"],
        "holdout_hash": holdout["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "provider_call_count": 0,
        "holdout_provider_call_count": 0,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
