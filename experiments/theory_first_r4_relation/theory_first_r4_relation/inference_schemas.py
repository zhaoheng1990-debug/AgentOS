"""Mechanical canonicalization for R4 v0.3G Provider receipts."""

from __future__ import annotations

from dataclasses import dataclass

from .inference_cases import ATTRIBUTE_NAMES, InferenceCase
from .receipt_envelope import canonicalize_receipt_envelope
from .transform_contracts import (
    ADDED_UNCERTAINTIES,
    INFORMATION_RELATIONS,
    LINEAGE_COUPLINGS,
    SOURCE_IDENTITIES,
    TARGET_CLAIM_RELATIONS,
)


REQUIRED_KEYS = {
    "case_id",
    *ATTRIBUTE_NAMES,
    "attribute_evidence_refs",
    "missing_facts",
}
FORBIDDEN_KEYS = {
    "accepted",
    "action",
    "baseline_state",
    "composition_action",
    "final_state",
    "probability",
    "published",
    "relation_state",
    "retained",
    "selected_packet_ids",
}
ALLOWED_VALUES = {
    "source_identity": SOURCE_IDENTITIES,
    "lineage_coupling": LINEAGE_COUPLINGS,
    "information_relation": INFORMATION_RELATIONS,
    "added_uncertainty": ADDED_UNCERTAINTIES,
    "target_claim_relation": TARGET_CLAIM_RELATIONS,
}


@dataclass(frozen=True)
class AttributeInferenceReceipt:
    case_id: str
    attributes: tuple[tuple[str, str], ...]
    attribute_evidence_refs: tuple[tuple[str, tuple[str, ...]], ...]
    missing_facts: tuple[str, ...]
    dropped_provider_fields: tuple[str, ...]

    def attribute_dict(self) -> dict[str, str]:
        return dict(self.attributes)

    def ref_dict(self) -> dict[str, tuple[str, ...]]:
        return dict(self.attribute_evidence_refs)


@dataclass(frozen=True)
class ParsedAttributeReceipts:
    receipts: tuple[AttributeInferenceReceipt, ...]
    root_type: str
    source_key: str | None
    root_metadata_fields: tuple[str, ...]


def parse_attribute_receipts(
    content: str, expected_cases: tuple[InferenceCase, ...]
) -> ParsedAttributeReceipts:
    envelope = canonicalize_receipt_envelope(content, REQUIRED_KEYS)
    expected = {case.case_id: case for case in expected_cases}
    receipts = []
    for item in envelope.items:
        if not isinstance(item, dict):
            raise ValueError("attribute receipt must be an object")
        missing = REQUIRED_KEYS - set(item)
        if missing:
            raise ValueError(f"attribute receipt fields missing: {sorted(missing)}")
        forbidden = FORBIDDEN_KEYS.intersection(item)
        if forbidden:
            raise ValueError(f"forbidden Provider authority fields: {sorted(forbidden)}")
        case_id = str(item["case_id"])
        if case_id not in expected:
            raise ValueError(f"unexpected attribute case: {case_id}")
        attributes = []
        for name in ATTRIBUTE_NAMES:
            value = str(item[name])
            if value not in ALLOWED_VALUES[name]:
                raise ValueError(f"unknown {name} value: {value}")
            attributes.append((name, value))
        refs_value = item["attribute_evidence_refs"]
        if not isinstance(refs_value, dict) or set(refs_value) != set(ATTRIBUTE_NAMES):
            raise ValueError(f"attribute evidence keys invalid: {case_id}")
        admitted = set(expected[case_id].evidence_refs)
        refs = []
        for name in ATTRIBUTE_NAMES:
            values = refs_value[name]
            if (
                not isinstance(values, list)
                or not values
                or not all(isinstance(value, str) for value in values)
                or not set(values).issubset(admitted)
            ):
                raise ValueError(f"attribute evidence scope mismatch: {case_id}:{name}")
            refs.append((name, tuple(sorted(set(values)))))
        missing_facts = item["missing_facts"]
        if not isinstance(missing_facts, list) or not all(
            isinstance(value, str) for value in missing_facts
        ):
            raise ValueError(f"missing facts invalid: {case_id}")
        receipts.append(
            AttributeInferenceReceipt(
                case_id=case_id,
                attributes=tuple(attributes),
                attribute_evidence_refs=tuple(refs),
                missing_facts=tuple(missing_facts),
                dropped_provider_fields=tuple(sorted(set(item) - REQUIRED_KEYS)),
            )
        )
    if len(receipts) != len(expected) or {item.case_id for item in receipts} != set(
        expected
    ):
        raise ValueError("attribute case coverage must be exact")
    return ParsedAttributeReceipts(
        receipts=tuple(sorted(receipts, key=lambda item: item.case_id)),
        root_type=envelope.root_type,
        source_key=envelope.source_key,
        root_metadata_fields=envelope.root_metadata_fields,
    )

