import json

from theory_first_r4.cases import CASES
from theory_first_r4.schemas import (
    COORDINATOR_BASIS,
    ROLE_BASIS,
    parse_coordinator_receipts,
    parse_role_receipts,
)


def test_role_receipt_contract() -> None:
    content = json.dumps(
        {
            "receipts": [
                {
                    "case_id": case.case_id,
                    "role_id": "ROLE_A",
                    "evidence_id": case.evidence_id("ROLE_A"),
                    "probability_y1": 0.6,
                    "direction": "Y1",
                    "calculation_basis": ROLE_BASIS,
                    "assumptions": ["ONLY_ASSIGNED_EVIDENCE", "COMMON_PRIOR"],
                }
                for case in CASES
            ]
        }
    )
    assert len(parse_role_receipts(content, "ROLE_A")) == 12


def test_coordinator_receipt_contract() -> None:
    content = json.dumps(
        {
            "receipts": [
                {
                    "case_id": case.case_id,
                    "included_roles": ["ROLE_A", "ROLE_B"],
                    "probability_y1": 0.6,
                    "direction": "Y1",
                    "composition_basis": COORDINATOR_BASIS,
                    "raw_evidence_used": False,
                    "private_reference_used": False,
                }
                for case in CASES
            ]
        }
    )
    assert len(
        parse_coordinator_receipts(content, ("ROLE_A", "ROLE_B"))
    ) == 12

