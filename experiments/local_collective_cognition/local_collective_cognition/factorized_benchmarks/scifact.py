"""SciFact adapter for claim-to-evidence semantic warrant evaluation."""

from __future__ import annotations

from typing import Any, Mapping

from .catalog import source_by_id
from .contracts import (
    BenchmarkLayer,
    EvidenceUnit,
    PrivateReference,
    PublicBenchmarkCase,
)

SOURCE_ID = "SCIFACT_RELEASE_LATEST_20210126"


def build_case(
    claim: Mapping[str, Any],
    corpus_by_doc_id: Mapping[int, Mapping[str, Any]],
) -> tuple[PublicBenchmarkCase, PrivateReference]:
    source = source_by_id(SOURCE_ID)
    cited_ids = [int(value) for value in claim.get("cited_doc_ids", [])]
    evidence_ids = [int(value) for value in claim.get("evidence", {})]
    candidate_doc_ids = list(dict.fromkeys(cited_ids + evidence_ids))
    units = []
    for doc_id in candidate_doc_ids:
        document = corpus_by_doc_id[doc_id]
        for sentence_index, sentence in enumerate(document["abstract"]):
            units.append(
                EvidenceUnit(
                    unit_id=f"{doc_id}:{sentence_index}",
                    text=sentence,
                    source_object_id=str(doc_id),
                    metadata={
                        "title": document["title"],
                        "sentence_index": sentence_index,
                    },
                )
            )
    public = PublicBenchmarkCase(
        benchmark_id="SCIFACT",
        case_id=str(claim["id"]),
        layer=BenchmarkLayer.SEMANTIC_WARRANT,
        cognitive_object={"claim": claim["claim"]},
        evidence_units=units,
        source_revision=source.revision,
    )
    supporting_ids = []
    labels = set()
    for doc_id, rationales in claim.get("evidence", {}).items():
        for rationale in rationales:
            labels.add(rationale["label"])
            supporting_ids.extend(
                f"{doc_id}:{index}" for index in rationale["sentences"]
            )
    expected_state = _expected_state(labels)
    private = PrivateReference(
        benchmark_id="SCIFACT",
        case_id=str(claim["id"]),
        expected_state=expected_state,
        supporting_unit_ids=tuple(sorted(set(supporting_ids))),
        metadata={"gold_labels": sorted(labels)},
    )
    return public, private


def _expected_state(labels: set[str]) -> str:
    if labels == {"SUPPORT"}:
        return "SUPPORTED"
    if labels == {"CONTRADICT"}:
        return "REFUTED"
    if not labels:
        return "NOT_ENOUGH_INFO"
    return "CONFLICTING"
