"""Fresh SciFact holdout and preregistration for binding-veto v0.89."""

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
HOLDOUT_VERSION = "scifact_claim_atom_binding_holdout_v0_89"
SELECTION_VERSION = "sha256_stratified_scifact_dev_third_slice_v0_89"
LABELS = ("SUPPORTED", "REFUTED", "NOT_ENOUGH_INFO")
CASES_PER_LABEL = 6
PRIOR_CASE_IDS = frozenset({
    "36", "51", "70", "115", "127", "141", "180", "232", "274",
    "303", "324", "386", "577", "619", "649", "702", "727", "743",
    "793", "808", "845", "852", "1019", "1062", "1086", "1137",
    "1144", "1146", "1191", "1225", "1226", "1232", "1262", "1270",
    "1273", "1344",
})


def freeze_holdout(archive_path: Path) -> dict[str, Any]:
    source = source_by_id(SOURCE_ID)
    artifact_receipt = verify_external_artifact(archive_path, source)
    if not artifact_receipt["verified"]:
        raise ValueError("scifact_v0_89_source_verification_failed")
    claims, corpus = _read_archive(archive_path)
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for claim in claims:
        if str(claim["id"]) not in PRIOR_CASE_IDS:
            groups[_claim_state(claim)].append(claim)
    selected = []
    for label in LABELS:
        ranked = sorted(groups[label], key=_selection_key)
        if len(ranked) < CASES_PER_LABEL:
            raise ValueError(f"scifact_v0_89_{label}_pool_too_small")
        selected.extend(ranked[:CASES_PER_LABEL])
    cases = []
    for claim in sorted(selected, key=lambda value: int(value["id"])):
        public, private = build_case(claim, corpus)
        cases.append({
            "public_case": public.to_dict(),
            "private_reference": private.to_dict(),
        })
    commitment = {
        "window_initialization": {
            "theory_baseline": "Cognitive Research Architecture v3.7",
            "methodology_kernel": "v1.1",
            "inherited_accept_objects": [
                "PROVIDER_SEMANTIC_SUPPORT_WITHOUT_POLICY_AUTHORITY",
                "DETERMINISTIC_KERNEL_CANDIDATE_COMPILATION",
                "PUBLIC_PRIVATE_BENCHMARK_SEPARATION",
                "V0_88_EVIDENCE_SET_AND_CLAIM_SCOPE_OBJECTS",
            ],
            "preserved_caveats": [
                "V0_87_AND_V0_88_REJECTED_AND_IMMUTABLE",
                "PRETRAINING_CONTAMINATION_NOT_EXCLUDED",
                "DEVELOPMENT_SPLIT_NOT_EXTERNAL_ACCEPTANCE",
                "SCIFACT_REFERENCE_TENSION_REMAINS_POSSIBLE",
            ],
            "specific_objective": (
                "Test whether explicit claim-atom binding plus an isolated "
                "veto-only challenger reduces harmful strong candidates "
                "without excessive loss of correct evidence."
            ),
            "object_before_proxy": (
                "ClaimAtomBinding+IndependentChallenge -> deterministic "
                "veto-only Kernel candidate -> paired safety and SciFact "
                "sentence metrics"
            ),
        },
        "holdout_version": HOLDOUT_VERSION,
        "selection_version": SELECTION_VERSION,
        "source_id": SOURCE_ID,
        "source_revision": source.revision,
        "source_artifact_sha256": source.artifact_sha256,
        "source_split": "dev",
        "excluded_case_ids": sorted(PRIOR_CASE_IDS, key=int),
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
    case_count = panel["case_count"]
    value = {
        "preregistration_version": "scifact_claim_atom_binding_prereg_v0_89",
        "source_holdout_hash": panel["artifact_hash"],
        "source_public_holdout_hash": public["artifact_hash"],
        "case_count": case_count,
        "shared_provider_operations": [
            "EVIDENCE_SET",
            "CLAIM_SCOPE",
        ],
        "candidate_only_provider_operations": [
            "CLAIM_ATOM_BINDING",
            "EVIDENCE_BINDING_CHALLENGE",
        ],
        "arm_definition": {
            "A0_FROZEN_V0_88": (
                "shared EvidenceSet+ClaimScope candidate"
            ),
            "A1_BINDING_VETO": (
                "same shared candidate plus binding and isolated veto gate"
            ),
        },
        "authoritative_rationale_metric": (
            "SCIFACT_OFFICIAL_SENTENCE_PRECISION_RECALL_F1"
        ),
        "operational_gate": {
            "valid_evidence_receipts_min": case_count,
            "valid_scope_receipts_min": case_count,
            "valid_binding_receipts_min": case_count,
            "valid_challenge_receipts_min": case_count,
            "contract_failures_max": 0,
            "physical_attempts_max": case_count * 8,
            "hard_total_token_ceiling": 250_000,
        },
        "semantic_gate": {
            "candidate_harmful_strong_candidates_max": 0,
            "candidate_harm_not_above_baseline": True,
            "conditional_harm_reduction_min": 1,
            "candidate_strong_precision_min": 0.90,
            "correct_strong_retention_min": 0.80,
            "sentence_precision_not_below_baseline": True,
            "sentence_f1_delta_min": -0.05,
            "label_accuracy_delta_min": -0.10,
            "candidate_abstention_rate_max": 0.35,
            "veto_only_no_promotion_required": True,
        },
        "conditional_harm_rule": (
            "When A0 has at least one harmful strong candidate, A1 must "
            "remove at least one; otherwise no reduction is required."
        ),
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
        raise ValueError("scifact_v0_89_holdout_hash_invalid")
    if panel.get("holdout_version") != HOLDOUT_VERSION:
        raise ValueError("scifact_v0_89_holdout_version_invalid")
    if panel.get("case_count") != len(panel.get("cases", [])):
        raise ValueError("scifact_v0_89_case_count_invalid")
    if panel.get("label_balance") != {
        label: CASES_PER_LABEL for label in sorted(LABELS)
    }:
        raise ValueError("scifact_v0_89_label_balance_invalid")
    selected_ids = {
        item["public_case"]["case_id"] for item in panel.get("cases", [])
    }
    if selected_ids.intersection(PRIOR_CASE_IDS):
        raise ValueError("scifact_v0_89_prior_case_overlap")
    if panel.get("provider_calls_before_freeze") != 0:
        raise ValueError("scifact_v0_89_prefreeze_provider_call_detected")


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
        raise ValueError("scifact_v0_89_preregistration_hash_invalid")
    if preregistration.get("source_holdout_hash") != panel["artifact_hash"]:
        raise ValueError("scifact_v0_89_preregistration_panel_mismatch")
    if (
        preregistration.get("authoritative_rationale_metric")
        != "SCIFACT_OFFICIAL_SENTENCE_PRECISION_RECALL_F1"
    ):
        raise ValueError("scifact_v0_89_metric_authority_invalid")
    if preregistration.get("same_version_retuning_allowed") is not False:
        raise ValueError("scifact_v0_89_retuning_boundary_invalid")


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
        raise ValueError(f"scifact_v0_89_member_missing:{member_name}")
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
    raise ValueError("scifact_v0_89_conflicting_gold_labels")


def _selection_key(claim: dict[str, Any]) -> str:
    return hashlib.sha256(
        f"scifact-v0.89:{claim['id']}".encode("utf-8")
    ).hexdigest()
