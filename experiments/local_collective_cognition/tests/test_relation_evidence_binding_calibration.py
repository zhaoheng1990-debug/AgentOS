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
from local_collective_cognition.relation_evidence_binding_calibration import (  # noqa: E402
    BINDING_ROLES,
    STATE_ROLES,
    analyze_state_panel,
    binding_schema,
    build_binding_preregistration,
)


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _run(value):
    return {**value, "run_hash": hash_payload(value)}


def _setup():
    corpus = build_portfolio_critic_fresh_holdout_v0_61_1()
    failed_reference = _artifact({
        "reference_complete": False,
        "reference_mismatches": [{}, {}],
    })
    closure = _artifact({
        "decision": "REJECT_FRESH_PORTFOLIO_REFERENCE_GATE",
        "object_evidence_binding_calibration_required": True,
    })
    preregistration = build_binding_preregistration(
        corpus=corpus,
        failed_reference=failed_reference,
        source_closure=closure,
    )
    return corpus, preregistration


def _expected(corpus, case_id):
    binding = corpus["private_provenance"]["bindings"][case_id]
    supported = {
        value["source_object_id"]
        for value in binding["supported_targets"]
    }
    nulls = {
        value["source_object_id"]
        for value in binding["informative_null_targets"]
    }
    return {
        f"REL-{source}-O1": (
            "SUPPORTED_EFFECT" if source in supported
            else "SUPPORTED_NULL" if source in nulls
            else "UNRESOLVED"
        )
        for source in ("O2", "O3", "O4", "O5", "O6")
    }


def _perfect_runs(corpus):
    binding_run = _run({
        "raw_receipts": {
            f"{role}:{item['case_id']}": {"valid": True}
            for role in BINDING_ROLES
            for item in corpus["public_surface"]["items"]
        },
        "binding_relation_consensus_count": 30,
        "binding_conflicts": [],
        "task_calls": [
            {"token_usage": {"total_tokens": 1}}
            for _ in range(12)
        ],
    })
    state_receipts = {}
    for role in STATE_ROLES:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            state_receipts[f"{role}:{case_id}"] = {
                "relation_assessments": [
                    {
                        "relation_id": relation_id,
                        "relation_truth_state": state,
                    }
                    for relation_id, state in _expected(
                        corpus, case_id
                    ).items()
                ],
            }
    state_run = _run({
        "raw_receipts": state_receipts,
        "contract_failures": [],
        "task_calls": [
            {"token_usage": {"total_tokens": 1}}
            for _ in range(12)
        ],
    })
    return binding_run, state_run


def test_binding_schema_cannot_emit_truth_state():
    corpus, _preregistration = _setup()
    item = corpus["public_surface"]["items"][0]
    schema = binding_schema(
        item=item,
        role=BINDING_ROLES[0],
        refs=corpus["evidence_refs"],
    )
    relation = schema["properties"]["relation_bindings"]["items"]
    assert "relation_truth_state" not in relation["properties"]
    assert relation["additionalProperties"] is False


def test_conditioned_state_panel_recovers_failed_coordinate():
    corpus, preregistration = _setup()
    binding_run, state_run = _perfect_runs(corpus)
    analysis = analyze_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=state_run,
    )
    assert analysis["decision"] == (
        "PASS_RELATION_EVIDENCE_BINDING_CALIBRATION"
    )
    assert analysis["required_coordinate_recovered"] is True
    assert analysis["state_reference_mismatches"] == []

    damaged = copy.deepcopy(state_run)
    for role in STATE_ROLES:
        receipt = damaged["raw_receipts"][f"{role}:PC-TRAFFIC"]
        target = next(
            value for value in receipt["relation_assessments"]
            if value["relation_id"] == "REL-O3-O1"
        )
        target["relation_truth_state"] = "UNRESOLVED"
    commitment = {
        key: value for key, value in damaged.items() if key != "run_hash"
    }
    damaged["run_hash"] = hash_payload(commitment)
    rejected = analyze_state_panel(
        corpus=corpus,
        preregistration=preregistration,
        binding_run=binding_run,
        state_run=damaged,
    )
    assert rejected["decision"] == (
        "REJECT_RELATION_EVIDENCE_BINDING_CALIBRATION"
    )
    assert rejected["required_coordinate_recovered"] is False
