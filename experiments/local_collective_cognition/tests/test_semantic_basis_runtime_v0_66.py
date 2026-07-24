from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentos_kernel import ProviderCapabilityProfile

from local_collective_cognition.frontier_experiment import TASK_KIND
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.semantic_basis_runtime import (
    run_semantic_basis_panel,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "semantic_basis_v0_66"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.66 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


class FixtureSemanticBasisAdapter:
    profile = ProviderCapabilityProfile(
        provider_id="fixture-semantic-basis-v0-66",
        model_id="fixture",
        task_kinds=(TASK_KIND,),
        max_timeout_seconds=600,
    )

    def __init__(self, oracle: dict[str, dict]):
        self.oracle = oracle

    def invoke(self, task):
        mechanism = task.inputs["mechanism"]
        case_id = task.inputs["case_id"]
        label = self.oracle[case_id]["label"]
        if mechanism == "A2_SEMANTIC_BASIS":
            records = []
            for index, span in enumerate(
                task.inputs["admitted_candidate_spans"]
            ):
                records.append({
                    "span_id": span["span_id"],
                    "outcome_binding": "EXACT",
                    "timepoint_binding": "UNSPECIFIED_IN_OBJECT",
                    "measurement_binding": "EXACT_OR_COMPATIBLE",
                    "comparison_orientation": (
                        "NON_DIRECTIONAL"
                        if label == "NO_DIFFERENCE"
                        else "INTERVENTION_VS_COMPARATOR"
                    ),
                    "observed_direction": {
                        "INCREASED": "HIGHER",
                        "DECREASED": "LOWER",
                        "NO_DIFFERENCE": "NO_MATERIAL_DIFFERENCE",
                    }[label],
                    "significance_state": (
                        "NOT_SIGNIFICANT"
                        if label == "NO_DIFFERENCE"
                        else "SIGNIFICANT"
                    ),
                    "admissibility": (
                        "DECISIVE" if index == 0 else "SUPPORTING"
                    ),
                    "rationale": "fixture typed basis",
                })
            result = {
                "case_id": case_id,
                "mechanism": mechanism,
                "source_item_hash": task.inputs["source_item_hash"],
                "source_admission_hash": hash_payload(
                    task.inputs["admission_receipt"]
                ),
                "all_admitted_spans_assessed": True,
                "basis_records": records,
                "ambiguity_axes": [],
                "evidence_refs": list(task.allowed_evidence),
            }
        else:
            basis = task.inputs["semantic_basis_receipt"]
            primary = [
                value["span_id"]
                for value in basis["basis_records"]
                if value["admissibility"] == "DECISIVE"
            ]
            corroborating = [
                value["span_id"]
                for value in basis["basis_records"]
                if value["admissibility"] == "SUPPORTING"
            ]
            result = {
                "case_id": case_id,
                "mechanism": mechanism,
                "source_item_hash": hash_payload(
                    next(
                        item
                        for item in read("calibration_private.json")[
                            "public_surface"
                        ]["items"]
                        if item["case_id"] == case_id
                    )
                ),
                "source_admission_hash": hash_payload(
                    task.inputs["admission_receipt"]
                ),
                "source_basis_hash": hash_payload(basis),
                "basis_records_consumed": True,
                "decision_state": "DECISIVE",
                "predicted_label": label,
                "material_ambiguity": "NONE",
                "orientation_rule_applied": True,
                "significance_rule_applied": True,
                "primary_span_ids": primary,
                "corroborating_span_ids": corroborating,
                "counter_span_ids": [],
                "rejected_after_basis_span_ids": [],
                "rationale": "fixture synthesis",
                "evidence_refs": list(task.allowed_evidence),
            }
        return {
            "result": result,
            "usage": {"provider_calls": 1, "total_tokens": 10},
            "provenance_refs": list(task.allowed_evidence),
        }


def test_fixture_runtime_closes_all_twelve_cases() -> None:
    panel = read("calibration_private.json")
    run = run_semantic_basis_panel(
        panel=panel,
        preregistration=read("calibration_preregistration.json"),
        admission_receipts=panel["source_admission_receipts"],
        adapter=FixtureSemanticBasisAdapter(panel["private_gold"]),
    )
    assert len(run["basis_receipts"]) == 12
    assert len(run["receipts"]) == 12
    assert run["contract_failures"] == []
    assert run["semantic_consistency_failures"] == []
    assert not run["private_gold_exposed"]
