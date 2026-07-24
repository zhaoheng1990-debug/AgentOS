"""Freeze v0.66 calibration and fresh holdout before Provider calls."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.evidence_inference_bridge import (  # noqa: E402
    public_panel,
)
from local_collective_cognition.semantic_basis_calibration import (  # noqa: E402
    build_calibration_projection,
    public_projection,
    validate_calibration_projection,
)
from local_collective_cognition.semantic_basis_holdout import (  # noqa: E402
    build_semantic_basis_holdout,
)
from local_collective_cognition.semantic_basis_sources import (  # noqa: E402
    ensure_semantic_basis_sources,
)
from local_collective_cognition.semantic_basis_protocol import (  # noqa: E402
    build_calibration_preregistration,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    source = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"
    output = REPO_ROOT / "outputs" / "semantic_basis_v0_66"
    output.mkdir(parents=True, exist_ok=True)
    calibration = build_calibration_projection(
        calibration_panel=read(source / "calibration_panel_private.json"),
        calibration_run=read(source / "a1_staged_run.json"),
        holdout_panel=read(source / "holdout_panel_private.json"),
        holdout_run=read(source / "holdout_a1_run.json"),
        source_closure=read(source / "holdout_decision.json"),
    )
    validate_calibration_projection(calibration)
    holdout = build_semantic_basis_holdout(
        ensure_semantic_basis_sources()
    )
    preregistration = build_calibration_preregistration(
        panel=calibration
    )
    write(output / "calibration_private.json", calibration)
    write(output / "calibration_public.json", public_projection(calibration))
    write(output / "holdout_private.json", holdout)
    write(output / "holdout_public.json", public_panel(holdout))
    write(
        output / "calibration_preregistration.json",
        preregistration,
    )
    print(json.dumps({
        "calibration_case_count": calibration["case_count"],
        "calibration_hash": calibration["artifact_hash"],
        "calibration_label_balance": calibration["label_balance"],
        "fresh_holdout_case_count": holdout["case_count"],
        "fresh_holdout_hash": holdout["artifact_hash"],
        "fresh_holdout_label_balance": holdout["label_balance"],
        "preregistration_hash": preregistration["artifact_hash"],
        "provider_call_count": 0,
        "raw_data_written_to_repository": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
