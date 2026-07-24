"""Split filtering and deterministic sampling for Evidence Inference."""

from __future__ import annotations

import csv
import re
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path


def read_prompts(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {row["PromptID"]: row for row in csv.DictReader(handle)}


def read_annotations(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def eligible(row: dict[str, str]) -> bool:
    return (
        row["Valid Label"].strip().lower() == "true"
        and row["Valid Reasoning"].strip().lower() == "true"
        and row["In Abstract"].strip().lower() == "true"
        and bool(row["Annotations"].strip())
    )


def select_distractors(
    *,
    prompt: dict[str, str],
    rows: list[dict[str, str]],
    target_prompt_id: str,
    excluded: set[str],
) -> list[str]:
    target_terms = terms(
        " ".join(
            prompt[field]
            for field in ("Intervention", "Comparator", "Outcome")
        )
    )
    candidates: list[tuple[float, str, str]] = []
    for row in rows:
        if row["PromptID"] == target_prompt_id:
            continue
        text = normalize(row["Annotations"])
        if not text or text in excluded:
            continue
        row_terms = terms(text)
        overlap = len(target_terms & row_terms) / max(
            1, len(target_terms | row_terms)
        )
        candidates.append((overlap, row["PromptID"], text))
    ordered = unique(
        value[2] for value in sorted(candidates, key=lambda value: value)
    )
    if len(ordered) < 2:
        raise ValueError(
            f"insufficient_same_article_distractors:{target_prompt_id}"
        )
    return ordered[:2]


def select_balanced_prompt_ids(
    *,
    paths: dict[str, Path],
    split_ids_name: str,
    per_label: int,
    label_map: dict[str, str],
    excluded_prompt_ids: tuple[str, ...] = (),
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
    excluded = set(excluded_prompt_ids)
    buckets: dict[str, list[str]] = defaultdict(list)
    for prompt_id, target_rows in by_prompt.items():
        if prompt_id in excluded or prompt_id not in prompts:
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
        prompt = prompts[prompt_id]
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
        buckets[label_map[majority]].append(prompt_id)
    selected: list[str] = []
    for label in label_map.values():
        ordered = sorted(
            buckets[label],
            key=lambda prompt_id: sha256(
                f"v0.65-holdout|{prompt_id}".encode("utf-8")
            ).hexdigest(),
        )
        if len(ordered) < per_label:
            raise ValueError(f"insufficient_holdout_cases:{label}")
        selected.extend(ordered[:per_label])
    return tuple(selected)


def normalize(value: str) -> str:
    return " ".join(value.split())


def unique(values) -> list[str]:
    return list(dict.fromkeys(values))


def terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", value.lower()))
