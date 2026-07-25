"""Deterministic, key-agnostic receipt-envelope canonicalization."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from typing import Any, Collection


@dataclass(frozen=True)
class CanonicalReceiptEnvelope:
    items: tuple[dict[str, Any], ...]
    root_type: str
    source_key: str | None
    root_metadata_fields: tuple[str, ...]


def _canonical_items(
    value: list[Any], required_keys: frozenset[str]
) -> tuple[dict[str, Any], ...]:
    if not value:
        raise ValueError("receipt collection must be non-empty")
    if not all(isinstance(item, dict) for item in value):
        raise ValueError("receipt collection items must be objects")
    if not all(required_keys.issubset(item) for item in value):
        raise ValueError("receipt collection must be homogeneous and receipt-shaped")
    return tuple(copy.deepcopy(item) for item in value)


def canonicalize_receipt_envelope(
    content: str, required_keys: Collection[str]
) -> CanonicalReceiptEnvelope:
    root = json.loads(content)
    required = frozenset(required_keys)
    if not required:
        raise ValueError("required receipt keys must be non-empty")

    if isinstance(root, list):
        return CanonicalReceiptEnvelope(
            items=_canonical_items(root, required),
            root_type="root_array",
            source_key=None,
            root_metadata_fields=(),
        )

    if not isinstance(root, dict):
        raise ValueError("receipt envelope root must be an object or array")

    if required.issubset(root):
        return CanonicalReceiptEnvelope(
            items=(copy.deepcopy(root),),
            root_type="direct_item",
            source_key=None,
            root_metadata_fields=(),
        )

    list_fields = [
        key for key, value in root.items() if isinstance(value, list)
    ]
    if len(list_fields) != 1:
        raise ValueError("receipt envelope must contain exactly one list field")

    source_key = list_fields[0]
    metadata = {key: value for key, value in root.items() if key != source_key}
    if any(isinstance(value, (dict, list)) for value in metadata.values()):
        raise ValueError("receipt envelope metadata must be scalar")

    return CanonicalReceiptEnvelope(
        items=_canonical_items(root[source_key], required),
        root_type="object_collection",
        source_key=source_key,
        root_metadata_fields=tuple(sorted(metadata)),
    )

