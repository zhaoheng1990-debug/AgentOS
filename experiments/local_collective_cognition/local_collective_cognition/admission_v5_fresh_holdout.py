"""Third unused-source holdout for atomic witness v0.80."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path

from .admission_v3_fresh_holdout import (
    PRIOR_TEST_PROMPT_IDS,
    SELECTED_PROMPT_IDS as V078_PROMPT_IDS,
    V077_DEVELOPMENT_PROMPT_IDS,
)
from .admission_v4_fresh_holdout import (
    SELECTED_PROMPT_IDS as V079_PROMPT_IDS,
)
from .evidence_inference_bridge import (
    build_selected_panel,
    public_panel,
    validate_panel,
)
from .provider_telemetry import hash_payload


SELECTED_PROMPT_IDS = (
    "694",
    "1103",
    "3145",
    "6747",
    "10179",
    "8560",
    "13163",
    "8430",
    "5792",
    "3209",
    "13791",
    "11993",
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
)


def build_fresh_holdout(paths, *, source_manifest):
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-admission-v5-fresh-holdout",
        split="third_unused_test_selection_v0_80",
        manifest=source_manifest,
        external_transfer_claim=True,
    )
    value = {
        key: item for key, item in panel.items()
        if key != "artifact_hash"
    }
    value.update({
        "bridge_version": "admission_v5_fresh_holdout_v0_80",
        "selection_version": "sha256_third_unused_test_objects_v0_80",
        "selected_prompt_ids": list(SELECTED_PROMPT_IDS),
        "prior_surface_ids_hash": hash_payload(sorted(
            set(PRIOR_TEST_PROMPT_IDS)
            | set(V077_DEVELOPMENT_PROMPT_IDS)
            | set(V078_PROMPT_IDS)
            | set(V079_PROMPT_IDS)
        )),
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
    prior = (
        set(PRIOR_TEST_PROMPT_IDS)
        | set(V077_DEVELOPMENT_PROMPT_IDS)
        | set(V078_PROMPT_IDS)
        | set(V079_PROMPT_IDS)
    )
    if (
        tuple(panel.get("selected_prompt_ids", []))
        != SELECTED_PROMPT_IDS
        or selected & prior
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
        raise ValueError("admission_v5_fresh_holdout_invalid")


def build_preregistration(panel):
    validate_fresh_holdout(panel)
    value = {
        "preregistration_version": "admission_v5_fresh_holdout_v0_80",
        "source_panel_hash": panel["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "arms": [
            "A11_TYPED_EVIDENCE_ADMISSION",
            "A14_ATOMIC_SEMANTIC_WITNESS",
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
            "conflict_ledger_required": True,
            "conflicted_effect_promotion_allowed": False,
        },
        "maximum_provider_tasks_per_arm": 12,
        "maximum_total_provider_tasks": 24,
        "maximum_total_physical_attempts": 48,
        "hard_total_token_ceiling": 250000,
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
        or value.get("primary_semantic_gate")
        != "EXTERNAL_TYPED_REFERENCE_REQUIRED"
        or gate.get("conflict_ledger_required") is not True
        or gate.get("conflicted_effect_promotion_allowed") is not False
    ):
        raise ValueError("admission_v5_preregistration_invalid")


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
