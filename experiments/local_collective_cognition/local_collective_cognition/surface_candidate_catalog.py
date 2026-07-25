"""Deterministic source-surface catalog for v0.71."""

from __future__ import annotations

import re
from collections import defaultdict
from hashlib import sha256

from .benchmark_bridge_contracts import admission_partition
from .provider_telemetry import hash_payload


CUES = {
    "higher", "lower", "more", "less", "fewer", "increase", "increased",
    "decrease", "decreased", "effect", "difference", "significant",
    "significantly", "no", "not", "observed", "positive", "negative",
}
STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "at", "on",
    "for", "with", "vs", "versus", "group",
}


def build_surface_catalog(*, item, admission, maximum_candidates=180):
    admitted, _ = admission_partition(admission)
    admitted_set = set(admitted)
    spans = [
        span for span in item["candidate_spans"]
        if span["span_id"] in admitted_set
    ]
    object_tokens = _terms(" ".join(item["object"].values())) - STOP
    surfaces: dict[str, set[str]] = defaultdict(set)
    scores: dict[str, tuple[int, int, int]] = {}
    display: dict[str, str] = {}
    for span in spans:
        matches = list(re.finditer(r"[\w≥%<>=.-]+", span["text"]))
        for size in range(1, 11):
            for start in range(0, len(matches) - size + 1):
                group = matches[start:start + size]
                surface = span["text"][group[0].start():group[-1].end()]
                key = surface.casefold()
                terms = _terms(surface)
                overlap = len(terms & object_tokens)
                cue = int(bool(terms & CUES))
                if not overlap and not cue and size > 3:
                    continue
                surfaces[key].add(span["span_id"])
                display.setdefault(key, surface)
                scores[key] = max(
                    scores.get(key, (0, 0, 0)),
                    (overlap + 2 * cue, size, len(surface)),
                )
    ordered = sorted(
        surfaces,
        key=lambda key: (
            -scores[key][0],
            -scores[key][1],
            sha256(key.encode("utf-8")).hexdigest(),
        ),
    )[:maximum_candidates]
    candidates = [
        {
            "candidate_id": "SC-" + sha256(
                f"{item['case_id']}|{key}".encode("utf-8")
            ).hexdigest()[:16],
            "surface": display[key],
            "span_ids": sorted(surfaces[key]),
        }
        for key in ordered
    ]
    commitment = {
        "catalog_version": "surface_candidate_catalog_v0_71",
        "case_id": item["case_id"],
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "maximum_candidates": maximum_candidates,
        "candidates": candidates,
        "semantic_role_assignment_performed": False,
    }
    return {**commitment, "catalog_hash": hash_payload(commitment)}


def _terms(value):
    return {term.casefold() for term in re.findall(r"[\w]+", value)}
