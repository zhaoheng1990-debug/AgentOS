"""Read-only port for project-scoped organization trial evidence."""

from __future__ import annotations

from typing import Protocol

from agentos_kernel import OrganizationTrialRecord


class OrganizationTrialRecordSource(Protocol):
    def organization_records(
        self,
        *,
        project_scope: str,
        context_key: str,
        evidence_tier: str,
    ) -> tuple[OrganizationTrialRecord, ...]:
        """Return admitted records for one exact project/context/tier."""


def collect_organization_records(
    *,
    source: OrganizationTrialRecordSource | None,
    project_scope: str,
    context_key: str,
    evidence_tier: str,
    explicit: tuple[OrganizationTrialRecord, ...],
) -> tuple[OrganizationTrialRecord, ...]:
    sourced = (
        source.organization_records(
            project_scope=project_scope,
            context_key=context_key,
            evidence_tier=evidence_tier,
        )
        if source is not None
        else ()
    )
    records = (*sourced, *explicit)
    by_hash = {item.record_hash: item for item in records}
    if len(by_hash) != len(records):
        raise ValueError("contextual_policy_duplicate_record_hash")
    return tuple(by_hash.values())
