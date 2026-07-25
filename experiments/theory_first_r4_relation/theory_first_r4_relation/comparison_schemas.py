"""Mechanical arm-specific receipt parsing for R4 v0.3J."""

from __future__ import annotations

from dataclasses import dataclass

from .comparison_cases import (
    COMPARISON_CASES,
    FACTORIZED_ATTRIBUTES,
    LEGACY_ATTRIBUTES,
)
from .comparison_prompts import SHARED_ALLOWED
from .factor_contracts import INFORMATION_EFFECTS, TRANSFORM_STATUSES
from .receipt_envelope import canonicalize_receipt_envelope
from .transform_contracts import INFORMATION_RELATIONS


FORBIDDEN = {
    "action",
    "accepted",
    "baseline_state",
    "composition_action",
    "final_state",
    "probability",
    "published",
    "relation_state",
    "retained",
    "revalidation",
}


@dataclass(frozen=True)
class ComparisonReceipt:
    arm: str
    case_id: str
    attributes: tuple[tuple[str, str], ...]
    refs: tuple[tuple[str, tuple[str, ...]], ...]
    missing_facts: tuple[str, ...]
    dropped_fields: tuple[str, ...]

    def attribute_dict(self) -> dict[str, str]:
        return dict(self.attributes)

    def ref_dict(self) -> dict[str, tuple[str, ...]]:
        return dict(self.refs)


@dataclass(frozen=True)
class ParsedComparisonReceipts:
    arm: str
    receipts: tuple[ComparisonReceipt, ...]
    root_type: str
    source_key: str | None


def parse_comparison_receipts(content: str, arm: str) -> ParsedComparisonReceipts:
    attributes = LEGACY_ATTRIBUTES if arm == "legacy" else FACTORIZED_ATTRIBUTES
    allowed = SHARED_ALLOWED | (
        {"information_relation": INFORMATION_RELATIONS}
        if arm == "legacy"
        else {
            "transform_status": TRANSFORM_STATUSES,
            "information_effect": INFORMATION_EFFECTS,
        }
    )
    required = {"case_id", *attributes, "attribute_evidence_refs", "missing_facts"}
    envelope = canonicalize_receipt_envelope(content, required)
    cases = {case.case_id: case for case in COMPARISON_CASES}
    receipts = []
    for item in envelope.items:
        if not isinstance(item, dict):
            raise ValueError("comparison receipt must be an object")
        missing = required - set(item)
        if missing:
            raise ValueError(f"comparison fields missing: {sorted(missing)}")
        forbidden = FORBIDDEN.intersection(item)
        if forbidden:
            raise ValueError(f"forbidden Provider authority fields: {sorted(forbidden)}")
        case_id = str(item["case_id"])
        if case_id not in cases:
            raise ValueError(f"unexpected comparison case: {case_id}")
        values = []
        for name in attributes:
            value = str(item[name])
            if value not in allowed[name]:
                raise ValueError(f"unknown {name}: {value}")
            values.append((name, value))
        refs = item["attribute_evidence_refs"]
        if not isinstance(refs, dict) or set(refs) != set(attributes):
            raise ValueError(f"attribute evidence keys invalid: {case_id}")
        admitted = set(cases[case_id].refs)
        normalized_refs = []
        for name in attributes:
            selected = refs[name]
            if (
                not isinstance(selected, list)
                or not selected
                or not all(isinstance(value, str) for value in selected)
                or not set(selected).issubset(admitted)
            ):
                raise ValueError(f"evidence scope mismatch: {case_id}:{name}")
            normalized_refs.append((name, tuple(sorted(set(selected)))))
        missing_facts = item["missing_facts"]
        if not isinstance(missing_facts, list) or not all(
            isinstance(value, str) for value in missing_facts
        ):
            raise ValueError(f"missing facts invalid: {case_id}")
        receipts.append(
            ComparisonReceipt(
                arm,
                case_id,
                tuple(values),
                tuple(normalized_refs),
                tuple(missing_facts),
                tuple(sorted(set(item) - required)),
            )
        )
    if len(receipts) != 12 or {receipt.case_id for receipt in receipts} != set(cases):
        raise ValueError("comparison case coverage must be exact")
    return ParsedComparisonReceipts(
        arm,
        tuple(sorted(receipts, key=lambda value: value.case_id)),
        envelope.root_type,
        envelope.source_key,
    )
