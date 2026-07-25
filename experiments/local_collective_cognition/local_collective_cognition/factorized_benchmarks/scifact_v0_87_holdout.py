"""Deterministic SciFact development holdout and preregistration for v0.87."""

from __future__ import annotations

import hashlib
import io
import json
import tarfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from ..provider_telemetry import hash_payload
from .acquisition import verify_external_artifact
from .catalog import source_by_id
from .scifact import build_case

SOURCE_ID = "SCIFACT_RELEASE_LATEST_20210126"
HOLDOUT_VERSION = "scifact_semantic_warrant_holdout_v0_87"
SELECTION_VERSION = "sha256_stratified_scifact_dev_v0_87"
LABELS = ("SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO")
CASES_PER_LABEL = 6


def freeze_holdout(archive_path: Path) -> dict[str, Any]:
    source = source_by_id(SOURCE_ID)
    artifact_receipt = verify_external_artifact(archive_path, source)
    if not artifact_receipt["verified"]:
        raise ValueError("scifact_v0_87_source_verification_failed")
    claims, corpus = _read_archive(archive_path)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        groups[_claim_state(claim)].append(claim)
    selected = []
    for label in LABELS:
        ranked = sorted(groups[label], key=_selection_key)
        if len(ranked) < CASES_PER_LABEL:
            raise ValueError(f"scifact_v0_87_{label}_pool_too_small")
        selected.extend(ranked[:CASES_PER_LABEL])
    cases = []
    for claim in sorted(selected, key=lambda value: int(value["id"])):
        public, private = build_case(claim, corpus)
        cases.append({
            "public_case": public.to_dict(),
            "private_reference": private.to_dict(),
        })
    commitment = {
        "holdout_version": HOLDOUT_VERSION,
        "selection_version": SELECTION_VERSION,
        "source_id": SOURCE_ID,
        "source_revision": source.revision,
        "source_artifact_sha256": source.artifact_sha256,
        "source_split": "dev",
        "case_count": len(cases),
        "cases_per_label": CASES_PER_LABEL,
        "label_balance": dict(sorted(Counter(
            item["private_reference"]["expected_state"] for item in cases
        ).items())),
        "cases": cases,
        "provider_calls_before_freeze": 0,
        "external_acceptance_eligible": False,
        "private_reference_exposed_to_provider": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def public_holdout(panel: dict[str, Any]) -> dict[str, Any]:
    validate_holdout(panel)
    value = {
        "holdout_version": panel["holdout_version"],
        "selection_version": panel["selection_version"],
        "source_id": panel["source_id"],
        "source_revision": panel["source_revision"],
        "source_artifact_sha256": panel["source_artifact_sha256"],
        "source_split": panel["source_split"],
        "case_count": panel["case_count"],
        "cases": [item["public_case"] for item in panel["cases"]],
        "private_reference_exposed": False,
        "external_acceptance_eligible": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def build_preregistration(panel: dict[str, Any]) -> dict[str, Any]:
    validate_holdout(panel)
    public = public_holdout(panel)
    value = {
        "preregistration_version": "scifact_semantic_warrant_prereg_v0_87",
        "source_holdout_hash": panel["artifact_hash"],
        "source_public_holdout_hash": public["artifact_hash"],
        "case_count": panel["case_count"],
        "operational_gate": {
            "valid_receipts_min": panel["case_count"],
            "contract_failures_max": 0,
            "physical_attempts_max": panel["case_count"] * 2,
            "hard_total_token_ceiling": 80_000,
        },
        "semantic_gate": {
            "label_accuracy_min": 0.80,
            "macro_rationale_f1_min": 0.70,
            "joint_success_rate_min": 0.65,
            "harmful_compiled_candidates_max": 0,
            "abstention_rate_max": 0.25,
        },
        "selection_frozen_before_provider_calls": True,
        "score_axes_frozen_before_provider_calls": True,
        "same_version_retuning_allowed": False,
        "external_acceptance_allowed": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def validate_holdout(panel: dict[str, Any]) -> None:
    commitment = {
        key: value for key, value in panel.items() if key != "artifact_hash"
    }
    if panel.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("scifact_v0_87_holdout_hash_invalid")
    if panel.get("holdout_version") != HOLDOUT_VERSION:
        raise ValueError("scifact_v0_87_holdout_version_invalid")
    if panel.get("case_count") != len(panel.get("cases", [])):
        raise ValueError("scifact_v0_87_case_count_invalid")
    if panel.get("label_balance") != {
        label: CASES_PER_LABEL for label in sorted(LABELS)
    }:
        raise ValueError("scifact_v0_87_label_balance_invalid")
    if panel.get("provider_calls_before_freeze") != 0:
        raise ValueError("scifact_v0_87_prefreeze_provider_call_detected")


def validate_preregistration(
    preregistration: dict[str, Any],
    *,
    panel: dict[str, Any],
) -> None:
    commitment = {
        key: value
        for key, value in preregistration.items()
        if key != "artifact_hash"
    }
    if preregistration.get("artifact_hash") != hash_payload(commitment):
        raise ValueError("scifact_v0_87_preregistration_hash_invalid")
    if preregistration.get("source_holdout_hash") != panel["artifact_hash"]:
        raise ValueError("scifact_v0_87_preregistration_panel_mismatch")
    if preregistration.get("same_version_retuning_allowed") is not False:
        raise ValueError("scifact_v0_87_retuning_boundary_invalid")


def _read_archive(
    archive_path: Path,
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    with tarfile.open(archive_path, "r:gz") as archive:
        claims = _read_jsonl(archive, "data/claims_dev.jsonl")
        corpus_rows = _read_jsonl(archive, "data/corpus.jsonl")
    return claims, {int(row["doc_id"]): row for row in corpus_rows}


def _read_jsonl(
    archive: tarfile.TarFile,
    member_name: str,
) -> list[dict[str, Any]]:
    stream = archive.extractfile(member_name)
    if stream is None:
        raise ValueError(f"scifact_v0_87_member_missing:{member_name}")
    text = io.TextIOWrapper(stream, encoding="utf-8")
    return [json.loads(line) for line in text if line.strip()]


def _claim_state(claim: dict[str, Any]) -> str:
    labels = {
        rationale["label"]
        for rationales in claim.get("evidence", {}).values()
        for rationale in rationales
    }
    if not labels:
        return "NOT_ENOUGH_INFO"
    if labels == {"SUPPORT"}:
        return "SUPPORTED"
    if labels == {"CONTRADICT"}:
        return "REFUTED"
    raise ValueError("scifact_v0_87_conflicting_gold_labels")


def _selection_key(claim: dict[str, Any]) -> str:
    return hashlib.sha256(
        f"scifact-v0.87:{claim['id']}".encode("utf-8")
    ).hexdigest()
