"""Fresh Evidence Inference challenge holdout for v0.66."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence_inference_bridge import (
    LABEL_MAP,
    build_selected_panel,
    validate_panel,
)
from .semantic_basis_selection import (
    challenge_tags,
    select_balanced_semantic_challenges,
)
from .semantic_basis_sources import semantic_basis_source_manifest


def build_semantic_basis_holdout(
    paths: dict[str, Path],
) -> dict[str, Any]:
    selected = select_balanced_semantic_challenges(
        paths=paths,
        split_ids_name="train_article_ids.txt",
        per_label=12,
        label_map=LABEL_MAP,
    )
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=selected,
        split_ids_name="train_article_ids.txt",
        benchmark_id="evidence-inference-semantic-basis-fresh-holdout",
        split="previously_unused_train_split_transfer_holdout",
        manifest=semantic_basis_source_manifest(),
        external_transfer_claim=True,
    )
    validate_semantic_basis_holdout(panel)
    return panel


def validate_semantic_basis_holdout(panel: dict[str, Any]) -> None:
    validate_panel(panel)
    if panel.get("case_count") != 36:
        raise ValueError("semantic_basis_holdout_count_invalid")
    if panel.get("label_balance") != {
        "INCREASED": 12,
        "DECREASED": 12,
        "NO_DIFFERENCE": 12,
    }:
        raise ValueError("semantic_basis_holdout_balance_invalid")
    for item in panel["public_surface"]["items"]:
        text = " ".join(
            span["text"] for span in item["candidate_spans"]
        )
        if not challenge_tags(text):
            raise ValueError("semantic_basis_holdout_challenge_missing")
