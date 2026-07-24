"""Build v0.11 state from promoted v0.9 and v0.10 resolution evidence."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .fingerprint_history import build_historical_fingerprint_credit
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .holdout_v6_benchmark import build_holdout_v6_harness
from .holdout_v7_benchmark import HOLDOUT_V7_ITEM_FINGERPRINTS, build_holdout_v7_harness
from .holdout_v8_benchmark import HOLDOUT_V8_ITEM_FINGERPRINTS, build_holdout_v8_harness
from .holdout_v9_benchmark import HOLDOUT_V9_ITEM_DOMAINS, HOLDOUT_V9_ITEM_FINGERPRINTS
from .multi_cycle_resolution import MultiCycleResolutionLifecycle
from .operator_competition_workflow import build_operator_competition_state
from .resolution_exploration_policy import build_resolution_exploration_schedule
from .routing_calibration import CalibratedModelProfile
from .structural_operator_policy import build_structural_operator_schedule


def build_calibrated_resolution_state(
    *,
    base_profiles: dict[str, CalibratedModelProfile],
    calibration_cache: Path,
    pre_v08_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
    v08_report_path: Path,
    v09_report_path: Path,
    v10_report_path: Path,
) -> dict[str, Any]:
    operator_state = build_operator_competition_state(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        pre_v08_sources=pre_v08_sources, v08_report_path=v08_report_path,
    )
    v09_receipt = build_resolution_receipt_from_report(
        report_path=v09_report_path, harness=build_holdout_v7_harness(),
        item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
        source_credit_hash_key=("structural_operator_credit", "snapshot_hash"),
        source_actions=("PEER_VERIFICATION_RESOLVED",),
    )
    v10_receipt = build_resolution_receipt_from_report(
        report_path=v10_report_path, harness=build_holdout_v8_harness(),
        item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS,
        source_credit_hash_key=("disagreement_resolution_credit", "snapshot_hash"),
        source_actions=("PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED"),
    )
    lifecycle = MultiCycleResolutionLifecycle()
    candidates = []
    promotions = []
    for receipt in (v09_receipt, v10_receipt):
        candidate = lifecycle.ingest_candidate(receipt)
        candidates.append(candidate)
        promotions.append(lifecycle.promote(
            candidate_hash=candidate.candidate_hash,
            validation_ref=receipt.source_report_hash,
        ))
    resolution_credit = lifecycle.snapshot()

    profiles, fingerprint_snapshot, history = build_historical_fingerprint_credit(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        report_sources=(
            *pre_v08_sources,
            (v08_report_path, build_holdout_v6_harness()),
            (v09_report_path, build_holdout_v7_harness()),
            (v10_report_path, build_holdout_v8_harness()),
        ),
    )
    acquisition_schedule = build_structural_operator_schedule(
        profiles=profiles, operator_credit=operator_state["operator_credit_snapshot"],
        item_domains=HOLDOUT_V9_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V9_ITEM_FINGERPRINTS, budget=4,
    )
    exploration_schedule = build_resolution_exploration_schedule(
        resolution_credit=resolution_credit,
        item_fingerprints=HOLDOUT_V9_ITEM_FINGERPRINTS,
        existing_schedule=acquisition_schedule, budget=2,
    )
    return {
        "profiles": profiles,
        "fingerprint_credit_snapshot": fingerprint_snapshot,
        "fingerprint_credit_history": history,
        "operator_evidence_receipt": operator_state["operator_evidence_receipt"],
        "operator_credit_snapshot": operator_state["operator_credit_snapshot"],
        "operator_schedule": {**acquisition_schedule, **exploration_schedule},
        "acquisition_schedule": acquisition_schedule,
        "resolution_exploration_schedule": exploration_schedule,
        "resolution_evidence_receipts": (v09_receipt, v10_receipt),
        "resolution_candidates": tuple(candidates),
        "resolution_promotions": tuple(promotions),
        "resolution_credit_snapshot": resolution_credit,
    }


def build_resolution_receipt_from_report(
    *, report_path, harness, item_fingerprints, source_credit_hash_key, source_actions,
):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    source_hash = sha256(report_path.read_bytes()).hexdigest()
    peer_answers = _peer_answers(report, source_actions)
    return harness.calibrate_routing(
        experiment_id=report["experiment_id"] + "-multi-cycle-resolution-evidence",
        source_report_hash=source_hash,
        source_operator_credit_hash=report[source_credit_hash_key[0]][source_credit_hash_key[1]],
        route_decisions=tuple(report["route_decisions"]),
        resolver_peer_answer_by_item=peer_answers,
        item_fingerprints=item_fingerprints,
        source_actions=source_actions,
    )


def _peer_answers(report: dict[str, Any], source_actions: tuple[str, ...]) -> dict[str, str]:
    solo_answers = {
        item["model_ids"][0]: item["answer_vector"]
        for item in report["solo_arms"] if len(item["model_ids"]) == 1
    }
    answers = {
        item["item_id"]: solo_answers[item["reviewer_model_id"]][item["item_id"]]
        for item in report["route_decisions"] if item.get("action") in source_actions
    }
    if not answers:
        raise ValueError("multi_cycle_resolution_source_routes_missing")
    return answers
