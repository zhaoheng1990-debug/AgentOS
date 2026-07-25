"""Mechanical acquisition checks; this module never downloads benchmark data."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from .catalog import CATALOG_VERSION
from .contracts import BenchmarkSource


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_external_artifact(
    path: Path,
    source: BenchmarkSource,
) -> dict[str, Any]:
    actual_size = path.stat().st_size
    actual_sha256 = sha256_file(path)
    failures = []
    if actual_size != source.artifact_size_bytes:
        failures.append("ARTIFACT_SIZE_MISMATCH")
    if actual_sha256 != source.artifact_sha256:
        failures.append("ARTIFACT_SHA256_MISMATCH")
    return {
        "catalog_version": CATALOG_VERSION,
        "source_id": source.source_id,
        "path": str(path.resolve()),
        "expected_size_bytes": source.artifact_size_bytes,
        "actual_size_bytes": actual_size,
        "expected_sha256": source.artifact_sha256,
        "actual_sha256": actual_sha256,
        "verified": not failures,
        "failures": failures,
        "redistribution_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
