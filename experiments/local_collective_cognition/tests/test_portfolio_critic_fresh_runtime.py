from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.portfolio_critic_calibration import (  # noqa: E402
    build_portfolio_critic_receipts,
)
from local_collective_cognition.portfolio_critic_fresh_holdout import (  # noqa: E402
    build_portfolio_critic_fresh_holdout,
    validate_portfolio_critic_fresh_holdout,
)
from local_collective_cognition.portfolio_critic_fresh_runtime import (  # noqa: E402
    RUNTIME_VERSION,
    analyze_fresh_kernel_actions,
    build_fresh_preregistration,
    run_fresh_kernel_actions,
)
from local_collective_cognition.portfolio_target_discovery import (  # noqa: E402
    TARGET_ROLES,
    build_target_view,
    target_schema,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.reference_completeness_audit import (  # noqa: E402
    AUDIT_ROLES,
)


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _run_artifact(value):
    return {**value, "run_hash": hash_payload(value)}


def _reference(corpus):
    receipts = {}
    bindings = corpus["private_provenance"]["bindings"]
    for item in corpus["public_surface"]["items"]:
        case_id = item["case_id"]
        binding = bindings[case_id]
        supported = {
            value["source_object_id"]
            for value in binding["supported_targets"]
        }
        nulls = {
            value["source_object_id"]
            for value in binding["informative_null_targets"]
        }
        for role in AUDIT_ROLES:
            assessments = []
            for value in item["object_registry"]:
                source = value["object_id"]
                if source == "O1":
                    continue
                state = (
                    "SUPPORTED_EFFECT" if source in supported
                    else "SUPPORTED_NULL" if source in nulls
                    else "UNRESOLVED"
                )
                assessments.append({
                    "relation_id": f"REL-{source}-O1",
                    "relation_truth_state": state,
                    "evidence_span_ids": [f"S{int(source[1:]) - 1}"],
                    "rationale": f"{role}:{case_id}:{source}",
                })
            receipts[f"{role}:{case_id}"] = {
                "case_id": case_id,
                "relation_assessments": assessments,
            }
    return _artifact({
        "source_corpus_hash": corpus["artifact_hash"],
        "reference_complete": True,
        "raw_receipts": receipts,
    })


def _target_run(corpus):
    consensus = {}
    bindings = corpus["private_provenance"]["bindings"]
    for rep in corpus["replication_ids"]:
        for item in corpus["public_surface"]["items"]:
            target = bindings[item["case_id"]]["designed_target_relation"]
            consensus[f"{rep}:{item['case_id']}"] = {
                "agreed": True,
                "source_object_id": target["source_object_id"],
                "target_object_id": target["target_object_id"],
            }
    return _run_artifact({"consensus_candidates": consensus})


def test_target_schema_forbids_drop_selection():
    corpus = build_portfolio_critic_fresh_holdout()
    item = corpus["public_surface"]["items"][0]
    view = build_target_view(
        item=item, corpus_hash=corpus["artifact_hash"]
    )
    schema = target_schema(
        view=view,
        role=TARGET_ROLES[0],
        refs=corpus["evidence_refs"],
    )
    assert "proposed_drop_pool_id" not in schema["properties"]
    assert schema["additionalProperties"] is False
    assert view["drop_selection_requested"] is False


def test_fresh_kernel_selects_only_unique_topology():
    corpus = build_portfolio_critic_fresh_holdout()
    reference = _reference(corpus)
    source_closure = _artifact({
        "decision": "PASS_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION",
        "fresh_holdout_required": True,
        "promotion_allowed": False,
    })
    preregistration = build_fresh_preregistration(
        corpus=corpus,
        reference_audit=reference,
        source_calibration_closure=source_closure,
    )
    target_run = _target_run(corpus)
    target_analysis = _artifact({
        "source_run_hash": target_run["run_hash"],
        "decision": "PASS_FRESH_TARGET_ONLY_DISCOVERY",
    })
    critic = build_portfolio_critic_receipts(
        corpus=corpus,
        reference_audit=reference,
        preregistration=preregistration,
        corpus_validator=validate_portfolio_critic_fresh_holdout,
        runtime_version=RUNTIME_VERSION,
    )
    run = run_fresh_kernel_actions(
        corpus=corpus,
        preregistration=preregistration,
        target_run=target_run,
        target_analysis=target_analysis,
        critic_artifact=critic,
    )
    analysis = analyze_fresh_kernel_actions(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert analysis["decision"] == (
        "PASS_FRESH_PORTFOLIO_CRITIC_SELECTIVITY"
    )
    assert analysis["unique_replacement_count"] == 6
    assert analysis["no_eligible_abstention_count"] == 6
    assert analysis["ambiguous_abstention_count"] == 6
    assert analysis["harmful_replacement_count"] == 0
    assert analysis["protected_knowledge_loss_count"] == 0
