"""Sixth unused-source holdout for boundary review v0.83."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .admission_v7_fresh_holdout import (
    SELECTED_PROMPT_IDS as V082_PROMPT_IDS,
    prior_surface_ids as v082_prior_surface_ids,
)
from .evidence_inference_bridge import (
    build_selected_panel,
    public_panel,
    validate_panel,
)
from .provider_telemetry import hash_payload


SELECTED_PROMPT_IDS = (
    "3917",
    "8852",
    "6746",
    "9225",
    "9331",
    "11996",
    "10063",
    "13775",
    "212",
    "3625",
    "9126",
    "10709",
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
    "admission_v8_compiler.py",
    "admission_v8_contracts.py",
    "admission_v8_facts.py",
    "admission_v8_runtime.py",
    "admission_v8_schemas.py",
    "admission_v8_tasks.py",
)


def prior_surface_ids():
    return v082_prior_surface_ids() | set(V082_PROMPT_IDS)


def build_fresh_holdout(paths, *, source_manifest):
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-admission-v8-fresh-holdout",
        split="sixth_unused_test_selection_v0_83",
        manifest=source_manifest,
        external_transfer_claim=True,
    )
    value = {
        key: item for key, item in panel.items()
        if key != "artifact_hash"
    }
    value.update({
        "bridge_version": "admission_v8_fresh_holdout_v0_83",
        "selection_version": "sha256_sixth_unused_test_objects_v0_83",
        "selected_prompt_ids": list(SELECTED_PROMPT_IDS),
        "prior_surface_ids_hash": hash_payload(
            sorted(prior_surface_ids())
        ),
        "local_pipeline_object_fresh": True,
        "prior_holdout_reused": False,
        "typed_reference_available": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    })
    return {**value, "artifact_hash": hash_payload(value)}


def validate_fresh_holdout(panel):
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
        or panel.get("typed_reference_available") is not False
    ):
        raise ValueError("admission_v8_fresh_holdout_invalid")


def build_preregistration(panel):
    validate_fresh_holdout(panel)
    value = {
        "preregistration_version": "admission_v8_fresh_holdout_v0_83",
        "source_panel_hash": panel["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "arms": [
            "A11_TYPED_EVIDENCE_ADMISSION",
            "A14_ATOMIC_SEMANTIC_WITNESS",
            "A16_STAGED_CONTEXT_UTILITY_ADDON",
            "A17_SELECTIVE_EVIDENCE_BOUNDARY_REVIEW",
        ],
        "case_count": 12,
        "label_balance": panel["label_balance"],
        "prompt_or_contract_tuning_after_freeze_allowed": False,
        "holdout_reexecution_allowed": False,
        "benchmark_gold_role": "SECONDARY_COVERAGE_GUARD_ONLY",
        "primary_semantic_gate": "EXTERNAL_TYPED_REFERENCE_REQUIRED",
        "operational_gate": {
            "valid_receipts_min_per_arm": 11,
            "failures_max_per_arm": 1,
            "complete_partitions_min_per_arm": 11,
            "reject_partition_invariance_required": True,
            "grounded_boundary_mutation_required": True,
            "conflicted_boundary_mutation_allowed": False,
            "provider_disposition_authority": False,
        },
        "maximum_provider_tasks_per_arm": 12,
        "maximum_total_provider_tasks": 48,
        "maximum_total_physical_attempts": 96,
        "hard_total_token_ceiling": 550000,
        "freshness_scope": "LOCAL_PIPELINE_UNSEEN_SOURCE_OBJECTS",
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
        or value.get("primary_semantic_gate")
        != "EXTERNAL_TYPED_REFERENCE_REQUIRED"
        or gate.get("reject_partition_invariance_required") is not True
        or gate.get("grounded_boundary_mutation_required") is not True
        or gate.get("conflicted_boundary_mutation_allowed") is not False
        or gate.get("provider_disposition_authority") is not False
    ):
        raise ValueError("admission_v8_preregistration_invalid")


def public_fresh_holdout(panel):
    public = public_panel(panel)
    return {
        **public,
        "selection_version": panel["selection_version"],
        "case_count": panel["case_count"],
        "local_pipeline_object_fresh": True,
        "typed_reference_available": False,
    }


def source_hashes():
    root = Path(__file__).resolve().parent
    return {
        name: sha256((root / name).read_bytes()).hexdigest()
        for name in SOURCE_FILES
    }
