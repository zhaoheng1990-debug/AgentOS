"""Adapt completed local pilot artifacts into fingerprint-credit candidates."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .frozen_answer_harness import FrozenAnswerBenchmarkHarness
from .hierarchical_fingerprint_credit import HierarchicalFingerprintCreditLedger
from .routing_calibration import CalibratedModelProfile
from .task_fingerprints import build_item_fingerprints


def build_historical_fingerprint_credit(
    *,
    base_profiles: dict[str, CalibratedModelProfile],
    calibration_cache: Path,
    report_sources: tuple[tuple[Path, FrozenAnswerBenchmarkHarness], ...],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    ledger = HierarchicalFingerprintCreditLedger(base_profiles=base_profiles)
    history = []
    sources = ((calibration_cache, None), *report_sources)
    for sequence, (path, harness) in enumerate(sources, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        source_hash = sha256(path.read_bytes()).hexdigest()
        if harness is None:
            receipts = _receipts_from_calibration_cache(payload, source_hash)
            cycle_id = payload["receipt"]["calibration_id"]
        else:
            receipts = _receipts_from_pilot_report(payload, harness, source_hash)
            cycle_id = payload["experiment_id"]
        candidate = ledger.ingest_candidate(
            cycle_id=cycle_id,
            sequence=sequence,
            source_report_hash=source_hash,
            receipts=receipts,
        )
        promotion = ledger.promote(candidate_hash=candidate.candidate_hash, source_report_hash=source_hash)
        history.append({"source_path": str(path), "candidate": candidate.as_dict(), "promotion": promotion.as_dict()})
    profiles, snapshot = ledger.snapshot()
    return profiles, snapshot, {"cycles": history, "experiment_only": True, "core_baseline_authority": False}


def _receipts_from_calibration_cache(payload: dict[str, Any], source_hash: str):
    receipt_records = {item["model_id"]: item for item in payload["receipt"]["model_records"]}
    results = []
    for run in payload["runs"]:
        model_id = run["model_id"]
        answers = run["result"]["answers"]
        harness = _harness_for_calibration_payload(payload)
        fingerprints = build_item_fingerprints(tuple(item["item_id"] for item in answers))
        results.append(harness.calibrate_reliability(
            calibration_id=f"fingerprint-history-{source_hash[:12]}",
            model_id=model_id,
            candidate_output=run["result"],
            item_domains=fingerprints,
            source_harness_receipt_hash=receipt_records[model_id]["source_harness_receipt_hash"],
        ))
    return tuple(results)


def _harness_for_calibration_payload(payload: dict[str, Any]):
    from .holdout_benchmark import build_holdout_harness

    harness = build_holdout_harness()
    if payload["receipt"]["evidence_refs"] != list(harness.evidence_refs):
        raise ValueError("fingerprint_history_calibration_benchmark_invalid")
    return harness


def _receipts_from_pilot_report(
    payload: dict[str, Any],
    harness: FrozenAnswerBenchmarkHarness,
    source_hash: str,
):
    results = []
    for arm in payload["solo_arms"]:
        if len(arm["model_ids"]) != 1:
            raise ValueError("fingerprint_history_solo_arm_invalid")
        answers = arm["answer_vector"]
        candidate_output = {
            "answers": [{"item_id": item_id, "answer": answer} for item_id, answer in answers.items()],
            "evidence_refs": list(harness.evidence_refs),
        }
        results.append(harness.calibrate_reliability(
            calibration_id=f"fingerprint-history-{source_hash[:12]}",
            model_id=arm["model_ids"][0],
            candidate_output=candidate_output,
            item_domains=build_item_fingerprints(tuple(answers)),
            source_harness_receipt_hash=arm["harness_receipt_hash"],
        ))
    return tuple(results)
