"""Freeze a balanced 36-case Evidence Inference test-split holdout."""

from __future__ import annotations

import json
import sys
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(REPO_ROOT / "agentos_core_slim_v0"), str(PACK_ROOT)]

from local_collective_cognition.benchmark_bridge_holdout import (  # noqa: E402
    build_holdout_preregistration,
)
from local_collective_cognition.benchmark_bridge_sources import (  # noqa: E402
    ensure_holdout_source,
    ensure_sources,
    holdout_source_manifest,
)
from local_collective_cognition.evidence_inference_bridge import (  # noqa: E402
    LABEL_MAP,
    SELECTED_PROMPT_IDS,
    build_selected_panel,
    public_panel,
    validate_panel,
)
from local_collective_cognition.evidence_inference_selection import (  # noqa: E402
    select_balanced_prompt_ids,
)


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def main() -> int:
    output = REPO_ROOT / "outputs" / "benchmark_bridge_v0_65"
    calibration_decision = read(output / "calibration_decision.json")
    paths = ensure_sources()
    paths["test_article_ids.txt"] = ensure_holdout_source()
    selected = select_balanced_prompt_ids(
        paths=paths,
        split_ids_name="test_article_ids.txt",
        per_label=12,
        label_map=LABEL_MAP,
        excluded_prompt_ids=SELECTED_PROMPT_IDS,
    )
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=selected,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-candidate-rationale-test-transfer",
        split="test_frozen_transfer_holdout",
        manifest=holdout_source_manifest(),
        external_transfer_claim=True,
    )
    validate_panel(panel)
    preregistration = build_holdout_preregistration(
        panel=panel,
        calibration_decision=calibration_decision,
    )
    write(output / "holdout_panel_private.json", panel)
    write(output / "holdout_panel_public.json", public_panel(panel))
    write(output / "holdout_preregistration.json", preregistration)
    print(json.dumps({
        "case_count": panel["case_count"],
        "label_balance": panel["label_balance"],
        "selected_prompt_ids": list(selected),
        "panel_hash": panel["artifact_hash"],
        "preregistration_hash": preregistration["artifact_hash"],
        "prompt_or_contract_tuning_allowed": False,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
