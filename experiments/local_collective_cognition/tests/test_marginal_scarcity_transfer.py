from __future__ import annotations

import copy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.marginal_scarcity_contract import (  # noqa: E402
    DISCOVERY_ROLES,
)
from local_collective_cognition.marginal_scarcity_transfer import (  # noqa: E402
    analyze_transfer_discovery,
    analyze_transfer_replacement,
    build_transfer_preregistration,
    run_transfer_replacement,
)
from local_collective_cognition.marginal_scarcity_transfer_holdout import (  # noqa: E402
    build_marginal_scarcity_transfer_holdout,
)
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402


def _artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


def _sources(corpus):
    reference = _artifact({
        "source_corpus_hash": corpus["artifact_hash"],
        "reference_complete": True,
    })
    closure = _artifact({
        "decision": "PASS_MARGINAL_SCARCITY_REPLACEMENT",
        "promotion_allowed": False,
    })
    return reference, closure


def _perfect_run(corpus, preregistration):
    bindings = corpus["private_provenance"]["bindings"]
    consensus = {}
    receipts = {}
    calls = []
    for rep in corpus["replication_ids"]:
        for item in corpus["public_surface"]["items"]:
            case_id = item["case_id"]
            binding = bindings[case_id]
            target = binding["designed_target_relation"]
            consensus[f"{rep}:{case_id}"] = {
                "agreed": True,
                "source_object_id": target["source_object_id"],
                "target_object_id": target["target_object_id"],
                "proposed_drop_pool_id": binding["designed_drop_pool_id"],
            }
            for role in DISCOVERY_ROLES:
                receipts[f"{rep}:{case_id}:{role}"] = {"valid": True}
                calls.append({
                    "replication_id": rep,
                    "case_id": case_id,
                    "role": role,
                    "token_usage": {"total_tokens": 1},
                })
    commitment = {
        "runtime_version": "marginal_scarcity_transfer_v0_59",
        "source_corpus_hash": corpus["artifact_hash"],
        "source_preregistration_hash": preregistration["artifact_hash"],
        "task_calls": calls,
        "receipts": receipts,
        "consensus_candidates": consensus,
    }
    return {**commitment, "run_hash": hash_payload(commitment)}


def _setup():
    corpus = build_marginal_scarcity_transfer_holdout()
    reference, closure = _sources(corpus)
    preregistration = build_transfer_preregistration(
        corpus=corpus,
        reference_audit=reference,
        source_replacement_closure=closure,
    )
    return corpus, preregistration


def test_transfer_discovery_requires_position_generalization():
    corpus, preregistration = _setup()
    run = _perfect_run(corpus, preregistration)
    analysis = analyze_transfer_discovery(
        corpus=corpus,
        preregistration=preregistration,
        run=run,
    )
    assert analysis["decision"] == (
        "PASS_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
    )
    assert analysis["target_source_position_coverage"] == 5
    assert analysis["drop_pool_coverage"] == 3
    assert analysis["wrong_target_consensus_count"] == 0

    damaged = copy.deepcopy(run)
    for key in damaged["consensus_candidates"]:
        if key.endswith(":MT-DRONE"):
            damaged["consensus_candidates"][key]["source_object_id"] = "O2"
    commitment = {
        key: value for key, value in damaged.items() if key != "run_hash"
    }
    damaged["run_hash"] = hash_payload(commitment)
    rejected = analyze_transfer_discovery(
        corpus=corpus,
        preregistration=preregistration,
        run=damaged,
    )
    assert rejected["decision"] == (
        "REJECT_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
    )
    assert rejected["target_source_position_coverage"] == 4
    assert rejected["wrong_target_consensus_count"] == 3


def test_transfer_replacement_blocks_wrong_drop_and_preserves_gain():
    corpus, preregistration = _setup()
    discovery_run = _perfect_run(corpus, preregistration)
    key = next(
        value for value in discovery_run["consensus_candidates"]
        if value.endswith(":MT-ORBIT")
    )
    discovery_run["consensus_candidates"][key][
        "proposed_drop_pool_id"
    ] = "BASE:C2"
    commitment = {
        name: value
        for name, value in discovery_run.items()
        if name != "run_hash"
    }
    discovery_run["run_hash"] = hash_payload(commitment)
    discovery_analysis = analyze_transfer_discovery(
        corpus=corpus,
        preregistration=preregistration,
        run=discovery_run,
    )
    assert discovery_analysis["decision"] == (
        "PASS_MARGINAL_SCARCITY_TRANSFER_DISCOVERY"
    )
    replacement_run = run_transfer_replacement(
        corpus=corpus,
        preregistration=preregistration,
        discovery_run=discovery_run,
        discovery_analysis=discovery_analysis,
    )
    assert replacement_run["decisions"][key]["state"] == "BLOCK_WRONG_DROP"
    replacement_analysis = analyze_transfer_replacement(
        corpus=corpus,
        preregistration=preregistration,
        run=replacement_run,
    )
    assert replacement_analysis["decision"] == (
        "PASS_MARGINAL_SCARCITY_TRANSFER_REPLACEMENT"
    )
    assert replacement_analysis["replacement_count"] == 17
    assert replacement_analysis["realized_gross_cbit_mean"] == 2.0
    assert replacement_analysis["protected_knowledge_loss_count"] == 0
