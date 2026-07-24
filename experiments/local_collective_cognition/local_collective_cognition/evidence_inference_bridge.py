"""Deterministic Evidence Inference calibration panel for v0.65."""

from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from .benchmark_bridge_sources import source_manifest
from .evidence_inference_selection import (
    eligible,
    normalize,
    read_annotations,
    read_prompts,
    select_distractors,
    unique,
)
from .provider_telemetry import hash_payload


BRIDGE_VERSION = "benchmark_bridge_v0_65"
SELECTED_PROMPT_IDS = (
    "1113", "9554", "8846",
    "7155", "14", "9748",
    "866", "6165", "6857",
)
LABEL_MAP = {
    "significantly increased": "INCREASED",
    "significantly decreased": "DECREASED",
    "no significant difference": "NO_DIFFERENCE",
}


def build_calibration_panel(paths: dict[str, Path]) -> dict[str, Any]:
    return build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="validation_article_ids.txt",
        benchmark_id="evidence-inference-candidate-rationale-calibration",
        split="validation_development_calibration",
        manifest=source_manifest(),
        external_transfer_claim=False,
    )


def build_selected_panel(
    *,
    paths: dict[str, Path],
    selected_prompt_ids: tuple[str, ...],
    split_ids_name: str,
    benchmark_id: str,
    split: str,
    manifest: dict[str, Any],
    external_transfer_claim: bool,
) -> dict[str, Any]:
    prompts = read_prompts(paths["prompts.csv"])
    rows = read_annotations(paths["annotations.csv"])
    validation_ids = {
        value.strip().replace("PMC", "")
        for value in paths[split_ids_name].read_text(
            encoding="utf-8"
        ).splitlines()
        if value.strip()
    }
    by_prompt: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_article: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if not eligible(row):
            continue
        pmcid = row["PMCID"].replace("PMC", "").strip()
        if pmcid not in validation_ids:
            continue
        by_prompt[row["PromptID"]].append(row)
        by_article[pmcid].append(row)

    public_items: list[dict[str, Any]] = []
    private_gold: dict[str, dict[str, Any]] = {}
    for prompt_id in selected_prompt_ids:
        prompt = prompts[prompt_id]
        pmcid = prompt["PMCID"].replace("PMC", "").strip()
        target_rows = by_prompt[prompt_id]
        majority = Counter(
            row["Label"].strip() for row in target_rows
        ).most_common(1)[0][0]
        gold_texts = unique(
            normalize(row["Annotations"])
            for row in target_rows
            if row["Label"].strip() == majority
        )
        if len(gold_texts) < 2:
            raise ValueError(f"insufficient_gold_rationales:{prompt_id}")
        distractors = select_distractors(
            prompt=prompt,
            rows=by_article[pmcid],
            target_prompt_id=prompt_id,
            excluded=set(gold_texts),
        )
        candidates = [
            {"text": text, "derived_source": "TARGET_ANNOTATION"}
            for text in gold_texts
        ] + [
            {"text": text, "derived_source": "SAME_ARTICLE_DISTRACTOR"}
            for text in distractors
        ]
        candidates.sort(
            key=lambda value: sha256(
                f"{prompt_id}|{value['text']}".encode("utf-8")
            ).hexdigest()
        )
        spans = [
            {
                "span_id": f"EI-{prompt_id}-S{index + 1}",
                "text": value["text"],
            }
            for index, value in enumerate(candidates)
        ]
        text_to_id = {value["text"]: value["span_id"] for value in spans}
        case_id = f"EI-CAL-{prompt_id}"
        item = {
            "case_id": case_id,
            "source_prompt_id": prompt_id,
            "source_pmcid": pmcid,
            "object": {
                "intervention": normalize(prompt["Intervention"]),
                "comparator": normalize(prompt["Comparator"]),
                "outcome": normalize(prompt["Outcome"]),
            },
            "candidate_spans": spans,
            "candidate_order_policy": "SHA256_PROMPT_TEXT",
        }
        public_items.append(item)
        private_gold[case_id] = {
            "label": LABEL_MAP[majority],
            "gold_rationale_span_ids": sorted(
                text_to_id[text] for text in gold_texts
            ),
            "gold_rationale_texts": gold_texts,
            "distractor_span_ids": sorted(
                text_to_id[text] for text in distractors
            ),
            "label_vote_count": sum(
                row["Label"].strip() == majority for row in target_rows
            ),
            "derived_truth_scope": (
                "MAJORITY_LABEL_AND_TARGET_ANNOTATION_RATIONALE"
            ),
        }

    commitment = {
        "bridge_version": BRIDGE_VERSION,
        "benchmark_id": benchmark_id,
        "split": split,
        "case_count": len(public_items),
        "label_balance": {
            label: sum(
                gold["label"] == label for gold in private_gold.values()
            )
            for label in LABEL_MAP.values()
        },
        "public_surface": {"items": public_items},
        "private_gold": private_gold,
        "source_manifest": manifest,
        "benchmark_native_claim": False,
        "external_transfer_claim": external_transfer_claim,
        "pretraining_contamination_excluded": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def public_panel(panel: dict[str, Any]) -> dict[str, Any]:
    return {
        "bridge_version": panel["bridge_version"],
        "benchmark_id": panel["benchmark_id"],
        "split": panel["split"],
        "public_surface": panel["public_surface"],
        "source_artifact_hash": panel["artifact_hash"],
    }


def validate_panel(panel: dict[str, Any]) -> None:
    commitment = {
        key: value for key, value in panel.items() if key != "artifact_hash"
    }
    if panel.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("benchmark_bridge_panel_hash_mismatch")
    items = panel.get("public_surface", {}).get("items", [])
    case_count = panel.get("case_count")
    if (
        not isinstance(case_count, int)
        or case_count < 1
        or len(items) != case_count
        or len(panel.get("private_gold", {})) != case_count
    ):
        raise ValueError("benchmark_bridge_case_count_invalid")
    observed_balance = {
        label: sum(
            gold["label"] == label
            for gold in panel["private_gold"].values()
        )
        for label in LABEL_MAP.values()
    }
    if panel.get("label_balance") != observed_balance:
        raise ValueError("benchmark_bridge_label_balance_invalid")
    for item in items:
        ids = [span["span_id"] for span in item["candidate_spans"]]
        if len(ids) < 4 or len(ids) != len(set(ids)):
            raise ValueError("benchmark_bridge_candidates_invalid")
        gold = panel["private_gold"][item["case_id"]]
        if set(gold["gold_rationale_span_ids"]) & set(
            gold["distractor_span_ids"]
        ):
            raise ValueError("benchmark_bridge_private_overlap")
        if set(ids) != set(gold["gold_rationale_span_ids"]) | set(
            gold["distractor_span_ids"]
        ):
            raise ValueError("benchmark_bridge_private_partition_invalid")
