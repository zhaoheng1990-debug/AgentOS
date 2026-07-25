"""QASPER adapter for question-conditioned context utility evaluation."""

from __future__ import annotations

from typing import Any, Mapping

from .catalog import source_by_id
from .contracts import (
    BenchmarkLayer,
    EvidenceUnit,
    PrivateReference,
    PublicBenchmarkCase,
)

SOURCE_ID = "QASPER_LED_FIXTURE_AFD0FB9"


def build_cases(
    article_id: str,
    article: Mapping[str, Any],
) -> list[tuple[PublicBenchmarkCase, PrivateReference]]:
    source = source_by_id(SOURCE_ID)
    units = _paragraph_units(article_id, article)
    cases = []
    for position, qa in enumerate(article["qas"]):
        case_id = f"{article_id}:{qa['question_id']}:{position}"
        public = PublicBenchmarkCase(
            benchmark_id="QASPER",
            case_id=case_id,
            layer=BenchmarkLayer.CONTEXT_UTILITY,
            cognitive_object={"question": qa["question"]},
            evidence_units=units,
            source_revision=source.revision,
        )
        evidence_texts = {
            text.strip()
            for annotation in qa["answers"]
            for text in annotation["answer"].get("evidence", [])
            if text.strip()
        }
        supporting_ids = tuple(
            unit.unit_id for unit in units if unit.text in evidence_texts
        )
        answer_types = sorted(
            {_answer_type(annotation["answer"]) for annotation in qa["answers"]}
        )
        private = PrivateReference(
            benchmark_id="QASPER",
            case_id=case_id,
            expected_state=(
                "ANSWERABLE_WITH_CONTEXT"
                if supporting_ids
                else "NO_EVIDENCE_ANNOTATED"
            ),
            supporting_unit_ids=supporting_ids,
            metadata={"answer_types": answer_types},
        )
        cases.append((public, private))
    return cases


def _paragraph_units(
    article_id: str,
    article: Mapping[str, Any],
) -> tuple[EvidenceUnit, ...]:
    units = [
        EvidenceUnit(
            unit_id=f"{article_id}:abstract",
            text=article["abstract"],
            source_object_id=article_id,
            metadata={"section": "abstract"},
        )
    ]
    paragraph_index = 0
    for section in article["full_text"]:
        section_name = section.get("section_name") or ""
        for paragraph in section["paragraphs"]:
            normalized = paragraph.replace("\n", " ").strip()
            if not normalized:
                continue
            units.append(
                EvidenceUnit(
                    unit_id=f"{article_id}:paragraph:{paragraph_index}",
                    text=normalized,
                    source_object_id=article_id,
                    metadata={"section": section_name},
                )
            )
            paragraph_index += 1
    return tuple(units)


def _answer_type(answer: Mapping[str, Any]) -> str:
    if answer.get("unanswerable", False):
        return "UNANSWERABLE"
    if answer.get("yes_no") is not None:
        return "BOOLEAN"
    if answer.get("extractive_spans"):
        return "EXTRACTIVE"
    return "ABSTRACTIVE"
