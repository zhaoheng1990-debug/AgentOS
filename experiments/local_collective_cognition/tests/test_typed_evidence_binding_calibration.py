from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    build_portfolio_critic_fresh_holdout_v0_61_1,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.typed_evidence_binding_contracts import (  # noqa: E402
    BINDING_ROLES,
    STATE_ROLES,
    build_typed_consensus,
    build_typed_preregistration,
    expected_states,
    relation_ids_for,
    typed_binding_schema,
    validate_typed_binding_receipt,
    validate_typed_state_receipt,
)
from local_collective_cognition.typed_evidence_binding_runtime import (  # noqa: E402
    analyze_typed_state_panel,
)


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _run(value):
    return {**value, "run_hash": hash_payload(value)}


def _setup():
    corpus = build_portfolio_critic_fresh_holdout_v0_61_1()
    closure = _artifact({
        "decision": "REJECT_RELATION_EVIDENCE_BINDING_CONSENSUS_GATE",
        "typed_evidence_set_calibration_required": True,
        "state_assessment_executed": False,
    })
    return corpus, build_typed_preregistration(
        corpus=corpus,
        source_closure=closure,
    )


def _binding_receipt(item, role):
    relations = []
    for index, relation_id in enumerate(relation_ids_for(item), start=1):
        relations.append({
            "relation_id": relation_id,
            "source_object_id": relation_id.split("-")[1],
            "target_object_id": item["focal_object_id"],
            "source_object_binding": "EXACT_EXPLICIT",
            "target_outcome_binding": "EXACT_EXPLICIT",
            "evidence_design": "UNTESTED_DIFFERENCE",
            "primary_evidence_span_ids": [f"S{index}"],
            "corroborating_evidence_span_ids": [],
            "counterevidence_span_ids": [],
            "gap_evidence_span_ids": [],
            "rationale": "test",
        })
    return {
        "case_id": item["case_id"],
        "binding_role": role,
        "source_item_hash": hash_payload(item),
        "all_relations_assessed": True,
        "relation_bindings": relations,
        "evidence_refs": ["benchmark://local-portfolio-critic-fresh-v0-61-1"],
    }


def test_typed_schema_forbids_truth_and_binding_state():
    corpus, _ = _setup()
    item = corpus["public_surface"]["items"][0]
    schema = typed_binding_schema(
        item=item,
        role=BINDING_ROLES[0],
        refs=tuple(corpus["evidence_refs"]),
    )
    relation = schema["properties"]["relation_bindings"]["items"]
    assert "relation_truth_state" not in relation["properties"]
    assert "binding_state" not in relation["properties"]
    assert relation["additionalProperties"] is False


def test_typed_binding_rejects_cross_type_overlap():
    corpus, _ = _setup()
    item = corpus["public_surface"]["items"][0]
    receipt = _binding_receipt(item, BINDING_ROLES[0])
    receipt["relation_bindings"][0][
        "corroborating_evidence_span_ids"
    ] = ["S1"]
    failures = validate_typed_binding_receipt(
        receipt=receipt,
        item=item,
        role=BINDING_ROLES[0],
        refs=tuple(corpus["evidence_refs"]),
    )
    assert "BINDING_EVIDENCE_TYPE_OVERLAP" in failures


def test_consensus_unions_nonconflicting_corroboration():
    corpus, _ = _setup()
    item = next(
        value
        for value in corpus["public_surface"]["items"]
        if value["case_id"] == "PC-HVAC"
    )
    left = _binding_receipt(item, BINDING_ROLES[0])
    right = _binding_receipt(item, BINDING_ROLES[1])
    left["relation_bindings"][3]["evidence_design"] = (
        "INTERVENTION_OR_ROLLBACK"
    )
    right["relation_bindings"][3]["evidence_design"] = (
        "INTERVENTION_OR_ROLLBACK"
    )
    left["relation_bindings"][3][
        "corroborating_evidence_span_ids"
    ] = ["S6"]
    consensus, conflicts, divergences = build_typed_consensus(
        item=item,
        left=left,
        right=right,
    )
    assert conflicts == []
    relation = consensus["relation_bindings"][3]
    assert relation["primary_evidence_span_ids"] == ["S4"]
    assert relation["corroborating_evidence_span_ids"] == ["S6"]
    assert len(divergences) == 1


def test_consensus_blocks_primary_or_cross_type_disagreement():
    corpus, _ = _setup()
    item = corpus["public_surface"]["items"][0]
    left = _binding_receipt(item, BINDING_ROLES[0])
    right = _binding_receipt(item, BINDING_ROLES[1])
    right["relation_bindings"][0]["primary_evidence_span_ids"] = ["S2"]
    consensus, conflicts, _ = build_typed_consensus(
        item=item,
        left=left,
        right=right,
    )
    assert consensus["binding_ready"] is False
    assert "PRIMARY_EVIDENCE_DISAGREEMENT" in conflicts[0]["reasons"]

    right = _binding_receipt(item, BINDING_ROLES[1])
    left["relation_bindings"][0][
        "corroborating_evidence_span_ids"
    ] = ["S6"]
    right["relation_bindings"][0]["counterevidence_span_ids"] = ["S6"]
    _, conflicts, _ = build_typed_consensus(
        item=item,
        left=left,
        right=right,
    )
    assert "EVIDENCE_TYPE_CONFLICT" in conflicts[0]["reasons"]


