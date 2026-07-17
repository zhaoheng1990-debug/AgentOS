"""Domain-neutral evidence dimension registry and source hygiene."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any


SOURCE_AUDIT_EXCLUSIONS = (
    "outputs/",
    "return_packs/",
    "caches/",
    "__pycache__/",
    ".pytest_cache/",
    "provider_traces/",
    "tmp/",
    "_tmp",
)


@dataclass(frozen=True)
class EvidenceDimensionSpec:
    dimension_id: str
    claim_support_model: str
    freshness_policy: str
    evidence_admission_requirements: tuple[str, ...]
    conflict_strategy: str
    coverage_object_model: str
    cbit_gain_model: str = "qualitative"
    convergence_stop_condition: str = "dimension_owner_defined"
    plugin_owner: str = "core"


class EvidenceDimensionRegistry:
    def __init__(self) -> None:
        self._dimensions: dict[str, EvidenceDimensionSpec] = {}

    def register(self, spec: EvidenceDimensionSpec) -> None:
        if spec.dimension_id in self._dimensions:
            raise ValueError(f"evidence_dimension_already_registered:{spec.dimension_id}")
        self._dimensions[spec.dimension_id] = spec

    def get(self, dimension_id: str) -> EvidenceDimensionSpec:
        if dimension_id not in self._dimensions:
            raise KeyError(f"unknown_evidence_dimension:{dimension_id}")
        return self._dimensions[dimension_id]

    def as_read_model(self) -> dict[str, Any]:
        return {
            "dimension_count": len(self._dimensions),
            "dimensions": {
                key: {
                    "claim_support_model": value.claim_support_model,
                    "freshness_policy": value.freshness_policy,
                    "evidence_admission_requirements": list(value.evidence_admission_requirements),
                    "conflict_strategy": value.conflict_strategy,
                    "coverage_object_model": value.coverage_object_model,
                    "cbit_gain_model": value.cbit_gain_model,
                    "convergence_stop_condition": value.convergence_stop_condition,
                    "plugin_owner": value.plugin_owner,
                }
                for key, value in sorted(self._dimensions.items())
            },
        }


def is_source_audit_excluded(path: str) -> bool:
    normalized = PurePosixPath(path.replace("\\", "/")).as_posix().lstrip("./")
    return any(normalized.startswith(prefix) or f"/{prefix}" in normalized for prefix in SOURCE_AUDIT_EXCLUSIONS)
