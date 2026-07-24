"""Public-text challenge selection for the v0.66 fresh holdout."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path

from .evidence_inference_selection import (
    eligible,
    normalize,
    read_annotations,
    read_prompts,
    select_distractors,
    unique,
)


def challenge_tags(text: str) -> list[str]:
    value = text.lower()
    tags: list[str] = []
    if (
        re.search(r"p\s*[=<>]\s*0?\.(0[5-9]|1\d)", value)
        or "borderline" in value
        or "trend" in value
        or "not significant" in value
    ):
        tags.append("SIGNIFICANCE_BOUNDARY")
    if re.search(
        r"\b(less|lower|fewer|reduced|decreased)\b|negative effect",
        value,
    ):
        tags.append("COMPARISON_ORIENTATION")
    if re.search(
        r"\b(3|6|12|18|24)\s*(week|month|year)s?\b|"
        r"accelerometer|self-report|questionnaire|scale|score",
        value,
    ):
        tags.append("TIMEPOINT_OR_MEASUREMENT")
    return tags


def select_balanced_semantic_challenges(
    *,
    paths: dict[str, Path],
    split_ids_name: str,
    per_label: int,
    label_map: dict[str, str],
) -> tuple[str, ...]:
    prompts = read_prompts(paths["prompts.csv"])
    rows = read_annotations(paths["annotations.csv"])
    split_ids = {
        value.strip().replace("PMC", "")
        for value in paths[split_ids_name].read_text(
            encoding="utf-8"
        ).splitlines()
        if value.strip()
    }
    by_prompt: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_article: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        pmcid = row["PMCID"].replace("PMC", "").strip()
        if pmcid in split_ids and eligible(row):
            by_prompt[row["PromptID"]].append(row)
            by_article[pmcid].append(row)
    buckets: dict[str, list[str]] = defaultdict(list)
    for prompt_id, target_rows in by_prompt.items():
        prompt = prompts.get(prompt_id)
        if prompt is None:
            continue
        majority = Counter(
            row["Label"].strip() for row in target_rows
        ).most_common(1)[0][0]
        gold_texts = unique(
            normalize(row["Annotations"])
            for row in target_rows
            if row["Label"].strip() == majority
        )
        if majority not in label_map or len(gold_texts) < 2:
            continue
        pmcid = prompt["PMCID"].replace("PMC", "").strip()
        try:
            select_distractors(
                prompt=prompt,
                rows=by_article[pmcid],
                target_prompt_id=prompt_id,
                excluded=set(gold_texts),
            )
        except ValueError:
            continue
        if not challenge_tags(" ".join(gold_texts)):
            continue
        buckets[label_map[majority]].append(prompt_id)
    selected: list[str] = []
    for label in label_map.values():
        ordered = sorted(
            buckets[label],
            key=lambda prompt_id: sha256(
                f"v0.66-semantic-basis|{prompt_id}".encode("utf-8")
            ).hexdigest(),
        )
        if len(ordered) < per_label:
            raise ValueError(f"insufficient_semantic_basis_holdout:{label}")
        selected.extend(ordered[:per_label])
    return tuple(selected)
