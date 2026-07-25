"""Unseen validation-object development screen for v0.85."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .admission_v9_fresh_holdout import (
    SELECTED_PROMPT_IDS as V084_PROMPT_IDS,
    prior_surface_ids as v084_prior_surface_ids,
)
from .evidence_inference_bridge import (
    build_selected_panel,
    public_panel,
    validate_panel,
)
from .provider_telemetry import hash_payload


SELECTED_PROMPT_IDS = (
    "12834",
    "5754",
    "12835",
    "6600",
    "8402",
    "8662",
    "9744",
    "13709",
    "8844",
    "11319",
    "11073",
    "9745",
)
SOURCE_FILES = (
    "admission_v2_compiler.py",
    "admission_v2_contracts.py",
    "admission_v2_runtime.py",
    "admission_v2_schemas.py",
    "admission_v2_tasks.py",
    "admission_v5_compiler.py",
    "admission_v5_contracts.py",
    "admission_v5_derivation.py",
    "admission_v5_facts.py",
    "admission_v5_runtime.py",
    "admission_v5_schemas.py",
    "admission_v5_tasks.py",
    "admission_v6_facts.py",
    "admission_v7_compiler.py",
    "admission_v7_contracts.py",
    "admission_v7_facts.py",
    "admission_v7_runtime.py",
    "admission_v7_schemas.py",
    "admission_v7_tasks.py",
    "admission_v10_compiler.py",
    "admission_v10_contracts.py",
    "admission_v10_facts.py",
    "admission_v10_runtime.py",
    "admission_v10_schemas.py",
    "admission_v10_tasks.py",
)


def prior_surface_ids():
    return v084_prior_surface_ids() | set(V084_PROMPT_IDS)


def build_development_holdout(paths, *, source_manifest):
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="validation_article_ids.txt",
        benchmark_id="evidence-inference-admission-v10-development-screen",
        split="unused_validation_objects_v0_85",
        manifest=source_manifest,
        external_transfer_claim=False,
    )
    value = {
        key: item for key, item in panel.items()
        if key != "artifact_hash"
    }
    value.update({
        "bridge_version": "admission_v10_development_holdout_v0_85",
        "selection_version": "sha256_unused_validation_objects_v0_85",
        "selected_prompt_ids": list(SELECTED_PROMPT_IDS),
        "prior_surface_ids_hash": hash_payload(
            sorted(prior_surface_ids())
        ),
        "local_pipeline_object_fresh": True,
        "prior_holdout_reused": False,
        "source_split_role": "DEVELOPMENT_SCREEN_ONLY",
        "external_transfer_holdout": False,
        "external_acceptance_eligible": False,
        "typed_reference_available": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    return {**value, "artifact_hash": hash_payload(value)}


def validate_development_holdout(panel):
    validate_panel(panel)
    selected = set(panel.get("selected_prompt_ids", []))
    if (
        tuple(panel.get("selected_prompt_ids", []))
        != SELECTED_PROMPT_IDS
        or selected & prior_surface_ids()
        or panel.get("case_count") != 12
        or panel.get("label_balance") != {
            "INCREASED": 4,
            "DECREASED": 4,
            "NO_DIFFERENCE": 4,
        }
        or panel.get("local_pipeline_object_fresh") is not True
        or panel.get("prior_holdout_reused") is not False
        or panel.get("source_split_role") != "DEVELOPMENT_SCREEN_ONLY"
        or panel.get("external_transfer_holdout") is not False
        or panel.get("external_acceptance_eligible") is not False
        or panel.get("typed_reference_available") is not False
    ):
        raise ValueError("admission_v10_development_holdout_invalid")


def build_preregistration(panel):
    validate_development_holdout(panel)
    value = {
        "preregistration_version": "admission_v10_development_v0_85",
        "source_panel_hash": panel["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "arms": [
            "A11_TYPED_EVIDENCE_ADMISSION",
            "A14_ATOMIC_SEMANTIC_WITNESS",
            "A16_STAGED_CONTEXT_UTILITY_ADDON",
            "A19_STUDY_RELATION_REVIEW",
        ],
        "case_count": 12,
        "label_balance": panel["label_balance"],
        "prompt_or_contract_tuning_after_freeze_allowed": False,
        "holdout_reexecution_allowed": False,
        "external_acceptance_allowed": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "primary_semantic_gate": (
            "EXTERNAL_TYPED_REFERENCE_REQUIRED_FOR_SCREEN_RESULT"
        ),
        "operational_gate": {
            "valid_receipts_min_per_arm": 11,
            "failures_max_per_arm": 1,
            "complete_partitions_min_per_arm": 11,
            "grounded_relation_graph_required": True,
            "evidence_to_reject_allowed": False,
            "context_to_reject_allowed": False,
            "reject_to_evidence_allowed": False,
            "conflicted_mutation_allowed": False,
            "provider_disposition_authority": False,
        },
        "maximum_provider_tasks_per_arm": 12,
        "maximum_total_provider_tasks": 48,
        "maximum_total_physical_attempts": 96,
        "hard_total_token_ceiling": 600000,
        "freshness_scope": "LOCAL_PIPELINE_UNSEEN_DEVELOPMENT_OBJECTS",
        "pretraining_contamination_excluded": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def validate_preregistration(value, *, panel):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    gate = value.get("operational_gate", {})
    if (
        value.get("artifact_hash") != hash_payload(commitment)
        or value.get("source_panel_hash") != panel.get("artifact_hash")
        or value.get("mechanism_source_hashes") != source_hashes()
        or value.get("prompt_or_contract_tuning_after_freeze_allowed")
        is not False
        or value.get("holdout_reexecution_allowed") is not False
        or value.get("external_acceptance_allowed") is not False
        or gate.get("grounded_relation_graph_required") is not True
        or gate.get("evidence_to_reject_allowed") is not False
        or gate.get("context_to_reject_allowed") is not False
        or gate.get("reject_to_evidence_allowed") is not False
        or gate.get("conflicted_mutation_allowed") is not False
        or gate.get("provider_disposition_authority") is not False
    ):
        raise ValueError("admission_v10_preregistration_invalid")


def public_development_holdout(panel):
    public = public_panel(panel)
    return {
        **public,
        "selection_version": panel["selection_version"],
        "case_count": panel["case_count"],
        "local_pipeline_object_fresh": True,
        "source_split_role": "DEVELOPMENT_SCREEN_ONLY",
        "external_acceptance_eligible": False,
        "typed_reference_available": False,
    }


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }
