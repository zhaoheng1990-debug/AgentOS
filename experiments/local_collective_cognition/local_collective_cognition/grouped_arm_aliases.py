"""Deterministic, catalog-bounded aliases for grouped arm objects."""

from __future__ import annotations

import re
from typing import Any

from .provider_telemetry import hash_payload
from .relation_witness_contracts import validate_witness_frame


_GROUP_DELIMITER = re.compile(r"\s*(?:,|;|\|)\s*")
_MAX_GROUP_MEMBERS = 8


def build_grouped_alias_catalog(
    catalog: dict[str, Any],
) -> dict[str, Any]:
    arms = []
    for arm in catalog["arms"]:
        canonical = arm["canonical_text"].strip()
        members = _split_members(canonical)
        aliases = _unique([canonical, *members])
        arms.append({
            "arm_id": arm["arm_id"],
            "canonical_text": canonical,
            "accepted_aliases": aliases,
            "group_split_applied": bool(members),
            "split_rule": (
                "CATALOG_DELIMITER_MEMBERS"
                if members
                else "CANONICAL_ONLY"
            ),
        })
    value = {
        "normalizer_version": "grouped_arm_aliases_v0_74",
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "arms": arms,
        "semantic_synonyms_allowed": False,
        "provider_alias_expansion_allowed": False,
    }
    return {**value, "normalizer_hash": hash_payload(value)}


def validate_grouped_witness_frame(
    *,
    receipt,
    item,
    admission,
    catalog,
    refs,
    alias_catalog,
) -> list[str]:
    failures = validate_witness_frame(
        receipt=receipt,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
    )
    accepted = {
        arm["arm_id"]: {
            alias.casefold() for alias in arm["accepted_aliases"]
        }
        for arm in alias_catalog["arms"]
    }
    repairable = (
        (
            "WITNESS_INTERVENTION_ALIASES_UNGROUNDED",
            "intervention_aliases",
            "FOCAL_INTERVENTION",
        ),
        (
            "WITNESS_COMPARATOR_ALIASES_UNGROUNDED",
            "comparator_aliases",
            "FOCAL_COMPARATOR",
        ),
    )
    for failure, field, arm_id in repairable:
        if failure not in failures:
            continue
        aliases = receipt.get(field, [])
        if any(
            isinstance(alias, str)
            and alias.casefold() in accepted.get(arm_id, set())
            for alias in aliases
        ):
            failures.remove(failure)
    return sorted(set(failures))


def _split_members(canonical: str) -> list[str]:
    members = [
        value.strip()
        for value in _GROUP_DELIMITER.split(canonical)
    ]
    if (
        len(members) < 2
        or len(members) > _MAX_GROUP_MEMBERS
        or any(len(value) < 2 for value in members)
        or len({value.casefold() for value in members}) != len(members)
    ):
        return []
    return members


def _unique(values: list[str]) -> list[str]:
    result = []
    seen = set()
    for value in values:
        key = value.casefold()
        if key not in seen:
            result.append(value)
            seen.add(key)
    return result
