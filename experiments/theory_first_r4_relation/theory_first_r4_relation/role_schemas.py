"""Mechanical responsibility-bounded receipt parsing for R4 v0.3K."""

from __future__ import annotations

from dataclasses import dataclass

from .receipt_envelope import canonicalize_receipt_envelope
from .role_cases import ROLE_CASES
from .role_prompts import ALLOWED_VALUES, ATTRIBUTES_BY_SCOPE


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
class RoleReceipt:
    scope: str
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
class ParsedRoleReceipts:
    scope: str
    receipts: tuple[RoleReceipt, ...]
    root_type: str
    source_key: str | None

    def by_case(self) -> dict[str, RoleReceipt]:
        return {receipt.case_id: receipt for receipt in self.receipts}


def parse_role_receipts(content: str, scope: str) -> ParsedRoleReceipts:
    if scope not in ATTRIBUTES_BY_SCOPE:
        raise ValueError(f"unknown role scope: {scope}")
    attributes = ATTRIBUTES_BY_SCOPE[scope]
    required = {"case_id", *attributes, "attribute_evidence_refs", "missing_facts"}
    envelope = canonicalize_receipt_envelope(content, required)
    cases = {case.case_id: case for case in ROLE_CASES}
    receipts = []
    for item in envelope.items:
        if not isinstance(item, dict):
            raise ValueError("role receipt must be an object")
        missing = required - set(item)
        if missing:
            raise ValueError(f"role fields missing: {sorted(missing)}")
        forbidden = FORBIDDEN.intersection(item)
        if forbidden:
            raise ValueError(
                f"forbidden Provider authority fields: {sorted(forbidden)}"
            )
        case_id = str(item["case_id"])
        if case_id not in cases:
            raise ValueError(f"unexpected role case: {case_id}")
        values = []
        for name in attributes:
            value = str(item[name])
            if value not in ALLOWED_VALUES[name]:
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
            RoleReceipt(
                scope=scope,
                case_id=case_id,
                attributes=tuple(values),
                refs=tuple(normalized_refs),
                missing_facts=tuple(missing_facts),
                dropped_fields=tuple(sorted(set(item) - required)),
            )
        )
    if len(receipts) != 16 or {receipt.case_id for receipt in receipts} != set(cases):
        raise ValueError("role case coverage must be exact")
    return ParsedRoleReceipts(
        scope=scope,
        receipts=tuple(sorted(receipts, key=lambda value: value.case_id)),
        root_type=envelope.root_type,
        source_key=envelope.source_key,
    )