def test_state_validation_requires_primary_and_blocks_gap_promotion():
    corpus, _ = _setup()
    item = corpus["public_surface"]["items"][0]
    left = _binding_receipt(item, BINDING_ROLES[0])
    right = _binding_receipt(item, BINDING_ROLES[1])
    binding, conflicts, _ = build_typed_consensus(
        item=item,
        left=left,
        right=right,
    )
    assert conflicts == []
    assessments = [{
        "relation_id": relation["relation_id"],
        "relation_truth_state": "UNRESOLVED",
        "cited_primary_span_ids": relation["primary_evidence_span_ids"],
        "cited_corroborating_span_ids": [],
        "cited_counterevidence_span_ids": [],
        "cited_gap_evidence_span_ids": [],
        "rationale": "test",
    } for relation in binding["relation_bindings"]]
    receipt = {
        "case_id": item["case_id"],
        "state_role": STATE_ROLES[0],
        "source_binding_consensus_hash": binding["artifact_hash"],
        "all_relations_assessed": True,
        "relation_assessments": assessments,
        "evidence_refs": list(corpus["evidence_refs"]),
    }
    assert validate_typed_state_receipt(
        receipt=receipt,
        item=item,
        role=STATE_ROLES[0],
        binding_receipt=binding,
        refs=tuple(corpus["evidence_refs"]),
    ) == []
    receipt["relation_assessments"][0][
        "relation_truth_state"
    ] = "SUPPORTED_EFFECT"
    receipt["relation_assessments"][0]["cited_primary_span_ids"] = []
    failures = validate_typed_state_receipt(
        receipt=receipt,
        item=item,
        role=STATE_ROLES[0],
        binding_receipt=binding,
        refs=tuple(corpus["evidence_refs"]),
    )
    assert "STATE_PRIMARY_EVIDENCE_NOT_PRESERVED" in failures
    assert "STATE_EFFECT_WITHOUT_PRIMARY_EFFECT_DESIGN" in failures
    assert "STATE_GAP_OR_UNBOUND_PROMOTED" in failures


def test_perfect_typed_panel_passes_and_mismatch_rejects():
    corpus, preregistration = _setup()
    consensus_receipts = {}
    for item in corpus["public_surface"]["items"]:
        left = _binding_receipt(item, BINDING_ROLES[0])
        right = _binding_receipt(item, BINDING_ROLES[1])
        expected = expected_states(corpus)[item["case_id"]]
        for relation in left["relation_bindings"]:
            state = expected[relation["relation_id"]]
            relation["evidence_design"] = (
                "INTERVENTION_OR_ROLLBACK"
                if state == "SUPPORTED_EFFECT"
                else "MATCHED_NULL_COMPARISON"
                if state == "SUPPORTED_NULL"
                else "UNTESTED_DIFFERENCE"
            )
        right["relation_bindings"] = copy.deepcopy(
            left["relation_bindings"]
        )
        consensus, conflicts, _ = build_typed_consensus(
            item=item,
            left=left,
            right=right,
        )
        assert conflicts == []
        consensus_receipts[item["case_id"]] = consensus
    binding_run = _run({
        "raw_receipts": {
            f"{role}:{item['case_id']}": {"valid": True}
            for role in BINDING_ROLES
            for item in corpus["public_surface"]["items"]
        },
        "binding_relation_consensus_count": 30,
        "binding_conflicts": [],
        "contract_failures": [],
        "auxiliary_evidence_divergences": [],
        "consensus_receipts": consensus_receipts,
        "task_calls": [
            {"token_usage": {"total_tokens": 1}} for _ in range(12)
        ],
    })
    state_receipts = {}
    for role in STATE_ROLES:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            binding = consensus_receipts[case_id]
            state_receipts[f"{role}:{case_id}"] = {
                "relation_assessments": [{
                    "relation_id": relation["relation_id"],
                    "relation_truth_state": expected_states(corpus)[
                        case_id
                    ][relation["relation_id"]],
                } for relation in binding["relation_bindings"]],
            }
    state_run = _run({
        "raw_receipts": state_receipts,
        "contract_failures": [],
        "task_calls": [
            {"token_usage": {"total_tokens": 1}} for _ in range(12)
        ],
    })
    analysis = analyze_typed_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=state_run,
    )
    assert analysis["decision"] == (
        "PASS_TYPED_EVIDENCE_BINDING_CALIBRATION"
    )
    assert analysis["core_contract_sync_eligible"] is True

    damaged = copy.deepcopy(state_run)
    target = damaged["raw_receipts"][
        "STATE_ASSESSOR:PC-TRAFFIC"
    ]["relation_assessments"][1]
    target["relation_truth_state"] = "UNRESOLVED"
    damaged = _run({
        key: value
        for key, value in damaged.items()
        if key != "run_hash"
    })
    rejected = analyze_typed_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=damaged,
    )
    assert rejected["decision"] == (
        "REJECT_TYPED_EVIDENCE_BINDING_CALIBRATION"
    )
