"""Download pinned sources externally and freeze the v0.65 calibration panel."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.benchmark_bridge_protocol import (  # noqa: E402
    build_preregistration,
)
from local_collective_cognition.benchmark_bridge_sources import (  # noqa: E402
    default_cache_dir,
    ensure_sources,
)
from local_collective_cognition.evidence_inference_bridge import (  # noqa: E402
    build_calibration_panel,
    public_panel,
    validate_panel,
)


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    paths = ensure_sources()
    panel = build_calibration_panel(paths)
    validate_panel(panel)
    preregistration = build_preregistration(panel)
    output = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"
    output.mkdir(parents=True, exist_ok=True)
    write(output / "calibration_panel_private.json", panel)
    write(output / "calibration_panel_public.json", public_panel(panel))
    write(output / "preregistration.json", preregistration)
    print(json.dumps({
        "output": str(output),
        "external_cache": str(default_cache_dir()),
        "panel_hash": panel["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "case_count": panel["case_count"],
        "label_balance": panel["label_balance"],
        "raw_data_written_to_repository": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
