from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentos_kernel import ProviderCapabilityProfile

from local_collective_cognition.frontier_experiment import TASK_KIND
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.comparison_frame_runtime import (
    run_comparison_frame_panel,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "comparison_frame_v0_67"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.67 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


class FixtureFrameAdapter:
    profile = ProviderCapabilityProfile(
        provider_id="fixture-comparison-frame-v0-67",
        model_id="fixture",
        task_kinds=(TASK_KIND,),
        max_timeout_seconds=600,
    )

    def __init__(self, oracle: dict[str, dict]):
        self.oracle = oracle

    def invoke(self, task):
        case_id = task.inputs["case_id"]
        mechanism = task.inputs["mechanism"]
        if mechanism == "A3_COMPARISON_FRAME":
            result = self._frame(task)
        else:
            result = self._basis(task, self.oracle[case_id]["label"])
        return {
            "result": result,
            "usage": {"provider_calls": 1, "total_tokens": 10},
            "provenance_refs": list(task.allowed_evidence),
        }

    @staticmethod
    def _frame(task):
        return {
            "case_id": task.inputs["case_id"],
            "mechanism": "A3_COMPARISON_FRAME",
            "source_item_hash": task.inputs["source_item_hash"],
            "source_admission_hash": hash_payload(
                task.inputs["admission_receipt"]
            ),
            "study_arms": ["intervention", "comparator"],
            "focal_intervention_members": ["intervention"],
            "comparator_members": ["comparator"],
            "contrast_type": "BINARY",
            "normalization_rule": "DIRECT_INTERVENTION_VS_COMPARATOR",
            "timepoint_requirement": {
                "mode": "UNCONSTRAINED", "value": ""
            },
            "measurement_requirement": {
                "mode": "UNCONSTRAINED", "value": ""
            },
            "frame_status": "RESOLVED",
            "ambiguity_axes": [],
            "rationale": "fixture frame",
            "evidence_refs": list(task.allowed_evidence),
        }

    @staticmethod
    def _basis(task, label):
        records = []
        for index, span in enumerate(
            task.inputs["admitted_candidate_spans"]
        ):
            records.append({
                "span_id": span["span_id"],
                "outcome_binding": "EXACT",
                "focal_contrast_binding": "EXACT",
                "timepoint_binding": "ALLOWED_BY_UNCONSTRAINED",
                "measurement_binding": "ALLOWED_BY_UNCONSTRAINED",
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
                "rationale": "fixture frame-bound basis",
            })
        return {
            "case_id": task.inputs["case_id"],
            "mechanism": "A3_FRAME_BOUND_BASIS",
            "source_item_hash": task.inputs["source_item_hash"],
            "source_admission_hash": hash_payload(
                task.inputs["admission_receipt"]
            ),
            "source_frame_hash": task.inputs["source_frame_hash"],
            "frame_consumed": True,
            "all_admitted_spans_assessed": True,
            "basis_records": records,
            "evidence_refs": list(task.allowed_evidence),
        }


def test_fixture_runtime_closes_all_cases_without_provider_synthesis() -> None:
    panel = read("calibration_private.json")
    run = run_comparison_frame_panel(
        panel=panel,
        preregistration=read("calibration_preregistration.json"),
        admission_receipts=panel["source_admission_receipts"],
        adapter=FixtureFrameAdapter(panel["private_gold"]),
    )
    assert len(run["frame_receipts"]) == 12
    assert len(run["basis_receipts"]) == 12
    assert len(run["receipts"]) == 12
    assert len(run["task_calls"]) == 24
    assert run["contract_failures"] == []
    assert run["compiler_failures"] == []
    assert not run["provider_compiler_override_allowed"]
    assert not run["private_gold_exposed"]
    assert not run["core_write_allowed"]
    assert not run["retention_write_allowed"]
