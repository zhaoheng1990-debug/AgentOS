"""Build v0.14 state with v0.13 promoted as diagnostic context evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .calibrated_resolution_workflow import build_resolution_receipt_from_report
from .context_resolution_lifecycle import ContextResolutionLifecycle
from .context_resolution_policy import build_context_exploration_schedule
from .context_resolution_workflow import build_context_receipt_from_report
from .fingerprint_history import build_historical_fingerprint_credit
from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .holdout_v6_benchmark import build_holdout_v6_harness
from .holdout_v7_benchmark import build_holdout_v7_harness
from .holdout_v8_benchmark import build_holdout_v8_harness
from .holdout_v9_benchmark import build_holdout_v9_harness
from .holdout_v10_benchmark import build_holdout_v10_harness
from .holdout_v11_benchmark import HOLDOUT_V11_ITEM_FINGERPRINTS, build_holdout_v11_harness
from .holdout_v12_benchmark import HOLDOUT_V12_ITEM_DOMAINS, HOLDOUT_V12_ITEM_FINGERPRINTS
from .iterated_context_workflow import build_iterated_context_state
from .multi_cycle_resolution import MultiCycleResolutionLifecycle
from .routing_calibration import CalibratedModelProfile
from .structural_operator_policy import build_structural_operator_schedule


_ACTIONS = ("PEER_AGREEMENT_RESOLVED", "PEER_OVERRIDE_RESOLVED", "PRIMARY_KEEP_RESOLVED")


def build_case_adjudication_state(
    *, base_profiles: dict[str, CalibratedModelProfile], calibration_cache: Path,
    pre_v08_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
    v08_report_path: Path, v09_report_path: Path, v10_report_path: Path,
    v11_report_path: Path, v12_report_path: Path, v13_report_path: Path,
) -> dict[str, Any]:
    prior = build_iterated_context_state(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        pre_v08_sources=pre_v08_sources, v08_report_path=v08_report_path,
        v09_report_path=v09_report_path, v10_report_path=v10_report_path,
        v11_report_path=v11_report_path, v12_report_path=v12_report_path,
    )
    resolution = build_resolution_receipt_from_report(
        report_path=v13_report_path, harness=build_holdout_v11_harness(),
        item_fingerprints=HOLDOUT_V11_ITEM_FINGERPRINTS,
        source_credit_hash_key=("context_resolution_credit", "snapshot_hash"),
        source_actions=_ACTIONS,
    )
    context = build_context_receipt_from_report(
        report_path=v13_report_path, harness=build_holdout_v11_harness(),
        item_fingerprints=HOLDOUT_V11_ITEM_FINGERPRINTS,
        source_credit_hash_key=("context_resolution_credit", "snapshot_hash"),
        source_actions=_ACTIONS,
    )
    resolution_receipts = (*prior["resolution_evidence_receipts"], resolution)
    context_receipts = (*prior["context_evidence_receipts"], context)
    resolution_lifecycle = MultiCycleResolutionLifecycle()
    resolution_candidates, resolution_promotions = _promote_all(resolution_lifecycle, resolution_receipts)
    context_lifecycle = ContextResolutionLifecycle()
    context_candidates, context_promotions = _promote_all(context_lifecycle, context_receipts)
    profiles, fingerprint_snapshot, history = build_historical_fingerprint_credit(
        base_profiles=base_profiles, calibration_cache=calibration_cache,
        report_sources=(*pre_v08_sources,
                        (v08_report_path, build_holdout_v6_harness()),
                        (v09_report_path, build_holdout_v7_harness()),
                        (v10_report_path, build_holdout_v8_harness()),
                        (v11_report_path, build_holdout_v9_harness()),
                        (v12_report_path, build_holdout_v10_harness()),
                        (v13_report_path, build_holdout_v11_harness())),
    )
    context_credit = context_lifecycle.snapshot()
    acquisition = build_structural_operator_schedule(
        profiles=profiles, operator_credit=prior["operator_credit_snapshot"],
        item_domains=HOLDOUT_V12_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V12_ITEM_FINGERPRINTS,
        budget=4,
    )
    exploration = build_context_exploration_schedule(
        context_credit=context_credit, profiles=profiles,
        item_domains=HOLDOUT_V12_ITEM_DOMAINS, item_fingerprints=HOLDOUT_V12_ITEM_FINGERPRINTS,
        existing_schedule=acquisition, budget=2,
    )
    return {
        "profiles": profiles, "fingerprint_credit_snapshot": fingerprint_snapshot,
        "fingerprint_credit_history": history,
        "operator_evidence_receipt": prior["operator_evidence_receipt"],
        "operator_credit_snapshot": prior["operator_credit_snapshot"],
        "operator_schedule": {**acquisition, **exploration}, "acquisition_schedule": acquisition,
        "resolution_exploration_schedule": exploration,
        "resolution_evidence_receipts": resolution_receipts,
        "resolution_candidates": resolution_candidates, "resolution_promotions": resolution_promotions,
        "resolution_credit_snapshot": resolution_lifecycle.snapshot(),
        "context_evidence_receipts": context_receipts, "context_candidates": context_candidates,
        "context_promotions": context_promotions, "context_credit_snapshot": context_credit,
    }


def _promote_all(lifecycle, receipts):
    candidates, promotions = [], []
    for receipt in receipts:
        candidate = lifecycle.ingest_candidate(receipt)
        candidates.append(candidate)
        promotions.append(lifecycle.promote(
            candidate_hash=candidate.candidate_hash, validation_ref=receipt.source_report_hash,
        ))
    return tuple(candidates), tuple(promotions)
