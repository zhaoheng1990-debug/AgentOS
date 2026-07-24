"""Build v0.10 disagreement-resolution state from frozen prior artifacts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .disagreement_resolution_lifecycle import DisagreementResolutionLifecycle
from .fingerprint_history import build_historical_fingerprint_credit
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .holdout_v6_benchmark import build_holdout_v6_harness
from .holdout_v7_benchmark import HOLDOUT_V7_ITEM_FINGERPRINTS, build_holdout_v7_harness
from .holdout_v8_benchmark import HOLDOUT_V8_ITEM_DOMAINS, HOLDOUT_V8_ITEM_FINGERPRINTS
from .operator_competition_workflow import build_operator_competition_state
from .routing_calibration import CalibratedModelProfile
from .structural_operator_policy import build_structural_operator_schedule


def build_resolution_lifecycle_state(
    *,
    base_profiles: dict[str, CalibratedModelProfile],
    calibration_cache: Path,
    pre_v08_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
    v08_report_path: Path,
    v09_report_path: Path,
) -> dict[str, Any]:
    operator_state = build_operator_competition_state(
        base_profiles=base_profiles,
        calibration_cache=calibration_cache,
        pre_v08_sources=pre_v08_sources,
        v08_report_path=v08_report_path,
    )
    v09_report = json.loads(v09_report_path.read_text(encoding="utf-8"))
    source_report_hash = sha256(v09_report_path.read_bytes()).hexdigest()
    source_credit_hash = v09_report["structural_operator_credit"]["snapshot_hash"]
    if source_credit_hash != operator_state["operator_credit_snapshot"].snapshot_hash:
        raise ValueError("resolution_source_operator_credit_mismatch")

    peer_answers = _peer_answers_for_paid_routes(v09_report)
    evidence = build_holdout_v7_harness().calibrate_routing(
        experiment_id=v09_report["experiment_id"] + "-resolution-evidence",
        source_report_hash=source_report_hash,
        source_operator_credit_hash=source_credit_hash,
        route_decisions=tuple(v09_report["route_decisions"]),
        resolver_peer_answer_by_item=peer_answers,
        item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
    )
    lifecycle = DisagreementResolutionLifecycle(receipt=evidence)
    candidate = lifecycle.ingest_candidate()
    promotion = lifecycle.promote(
        candidate_hash=candidate.candidate_hash,
        validation_ref=source_report_hash,
    )
    resolution_credit = lifecycle.snapshot()

    profiles, fingerprint_snapshot, history = build_historical_fingerprint_credit(
        base_profiles=base_profiles,
        calibration_cache=calibration_cache,
        report_sources=(
            *pre_v08_sources,
            (v08_report_path, build_holdout_v6_harness()),
            (v09_report_path, build_holdout_v7_harness()),
        ),
    )
    schedule = build_structural_operator_schedule(
        profiles=profiles,
        operator_credit=operator_state["operator_credit_snapshot"],
        item_domains=HOLDOUT_V8_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V8_ITEM_FINGERPRINTS,
        budget=4,
    )
    return {
        "profiles": profiles,
        "fingerprint_credit_snapshot": fingerprint_snapshot,
        "fingerprint_credit_history": history,
        "operator_evidence_receipt": operator_state["operator_evidence_receipt"],
        "operator_credit_snapshot": operator_state["operator_credit_snapshot"],
        "operator_schedule": schedule,
        "resolution_evidence_receipt": evidence,
        "resolution_candidate": candidate,
        "resolution_promotion": promotion,
        "resolution_credit_snapshot": resolution_credit,
    }


def _peer_answers_for_paid_routes(report: dict[str, Any]) -> dict[str, str]:
    solo_answers = {
        item["model_ids"][0]: item["answer_vector"]
        for item in report["solo_arms"] if len(item["model_ids"]) == 1
    }
    paid = {
        item["item_id"]: solo_answers[item["reviewer_model_id"]][item["item_id"]]
        for item in report["route_decisions"]
        if item.get("action") == "PEER_VERIFICATION_RESOLVED"
    }
    if not paid:
        raise ValueError("resolution_source_paid_routes_missing")
    return paid
