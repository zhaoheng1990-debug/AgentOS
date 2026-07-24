from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from agentos_kernel import ProviderCapabilityProfile  # noqa: E402
from local_collective_cognition.frontier_experiment import TASK_KIND  # noqa: E402
from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.selection_retention_fresh_binding_runtime import (  # noqa: E402
    run_fresh_binding_panel,
)
from local_collective_cognition.selection_retention_fresh_contracts import (  # noqa: E402
    build_fresh_preregistration,
)
from local_collective_cognition.selection_retention_fresh_holdout import (  # noqa: E402
    audit_selection_retention_fresh_holdout,
    build_selection_retention_fresh_holdout,
)


def artifact(value):
    return {**value, "artifact_hash": hash_payload(value)}


class OverlapAdapter:
    profile = ProviderCapabilityProfile(
        provider_id="fake-overlap",
        model_id="fake",
        task_kinds=(TASK_KIND,),
        max_timeout_seconds=600,
    )

    def invoke(self, task):
        item = task.inputs["public_item"]
        role = task.inputs["binding_role"]
        bindings = []
        for index, value in enumerate(
            item["object_registry"][1:], start=1
        ):
            bindings.append({
                "relation_id": (
                    f"REL-{value['object_id']}-{item['focal_object_id']}"
                ),
                "source_object_id": value["object_id"],
                "target_object_id": item["focal_object_id"],
                "source_object_binding": "EXACT_EXPLICIT",
                "target_outcome_binding": "EXACT_EXPLICIT",
                "evidence_design": "UNTESTED_DIFFERENCE",
                "primary_evidence_span_ids": [f"S{index}"],
                "corroborating_evidence_span_ids": [],
                "counterevidence_span_ids": [],
                "gap_evidence_span_ids": [],
                "rationale": "test",
            })
        if role == "EVIDENCE_BINDER" and item["case_id"] == "SR64-CHIP":
            bindings[0]["corroborating_evidence_span_ids"] = ["S1"]
        return {
            "result": {
                "case_id": item["case_id"],
                "binding_role": role,
                "source_item_hash": hash_payload(item),
                "all_relations_assessed": True,
                "relation_bindings": bindings,
                "evidence_refs": task.allowed_evidence,
            },
            "usage": {"provider_calls": 1, "total_tokens": 1},
            "provenance_refs": task.allowed_evidence,
        }


def test_invalid_semantic_receipt_is_preserved_for_audit():
    corpus = build_selection_retention_fresh_holdout()
    audit = audit_selection_retention_fresh_holdout(corpus)
    closure = artifact({
        "decision": "PASS_TYPED_EVIDENCE_BINDING_CALIBRATION",
        "core_contract_sync_eligible": True,
        "fresh_generalization_claim": False,
    })
    preregistration = build_fresh_preregistration(
        corpus=corpus,
        construction_audit=audit,
        source_closure=closure,
    )
    run = run_fresh_binding_panel(
        corpus=corpus,
        preregistration=preregistration,
        adapter=OverlapAdapter(),
    )
    assert len(run["contract_failures"]) == 1
    failure = run["contract_failures"][0]
    assert failure["contract_failures"] == [
        "BINDING_EVIDENCE_TYPE_OVERLAP"
    ]
    assert failure["invalid_receipt"]["case_id"] == "SR64-CHIP"
    assert run["binding_ready_for_state_assessment"] is False


def test_fresh_runtime_stages_remain_modular():
    limits = {
        "selection_retention_fresh_binding_runtime.py": 300,
        "selection_retention_fresh_binding_tasks.py": 180,
        "selection_retention_fresh_selection_runtime.py": 300,
        "selection_retention_fresh_consequences.py": 120,
        "selection_retention_fresh_retention_runtime.py": 300,
        "selection_retention_fresh_provider_helpers.py": 80,
        "selection_retention_fresh_runtime.py": 40,
    }
    package = PACK / "local_collective_cognition"
    for filename, maximum in limits.items():
        lines = (package / filename).read_text(
            encoding="utf-8"
        ).splitlines()
        assert len(lines) <= maximum, (filename, len(lines), maximum)
