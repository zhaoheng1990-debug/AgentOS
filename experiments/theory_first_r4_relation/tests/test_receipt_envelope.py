import json

import pytest

from theory_first_r4_relation.envelope_cases import (
    ACCEPTED_CASES,
    REJECTED_CASES,
    required_keys,
)
from theory_first_r4_relation.receipt_envelope import (
    canonicalize_receipt_envelope,
)


@pytest.mark.parametrize("case", ACCEPTED_CASES, ids=lambda case: case.case_id)
def test_frozen_accepted_shapes(case) -> None:
    result = canonicalize_receipt_envelope(
        json.dumps(case.root, ensure_ascii=True), required_keys()
    )
    assert result.root_type == case.expected_root_type
    assert result.source_key == case.expected_source_key
    assert result.root_metadata_fields == case.expected_metadata_fields


@pytest.mark.parametrize("case", REJECTED_CASES, ids=lambda case: case.case_id)
def test_frozen_rejected_shapes(case) -> None:
    with pytest.raises(ValueError):
        canonicalize_receipt_envelope(
            json.dumps(case.root, ensure_ascii=True), required_keys()
        )


def test_canonicalizer_copies_item_values() -> None:
    root = {"unseen": [{"case_id": "one", "field": ["original"]}]}
    result = canonicalize_receipt_envelope(
        json.dumps(root), {"case_id", "field"}
    )
    root["unseen"][0]["field"].append("mutated")
    assert result.items[0]["field"] == ["original"]

