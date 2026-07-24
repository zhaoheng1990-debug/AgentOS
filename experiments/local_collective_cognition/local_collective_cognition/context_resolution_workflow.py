"""Build v0.12 context-resolution state from three promoted disagreement cycles."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .calibrated_resolution_workflow import build_resolution_receipt_from_report
from .context_resolution_lifecycle import ContextResolutionLifecycle
from .context_resolution_policy import build_context_exploration_schedule
from .fingerprint_history import build_historical_fingerprint_credit
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .holdout_v6_benchmark import build_holdout_v6_harness
from .holdout_v7_benchmark import HOLDOUT_V7_ITEM_FINGERPRINTS, build_holdout_v7_harness
from .holdout_v8_benchmark import HOLDOUT_V8_ITEM_FINGERPRINTS, build_holdout_v8_harness
from .holdout_v9_benchmark import HOLDOUT_V9_ITEM_FINGERPRINTS, build_holdout_v9_harness
from .holdout_v10_benchmark import HOLDOUT_V10_ITEM_DOMAINS, HOLDOUT_V10_ITEM_FINGERPRINTS
from .multi_cycle_resolution import MultiCycleResolutionLifecycle
from .operator_competition_workflow import build_operator_competition_state
from .routing_calibration import CalibratedModelProfile
from .structural_operator_policy import build_structural_operator_schedule


_CYCLES = (
    ("v09", build_holdout_v7_harness, HOLDOUT_V7_ITEM_FINGERPRINTS,
     ("structural_operator_credit", "snapshot_hash"), ("PEER_VERIFICATION_RESOLVED",)),
    ("v10", build_holdout_v8_harness, HOLDOUT_V8_ITEM_FINGERPRINTS,
     ("disagreement_resolution_credit", "snapshot_hash"),
     ("PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED")),
    ("v11", build_holdout_v9_harness, HOLDOUT_V9_ITEM_FINGERPRINTS,
     ("disagreement_resolution_credit", "snapshot_hash"),
     ("PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED")),
)


def build_context_resolution_state(
    *, base_profiles: dict[str, CalibratedModelProfile], calibration_cache: Path,
    pre_v08_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
    v08_report_path: Path, v09_report_path: Path, v10_report_path: Path, v11_report_path: Path,
) -> dict[str, Any]:
    operator_state = build_operator_competition_state(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        pre_v08_sources=pre_v08_sources, v08_report_path=v08_report_path,
    )
    paths = {"v09": v09_report_path, "v10": v10_report_path, "v11": v11_report_path}
    resolution_lifecycle = MultiCycleResolutionLifecycle()
    context_lifecycle = ContextResolutionLifecycle()
    resolution_receipts, resolution_candidates, resolution_promotions = [], [], []
    context_receipts, context_candidates, context_promotions = [], [], []
    for cycle, harness_builder, fingerprints, credit_key, actions in _CYCLES:
        path = paths[cycle]
        resolution = build_resolution_receipt_from_report(
            report_path=path, harness=harness_builder(), item_fingerprints=fingerprints,
            source_credit_hash_key=credit_key, source_actions=actions,
        )
        resolution_receipts.append(resolution)
        candidate = resolution_lifecycle.ingest_candidate(resolution)
        resolution_candidates.append(candidate)
        resolution_promotions.append(resolution_lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=resolution.source_report_hash,
        ))
        context = build_context_receipt_from_report(
            report_path=path, harness=harness_builder(), item_fingerprints=fingerprints,
            source_credit_hash_key=credit_key, source_actions=actions,
        )
        context_receipts.append(context)
        candidate = context_lifecycle.ingest_candidate(context)
        context_candidates.append(candidate)
        context_promotions.append(context_lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=context.source_report_hash,
        ))
    resolution_credit = resolution_lifecycle.snapshot()
    context_credit = context_lifecycle.snapshot()

    profiles, fingerprint_snapshot, history = build_historical_fingerprint_credit(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        report_sources=(*pre_v08_sources, (v08_report_path, build_holdout_v6_harness()),
                        (v09_report_path, build_holdout_v7_harness()),
                        (v10_report_path, build_holdout_v8_harness()),
                        (v11_report_path, build_holdout_v9_harness())),
    )
    acquisition = build_structural_operator_schedule(
        profiles=profiles, operator_credit=operator_state["operator_credit_snapshot"],
        item_domains=HOLDOUT_V10_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
        budget=4,
    )
    exploration = build_context_exploration_schedule(
        context_credit=context_credit, profiles=profiles,
        item_domains=HOLDOUT_V10_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V10_ITEM_FINGERPRINTS,
        existing_schedule=acquisition, budget=2,
    )
    return {
        "profiles": profiles, "fingerprint_credit_snapshot": fingerprint_snapshot,
        "fingerprint_credit_history": history,
        "operator_evidence_receipt": operator_state["operator_evidence_receipt"],
        "operator_credit_snapshot": operator_state["operator_credit_snapshot"],
        "operator_schedule": {**acquisition, **exploration},
        "acquisition_schedule": acquisition, "resolution_exploration_schedule": exploration,
        "resolution_evidence_receipts": tuple(resolution_receipts),
        "resolution_candidates": tuple(resolution_candidates),
        "resolution_promotions": tuple(resolution_promotions),
        "resolution_credit_snapshot": resolution_credit,
        "context_evidence_receipts": tuple(context_receipts),
        "context_candidates": tuple(context_candidates),
        "context_promotions": tuple(context_promotions),
        "context_credit_snapshot": context_credit,
    }


def build_context_receipt_from_report(
    *, report_path: Path, harness: FrozenAnswerBenchmarkHarness,
    item_fingerprints: dict[str, str], source_credit_hash_key: tuple[str, str],
    source_actions: tuple[str, ...],
):
    report = json.loads(report_path.read_text(encoding="utf-8"))
    solo = {item["model_ids"][0]: item["answer_vector"] for item in report["solo_arms"]}
    return harness.calibrate_routing(
        experiment_id=report["experiment_id"] + "-context-evidence",
        source_report_hash=sha256(report_path.read_bytes()).hexdigest(),
        source_credit_hash=report[source_credit_hash_key[0]][source_credit_hash_key[1]],
        route_decisions=tuple(report["route_decisions"]), solo_answer_vectors=solo,
        item_fingerprints=item_fingerprints, context_source_actions=source_actions,
    )
