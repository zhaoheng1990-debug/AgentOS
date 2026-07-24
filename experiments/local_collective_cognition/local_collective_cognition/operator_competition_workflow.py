"""Build v0.9 state only from completed, hash-bound experiment artifacts."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .fingerprint_history import build_historical_fingerprint_credit
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .holdout_v6_benchmark import (
    HOLDOUT_V6_ITEM_DOMAINS,
    HOLDOUT_V6_ITEM_FINGERPRINTS,
    build_holdout_v6_harness,
)
from .holdout_v7_benchmark import HOLDOUT_V7_ITEM_DOMAINS, HOLDOUT_V7_ITEM_FINGERPRINTS
from .routing_calibration import CalibratedModelProfile
from .structural_operator_credit import build_structural_operator_credit
from .structural_operator_policy import build_second_ranked_model_map, build_structural_operator_schedule
from .task_fingerprints import FINGERPRINT_TO_DOMAIN


def build_operator_competition_state(
    *,
    base_profiles: dict[str, CalibratedModelProfile],
    calibration_cache: Path,
    pre_v08_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
    v08_report_path: Path,
) -> dict[str, Any]:
    source_profiles, source_snapshot, _ = build_historical_fingerprint_credit(
        base_profiles=base_profiles, calibration_cache=calibration_cache, report_sources=pre_v08_sources,
    )
    v08_report = json.loads(v08_report_path.read_text(encoding="utf-8"))
    second_models = build_second_ranked_model_map(
        profiles=source_profiles,
        item_domains=HOLDOUT_V6_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V6_ITEM_FINGERPRINTS,
    )
    operator_evidence = build_holdout_v6_harness().calibrate_routing(
        experiment_id=v08_report["experiment_id"] + "-structural-operators",
        source_report_hash=sha256(v08_report_path.read_bytes()).hexdigest(),
        source_profile_hash=source_snapshot["snapshot_hash"],
        route_decisions=tuple(v08_report["route_decisions"]),
        second_model_by_item=second_models,
        majority_answer_vector=v08_report["majority_arm"]["answer_vector"],
        solo_answer_vectors={item["model_ids"][0]: item["answer_vector"] for item in v08_report["solo_arms"]},
        item_fingerprints=HOLDOUT_V6_ITEM_FINGERPRINTS,
    )
    operator_credit = build_structural_operator_credit(
        receipt=operator_evidence, fingerprint_domains=FINGERPRINT_TO_DOMAIN,
    )
    profiles, fingerprint_snapshot, history = build_historical_fingerprint_credit(
        base_profiles=base_profiles,
        calibration_cache=calibration_cache,
        report_sources=(*pre_v08_sources, (v08_report_path, build_holdout_v6_harness())),
    )
    schedule = build_structural_operator_schedule(
        profiles=profiles, operator_credit=operator_credit,
        item_domains=HOLDOUT_V7_ITEM_DOMAINS,
        item_fingerprints=HOLDOUT_V7_ITEM_FINGERPRINTS,
        budget=4,
    )
    return {
        "profiles": profiles,
        "fingerprint_credit_snapshot": fingerprint_snapshot,
        "fingerprint_credit_history": history,
        "operator_evidence_receipt": operator_evidence,
        "operator_credit_snapshot": operator_credit,
        "operator_schedule": schedule,
    }
