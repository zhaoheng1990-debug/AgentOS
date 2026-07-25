"""Local artifact smoke checks for the v0.86 factorized benchmark screen."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path
from typing import Any

from .acquisition import verify_external_artifact
from .catalog import source_by_id
from .qasper import build_cases


def run_smoke(
    *,
    scifact_archive: Path,
    ebm_archive: Path,
    qasper_fixture: Path,
) -> dict[str, Any]:
    receipts = [
        verify_external_artifact(
            scifact_archive,
            source_by_id("SCIFACT_RELEASE_LATEST_20210126"),
        ),
        verify_external_artifact(
            ebm_archive,
            source_by_id("EBM_NLP_2_00"),
        ),
        verify_external_artifact(
            qasper_fixture,
            source_by_id("QASPER_LED_FIXTURE_AFD0FB9"),
        ),
    ]
    scifact_counts = _scifact_counts(scifact_archive)
    ebm_counts = _ebm_counts(ebm_archive)
    qasper_counts = _qasper_counts(qasper_fixture)
    failures = [
        failure
        for receipt in receipts
        for failure in receipt["failures"]
    ]
    return {
        "smoke_version": "factorized_benchmark_smoke_v0_86",
        "artifact_receipts": receipts,
        "dataset_counts": {
            "scifact": scifact_counts,
            "ebm_nlp": ebm_counts,
            "qasper_fixture": qasper_counts,
        },
        "all_artifacts_verified": all(
            receipt["verified"] for receipt in receipts
        ),
        "failures": failures,
        "provider_calls": 0,
        "private_reference_exposed_to_provider": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }


def _scifact_counts(path: Path) -> dict[str, int]:
    expected = {
        "data/claims_train.jsonl",
        "data/claims_dev.jsonl",
        "data/claims_test.jsonl",
        "data/corpus.jsonl",
    }
    with tarfile.open(path, "r:gz") as archive:
        names = set(archive.getnames())
        missing = expected - names
        if missing:
            raise ValueError(f"scifact_members_missing:{sorted(missing)}")
        return {
            name.removeprefix("data/").removesuffix(".jsonl"): _jsonl_count(
                archive, name
            )
            for name in sorted(expected)
        }


def _jsonl_count(archive: tarfile.TarFile, name: str) -> int:
    extracted = archive.extractfile(name)
    if extracted is None:
        raise ValueError(f"archive_member_unreadable:{name}")
    return sum(1 for line in io.TextIOWrapper(extracted, encoding="utf-8") if line)


def _ebm_counts(path: Path) -> dict[str, int]:
    with tarfile.open(path, "r:gz") as archive:
        names = archive.getnames()
    return {
        "documents": sum(name.endswith(".txt") for name in names),
        "token_files": sum(name.endswith(".tokens") for name in names),
        "annotation_files": sum(name.endswith(".ann") for name in names),
    }


def _qasper_counts(path: Path) -> dict[str, int]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    case_count = 0
    evidence_unit_count = 0
    for article_id, article in payload.items():
        cases = build_cases(article_id, article)
        case_count += len(cases)
        evidence_unit_count += sum(
            len(public.evidence_units) for public, _ in cases
        )
    return {
        "articles": len(payload),
        "cases": case_count,
        "case_evidence_units": evidence_unit_count,
    }
