"""EBM-NLP adapter for study-object span binding evaluation."""

from __future__ import annotations

from itertools import groupby
from typing import Sequence

from .catalog import source_by_id
from .contracts import (
    BenchmarkLayer,
    EvidenceUnit,
    PrivateReference,
    PublicBenchmarkCase,
)

SOURCE_ID = "EBM_NLP_2_00"


def build_case(
    *,
    pmid: str,
    tokens: Sequence[str],
    labels_by_kind: dict[str, Sequence[int]],
) -> tuple[PublicBenchmarkCase, PrivateReference]:
    source = source_by_id(SOURCE_ID)
    for kind in ("participants", "interventions", "outcomes"):
        if kind not in labels_by_kind:
            raise ValueError(f"ebm_nlp_{kind}_labels_missing")
        if len(labels_by_kind[kind]) != len(tokens):
            raise ValueError(f"ebm_nlp_{kind}_label_length_mismatch")
    public = PublicBenchmarkCase(
        benchmark_id="EBM_NLP",
        case_id=pmid,
        layer=BenchmarkLayer.STUDY_OBJECT_BINDING,
        cognitive_object={
            "task": "bind_participant_intervention_outcome_spans",
            "allowed_kinds": ["participants", "interventions", "outcomes"],
        },
        evidence_units=(
            EvidenceUnit(
                unit_id=f"{pmid}:abstract",
                text=" ".join(tokens),
                source_object_id=pmid,
                metadata={"token_count": len(tokens)},
            ),
        ),
        source_revision=source.revision,
    )
    spans = []
    for kind, labels in labels_by_kind.items():
        spans.extend(_labeled_spans(tokens, labels, kind))
    private = PrivateReference(
        benchmark_id="EBM_NLP",
        case_id=pmid,
        expected_state="OBJECT_SPANS_ANNOTATED",
        supporting_unit_ids=(f"{pmid}:abstract",),
        metadata={"gold_spans": spans},
    )
    return public, private


def _labeled_spans(
    tokens: Sequence[str],
    labels: Sequence[int],
    kind: str,
) -> list[dict[str, object]]:
    spans = []
    cursor = 0
    for label, values in groupby(labels):
        length = sum(1 for _ in values)
        if label:
            spans.append(
                {
                    "kind": kind,
                    "label": int(label),
                    "token_start": cursor,
                    "token_end": cursor + length,
                    "text": " ".join(tokens[cursor : cursor + length]),
                }
            )
        cursor += length
    return spans
