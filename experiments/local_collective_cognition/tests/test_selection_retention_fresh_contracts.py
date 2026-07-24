from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selection_retention_fresh_contracts import (  # noqa: E402
    RETENTION_ROLES,
    SELECTION_ROLES,
    build_fresh_preregistration,
    build_retention_consensus,
    build_selection_consensus,
    retention_schema,
    selection_schema,
    validate_retention_receipt,
    validate_selection_receipt,
)
from local_collective_cognition.selection_retention_fresh_holdout import (  # noqa: E402
    audit_selection_retention_fresh_holdout,
    build_selection_retention_fresh_holdout,
)


REFS = ("benchmark://local-selection-retention-fresh-v0-64",)


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def setup():
    corpus = build_selection_retention_fresh_holdout()
    audit = audit_selection_retention_fresh_holdout(corpus)
    closure = artifact({
        "decision": "PASS_TYPED_EVIDENCE_BINDING_CALIBRATION",
        "core_contract_sync_eligible": True,
        "fresh_generalization_claim": False,
    })
    return corpus, build_fresh_preregistration(
        corpus=corpus,
        construction_audit=audit,
        source_closure=closure,
    )


def selection_receipt(item, role):
    alternatives = [
        value["alternative_ref"]
        for value in item["selection_alternatives"]
    ]
    return {
        "case_id": item["case_id"],
        "selection_role": role,
        "source_item_hash": hash_payload(item),
        "ranked_alternative_refs": alternatives,
        "selected_ref": "ALT:SHIFT",
        "rejected_refs": ["ALT:BASE"],
        "deferred_refs": ["ALT:PROBE"],
        "path_change_hypothesis": "Change the supported source policy.",
        "expected_cbit_gain": 0.5,
        "residual_risk": 0.2,
        "uncertainty": 0.2,
        "rationale": "Direct intervention evidence dominates.",
        "evidence_refs": list(REFS),
    }


def retention_receipt(case_id, role):
    return {
        "case_id": case_id,
        "retention_role": role,
        "source_selection_hash": "a" * 64,
        "source_consequence_hash": "b" * 64,
        "applicability_delta": 0.4,
        "validity_state": "CURRENT",
        "consequence_supported": True,
        "observed_cbit_interpretation": "POSITIVE",
        "recommended_candidate_state": "PENDING_RETENTION_REVIEW",
        "residual_risk": 0.2,
        "uncertainty": 0.2,
        "rationale": "Current positive evidence supports review.",
        "evidence_refs": list(REFS),
    }


def test_v064_preregistration_freezes_all_four_stages():
    _corpus, prereg = setup()
    assert prereg["required_binding_receipt_count"] == 16
    assert prereg["required_binding_relation_consensus_count"] == 40
    assert prereg["required_state_receipt_count"] == 16
    assert prereg["required_selection_receipt_count"] == 16
    assert prereg["required_retention_receipt_count"] == 16
    assert prereg["maximum_provider_tasks"] == 64
    assert prereg["hard_token_ceiling"] == 300000
    assert prereg["semantic_prompt_changes_after_first_receipt_allowed"] is False
    assert prereg["alpha_22_requires_all_gates"] is True


def test_selection_schema_has_no_consequence_or_authority_fields():
    corpus, _ = setup()
    item = corpus["public_surface"]["items"][0]
    schema = selection_schema(
        item=item, role=SELECTION_ROLES[0], refs=REFS
    )
    properties = schema["properties"]
    assert schema["additionalProperties"] is False
    for field in (
        "observed_cbit_gain",
        "consequence_ref",
        "validity_state",
        "retention_candidate_state",
    ):
        assert field not in properties


def test_selection_validation_and_consensus_require_real_partition():
    corpus, _ = setup()
    item = corpus["public_surface"]["items"][0]
    left = selection_receipt(item, SELECTION_ROLES[0])
    right = selection_receipt(item, SELECTION_ROLES[1])
    assert validate_selection_receipt(
        receipt=left, item=item, role=SELECTION_ROLES[0], refs=REFS
    ) == []
    consensus = build_selection_consensus(
        item=item, left=left, right=right
    )
    assert consensus["selection_ready"] is True
    assert consensus["consequence_known"] is False

    damaged = copy.deepcopy(right)
    damaged["selected_ref"] = "ALT:PROBE"
    damaged["deferred_refs"] = ["ALT:SHIFT"]
    conflict = build_selection_consensus(
        item=item, left=left, right=damaged
    )
    assert conflict["selection_ready"] is False
    assert "SELECTED_REF_DISAGREEMENT" in conflict["disagreements"]


def test_retention_contract_stays_unassigned_and_advisory():
    corpus, _ = setup()
    case_id = corpus["public_surface"]["items"][0]["case_id"]
    left = retention_receipt(case_id, RETENTION_ROLES[0])
    right = retention_receipt(case_id, RETENTION_ROLES[1])
    schema = retention_schema(
        case_id=case_id,
        role=RETENTION_ROLES[0],
        selection_hash="a" * 64,
        consequence_hash="b" * 64,
        refs=REFS,
    )
    assert schema["additionalProperties"] is False
    assert validate_retention_receipt(
        receipt=left,
        case_id=case_id,
        role=RETENTION_ROLES[0],
        selection_hash="a" * 64,
        consequence_hash="b" * 64,
        refs=REFS,
    ) == []
    consensus = build_retention_consensus(
        case_id=case_id, left=left, right=right
    )
    assert consensus["retention_ready"] is True
    assert consensus["consequence_assignment_state"] == "UNASSIGNED"
    assert consensus["retention_write_allowed"] is False
