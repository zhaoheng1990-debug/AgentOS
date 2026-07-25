"""Shared contracts for factorized external benchmark adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class BenchmarkLayer(str, Enum):
    STUDY_OBJECT_BINDING = "STUDY_OBJECT_BINDING"
    SEMANTIC_WARRANT = "SEMANTIC_WARRANT"
    CONTEXT_UTILITY = "CONTEXT_UTILITY"


class LicenseDisposition(str, Enum):
    EXTERNAL_REFERENCE_ALLOWED = "EXTERNAL_REFERENCE_ALLOWED"
    SMOKE_ONLY = "SMOKE_ONLY"
    BLOCKED_LICENSE_UNCLEAR = "BLOCKED_LICENSE_UNCLEAR"


@dataclass(frozen=True)
class BenchmarkSource:
    source_id: str
    benchmark_name: str
    layer: BenchmarkLayer
    repository_url: str
    artifact_url: str
    artifact_sha256: str
    artifact_size_bytes: int
    license_disposition: LicenseDisposition
    license_note: str
    redistribution_allowed: bool = False
    revision: str = ""

    def __post_init__(self) -> None:
        if len(self.artifact_sha256) != 64:
            raise ValueError("benchmark_source_sha256_invalid")
        if self.artifact_size_bytes <= 0:
            raise ValueError("benchmark_source_size_invalid")
        if self.redistribution_allowed:
            raise ValueError("external_benchmark_redistribution_forbidden")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["layer"] = self.layer.value
        value["license_disposition"] = self.license_disposition.value
        return value


@dataclass(frozen=True)
class EvidenceUnit:
    unit_id: str
    text: str
    source_object_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.unit_id or not self.text or not self.source_object_id:
            raise ValueError("evidence_unit_required_field_missing")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PublicBenchmarkCase:
    benchmark_id: str
    case_id: str
    layer: BenchmarkLayer
    cognitive_object: Mapping[str, Any]
    evidence_units: Sequence[EvidenceUnit]
    source_revision: str

    def __post_init__(self) -> None:
        if not self.benchmark_id or not self.case_id or not self.source_revision:
            raise ValueError("public_benchmark_case_required_field_missing")
        if not self.evidence_units:
            raise ValueError("public_benchmark_case_evidence_missing")

    def to_dict(self) -> dict[str, Any]:
        return {
            "benchmark_id": self.benchmark_id,
            "case_id": self.case_id,
            "layer": self.layer.value,
            "cognitive_object": dict(self.cognitive_object),
            "evidence_units": [unit.to_dict() for unit in self.evidence_units],
            "source_revision": self.source_revision,
            "private_reference_exposed": False,
            "core_write_allowed": False,
            "retention_write_allowed": False,
        }


@dataclass(frozen=True)
class PrivateReference:
    benchmark_id: str
    case_id: str
    expected_state: str
    supporting_unit_ids: Sequence[str]
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.benchmark_id or not self.case_id or not self.expected_state:
            raise ValueError("private_reference_required_field_missing")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
