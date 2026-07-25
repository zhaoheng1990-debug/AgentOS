"""Fourth unused-source holdout for context utility v0.81."""

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
from .admission_v5_fresh_holdout import (
    SELECTED_PROMPT_IDS as V080_PROMPT_IDS,
)
from .evidence_inference_bridge import (
    build_selected_panel,
    public_panel,
    validate_panel,
)
from .provider_telemetry import hash_payload


SELECTED_PROMPT_IDS = (
    "9226",
    "9269",
    "13774",
    "6789",
    "10176",
    "13165",
    "208",
    "13164",
    "11178",
    "97",
    "13877",
    "13729",
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
    "admission_v6_compiler.py",
    "admission_v6_contracts.py",
    "admission_v6_derivation.py",
    "admission_v6_facts.py",
    "admission_v6_runtime.py",
    "admission_v6_schemas.py",
    "admission_v6_tasks.py",
)


def prior_surface_ids():
    return set(
        PRIOR_TEST_PROMPT_IDS
        + V077_DEVELOPMENT_PROMPT_IDS
        + V078_PROMPT_IDS
        + V079_PROMPT_IDS
        + V080_PROMPT_IDS
    )


def build_fresh_holdout(paths, *, source_manifest):
    panel = build_selected_panel(
        paths=paths,
        selected_prompt_ids=SELECTED_PROMPT_IDS,
        split_ids_name="test_article_ids.txt",
        benchmark_id="evidence-inference-admission-v6-fresh-holdout",
        split="fourth_unused_test_selection_v0_81",
        manifest=source_manifest,
        external_transfer_claim=True,
    )
    value = {
        key: item for key, item in panel.items()
        if key != "artifact_hash"
    }
    value.update({
        "bridge_version": "admission_v6_fresh_holdout_v0_81",
        "selection_version": "sha256_fourth_unused_test_objects_v0_81",
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
        raise ValueError("admission_v6_fresh_holdout_invalid")


def build_preregistration(panel):
    validate_fresh_holdout(panel)
    value = {
        "preregistration_version": "admission_v6_fresh_holdout_v0_81",
        "source_panel_hash": panel["artifact_hash"],
        "mechanism_source_hashes": source_hashes(),
        "arms": [
            "A11_TYPED_EVIDENCE_ADMISSION",
            "A14_ATOMIC_SEMANTIC_WITNESS",
            "A15_CONTEXT_UTILITY_WITNESS",
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
            "candidate_context_and_reject_both_required": True,
            "grounded_context_policy_required": True,
            "context_conflict_effect_demotion_allowed": False,
        },
        "maximum_provider_tasks_per_arm": 12,
        "maximum_total_provider_tasks": 36,
        "maximum_total_physical_attempts": 72,
        "hard_total_token_ceiling": 400000,
        "freshness_scope": "LOCAL_PIPELINE_UNSEEN_SOURCE_OBJECTS",
        "pretraining_contamination_excluded": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def build_preflight_amendment(preregistration):
    current = source_hashes()
    frozen = preregistration["mechanism_source_hashes"]
    changes = {
        name: {
            "frozen_sha256": frozen[name],
            "amended_sha256": current[name],
        }
        for name in current
        if frozen.get(name) != current[name]
    }
    if set(changes) != {"admission_v6_runtime.py"}:
        raise ValueError("admission_v6_preflight_amendment_scope_invalid")
    value = {
        "amendment_version": "admission_v6_preflight_amendment_v0_81_1",
        "source_preregistration_hash": preregistration["artifact_hash"],
        "changed_source_files": changes,
        "reason": "MISSING_LOCAL_PREREGISTRATION_HASH_HELPER",
        "candidate_provider_calls_before_amendment": 0,
        "prompt_changed": False,
        "schema_changed": False,
        "compiler_policy_changed": False,
        "holdout_selection_changed": False,
        "baseline_and_atomic_runs_reusable": True,
        "candidate_reexecution": False,
        "runtime_tuning_authority": False,
        "core_write_allowed": False,
        "retention_write_allowed": False,
        "production_authority": False,
    }
    return {**value, "artifact_hash": hash_payload(value)}


def validate_preflight_amendment(value, *, preregistration):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    changes = value.get("changed_source_files", {})
    if (
        value.get("artifact_hash") != hash_payload(commitment)
        or value.get("source_preregistration_hash")
        != preregistration.get("artifact_hash")
        or set(changes) != {"admission_v6_runtime.py"}
        or changes["admission_v6_runtime.py"].get("frozen_sha256")
        != preregistration["mechanism_source_hashes"][
            "admission_v6_runtime.py"
        ]
        or changes["admission_v6_runtime.py"].get("amended_sha256")
        != source_hashes()["admission_v6_runtime.py"]
        or value.get("candidate_provider_calls_before_amendment") != 0
        or value.get("prompt_changed") is not False
        or value.get("schema_changed") is not False
        or value.get("compiler_policy_changed") is not False
        or value.get("holdout_selection_changed") is not False
        or value.get("baseline_and_atomic_runs_reusable") is not True
        or value.get("candidate_reexecution") is not False
    ):
        raise ValueError("admission_v6_preflight_amendment_invalid")


def validate_preregistration(value, *, panel, amendment=None):
    commitment = {
        key: item for key, item in value.items() if key != "artifact_hash"
    }
    gate = value.get("operational_gate", {})
    if (
        value.get("artifact_hash") != hash_payload(commitment)
        or value.get("source_panel_hash") != panel.get("artifact_hash")
        or (
            value.get("mechanism_source_hashes") != source_hashes()
            and not _valid_amendment(amendment, value)
        )
        or value.get("prompt_or_contract_tuning_after_freeze_allowed")
        is not False
        or value.get("holdout_reexecution_allowed") is not False
        or value.get("primary_semantic_gate")
        != "EXTERNAL_TYPED_REFERENCE_REQUIRED"
        or gate.get("candidate_context_and_reject_both_required")
        is not True
        or gate.get("grounded_context_policy_required") is not True
        or gate.get("context_conflict_effect_demotion_allowed")
        is not False
    ):
        raise ValueError("admission_v6_preregistration_invalid")


def _valid_amendment(amendment, preregistration):
    if amendment is None:
        return False
    try:
        validate_preflight_amendment(
            amendment,
            preregistration=preregistration,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return True


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
