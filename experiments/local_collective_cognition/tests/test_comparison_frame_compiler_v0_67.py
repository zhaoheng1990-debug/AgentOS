from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_contracts import (
    admission_partition,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.comparison_frame_contracts import (
    validate_comparison_frame,
    validate_frame_basis,
)
from local_collective_cognition.deterministic_basis_compiler import (
    compile_basis,
    validate_compiled_receipt,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "comparison_frame_v0_67"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.67 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def case(case_id: str) -> tuple[dict, dict]:
    panel = read("calibration_private.json")
    item = next(
        value for value in panel["public_surface"]["items"]
        if value["case_id"] == case_id
    )
    return item, panel["source_admission_receipts"][case_id]


def frame(item: dict, admission: dict, **changes) -> dict:
    value = {
        "case_id": item["case_id"],
        "mechanism": "A3_COMPARISON_FRAME",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "study_arms": ["intervention", "comparator"],
        "focal_intervention_members": ["intervention"],
        "comparator_members": ["comparator"],
        "contrast_type": "BINARY",
        "normalization_rule": "REVERSE_IF_COMPARATOR_STATED_FIRST",
        "timepoint_requirement": {
            "mode": "UNCONSTRAINED", "value": ""
        },
        "measurement_requirement": {
            "mode": "UNCONSTRAINED", "value": ""
        },
        "frame_status": "RESOLVED",
        "ambiguity_axes": [],
        "rationale": "fixture frame",
        "evidence_refs": list(evidence_refs(item)),
    }
    value.update(changes)
    return value


def basis(
    item: dict,
    admission: dict,
    parsed_frame: dict,
    *,
    orientation: str,
    direction: str,
    significance: str,
    timepoint: str = "ALLOWED_BY_UNCONSTRAINED",
) -> dict:
    admitted, _ = admission_partition(admission)
    records = []
    for index, span_id in enumerate(admitted):
        records.append({
            "span_id": span_id,
            "outcome_binding": "EXACT",
            "focal_contrast_binding": "EXACT",
            "timepoint_binding": timepoint,
            "measurement_binding": "ALLOWED_BY_UNCONSTRAINED",
            "comparison_orientation": orientation,
            "observed_direction": direction,
            "significance_state": significance,
            "admissibility": "DECISIVE" if index == 0 else "SUPPORTING",
            "rationale": "fixture basis",
        })
    return {
        "case_id": item["case_id"],
        "mechanism": "A3_FRAME_BOUND_BASIS",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_frame_hash": hash_payload(parsed_frame),
        "frame_consumed": True,
        "all_admitted_spans_assessed": True,
        "basis_records": records,
        "evidence_refs": list(evidence_refs(item)),
    }


def test_comparator_first_direction_is_mechanically_reversed() -> None:
    item, admission = case("EI-CAL-5842")
    parsed = frame(item, admission)
    typed = basis(
        item,
        admission,
        parsed,
        orientation="COMPARATOR_VS_INTERVENTION",
        direction="HIGHER",
        significance="SIGNIFICANT",
    )
    receipt = compile_basis(
        item=item, admission=admission, frame=parsed, basis=typed
    )
    assert receipt["predicted_label"] == "DECREASED"
    assert not receipt["provider_override_allowed"]


def test_borderline_direction_compiles_to_no_difference() -> None:
    item, admission = case("EI-CAL-11179")
    parsed = frame(item, admission)
    typed = basis(
        item,
        admission,
        parsed,
        orientation="INTERVENTION_VS_COMPARATOR",
        direction="LOWER",
        significance="TREND_OR_BORDERLINE",
    )
    assert compile_basis(
        item=item, admission=admission, frame=parsed, basis=typed
    )["predicted_label"] == "NO_DIFFERENCE"


def test_grouped_intervention_within_baseline_preserves_direction() -> None:
    item, admission = case("EI-CAL-3189")
    parsed = frame(
        item,
        admission,
        study_arms=["Kuntai", "Tibolone", "Control", "baseline"],
        focal_intervention_members=["Kuntai", "Tibolone", "Control"],
        comparator_members=["baseline"],
        contrast_type="WITHIN_GROUP_BASELINE",
        normalization_rule="WITHIN_GROUP_VS_BASELINE",
    )
    typed = basis(
        item,
        admission,
        parsed,
        orientation="INTERVENTION_VS_COMPARATOR",
        direction="LOWER",
        significance="SIGNIFICANT",
    )
    assert compile_basis(
        item=item, admission=admission, frame=parsed, basis=typed
    )["predicted_label"] == "DECREASED"


def test_unconstrained_query_accepts_explicit_passage_timepoint() -> None:
    item, admission = case("EI-CAL-9330")
    parsed = frame(item, admission)
    typed = basis(
        item,
        admission,
        parsed,
        orientation="INTERVENTION_VS_COMPARATOR",
        direction="LOWER",
        significance="SIGNIFICANT",
    )
    assert compile_basis(
        item=item, admission=admission, frame=parsed, basis=typed
    )["predicted_label"] == "DECREASED"


def test_compiled_receipt_is_exactly_replayable() -> None:
    item, admission = case("EI-CAL-5842")
    parsed = frame(item, admission)
    typed = basis(
        item,
        admission,
        parsed,
        orientation="COMPARATOR_VS_INTERVENTION",
        direction="HIGHER",
        significance="SIGNIFICANT",
    )
    receipt = compile_basis(
        item=item, admission=admission, frame=parsed, basis=typed
    )
    assert validate_compiled_receipt(
        receipt=receipt,
        item=item,
        admission=admission,
        frame=parsed,
        basis=typed,
    ) == []
    receipt["predicted_label"] = "INCREASED"
    assert validate_compiled_receipt(
        receipt=receipt,
        item=item,
        admission=admission,
        frame=parsed,
        basis=typed,
    ) == ["COMPILER_RECEIPT_NOT_REPLAYABLE"]


def test_incompatible_coordinate_must_be_rejected() -> None:
    item, admission = case("EI-CAL-9330")
    parsed = frame(item, admission)
    typed = basis(
        item,
        admission,
        parsed,
        orientation="INTERVENTION_VS_COMPARATOR",
        direction="LOWER",
        significance="SIGNIFICANT",
        timepoint="DIFFERENT",
    )
    assert "BASIS_INCOMPATIBLE_SPAN_NOT_REJECTED" in validate_frame_basis(
        receipt=typed,
        item=item,
        admission=admission,
        frame=parsed,
        refs=evidence_refs(item),
    )


def test_resolved_frame_cannot_carry_ambiguity_axis() -> None:
    item, admission = case("EI-CAL-5842")
    parsed = frame(item, admission, ambiguity_axes=["FOCAL_CONTRAST"])
    assert "FRAME_RESOLVED_STATE_INCONSISTENT" in validate_comparison_frame(
        receipt=parsed,
        item=item,
        admission=admission,
        refs=evidence_refs(item),
    )
