from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    build_marginal_scarcity_transfer_holdout_v0_59_1,
)
from local_collective_cognition.portfolio_critic_calibration import (  # noqa: E402
    analyze_kernel_displacement,
    build_portfolio_critic_preregistration,
    build_portfolio_critic_receipts,
    run_kernel_displacement,
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
    bindings = corpus["private_provenance"]["bindings"]
    receipts = {}
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


def _discovery_sources(corpus):
    bindings = corpus["private_provenance"]["bindings"]
    consensus = {}
    nonconsensus = {
        "R1:MT-DRONE",
        "R1:MT-PATH",
        "R2:MT-DRONE",
        "R3:MT-ORBIT",
    }
    wrong_drop = {
        "R1:MT-CROP",
        "R2:MT-CROP",
        "R3:MT-CROP",
        "R2:MT-PATH",
        "R3:MT-PATH",
        "R2:MT-TELESCOPE",
    }
    for rep in corpus["replication_ids"]:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            key = f"{rep}:{case_id}"
            if key in nonconsensus:
                consensus[key] = {
                    "agreed": False,
                    "source_object_id": None,
                    "target_object_id": None,
                    "proposed_drop_pool_id": None,
                }
                continue
            binding = bindings[case_id]
            target = binding["designed_target_relation"]
            advisory = binding["designed_drop_pool_id"]
            if key in wrong_drop:
                advisory = next(
                    value["pool_candidate_id"]
                    for value in item["frozen_active_portfolio"]
                    if value["pool_candidate_id"] != advisory
                )
            consensus[key] = {
                "agreed": True,
                "source_object_id": target["source_object_id"],
                "target_object_id": target["target_object_id"],
                "proposed_drop_pool_id": advisory,
            }
    run = _run_artifact({
        "consensus_candidates": consensus,
    })
    analysis = _artifact({
        "decision": "REJECT_MARGINAL_SCARCITY_TRANSFER_DISCOVERY",
        "wrong_target_consensus_count": 0,
        "consensus_count": 14,
    })
    closure = _artifact({
        "target_discovery_transfer_supported": True,
        "displacement_selection_transfer_supported": False,
    })
    return run, analysis, closure


def _setup(reference=None):
    corpus = build_marginal_scarcity_transfer_holdout_v0_59_1()
    reference = reference or _reference(corpus)
    run, analysis, closure = _discovery_sources(corpus)
    preregistration = build_portfolio_critic_preregistration(
        corpus=corpus,
        reference_audit=reference,
        discovery_run=run,
        discovery_analysis=analysis,
        discovery_closure=closure,
    )
    return corpus, reference, run, preregistration


def test_critic_separates_target_discovery_from_kernel_drop():
    corpus, reference, discovery_run, preregistration = _setup()
    critic = build_portfolio_critic_receipts(
        corpus=corpus,
        reference_audit=reference,
        preregistration=preregistration,
    )
    run = run_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        discovery_run=discovery_run,
        critic_artifact=critic,
    )
    analysis = analyze_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert analysis["decision"] == (
        "PASS_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION"
    )
    assert analysis["replacement_count"] == 14
    assert analysis["corrective_override_count"] == 6
    assert analysis["drop_pool_coverage"] == 3
    assert analysis["harmful_replacement_count"] == 0
    assert analysis["protected_knowledge_loss_count"] == 0


def test_critic_conflict_blocks_kernel_displacement():
    corpus = build_marginal_scarcity_transfer_holdout_v0_59_1()
    reference = _reference(corpus)
    damaged = copy.deepcopy(reference)
    receipt = damaged["raw_receipts"][
        "REFERENCE_SKEPTIC:MT-CROP"
    ]
    target = next(
        value for value in receipt["relation_assessments"]
        if value["relation_id"] == "REL-O5-O1"
    )
    target["relation_truth_state"] = "SUPPORTED_EFFECT"
    commitment = {
        key: value for key, value in damaged.items()
        if key != "artifact_hash"
    }
    damaged["artifact_hash"] = hash_payload(commitment)
    corpus, reference, discovery_run, preregistration = _setup(damaged)
    critic = build_portfolio_critic_receipts(
        corpus=corpus,
        reference_audit=reference,
        preregistration=preregistration,
    )
    assert critic["critic_receipts"]["MT-CROP"]["critic_state"] == (
        "BLOCK_AMBIGUOUS_OR_CONFLICTED"
    )
    run = run_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        discovery_run=discovery_run,
        critic_artifact=critic,
    )
    analysis = analyze_kernel_displacement(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert analysis["decision"] == (
        "REJECT_PORTFOLIO_CRITIC_MECHANISM_CALIBRATION"
    )
    assert analysis["critic_conflict_count"] == 3
