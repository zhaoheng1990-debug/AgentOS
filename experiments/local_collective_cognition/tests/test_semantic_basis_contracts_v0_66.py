from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.semantic_basis_consistency import (
    semantic_consistency_failures,
)
from local_collective_cognition.semantic_basis_contracts import (
    validate_semantic_basis,
    validate_synthesis,
)


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "semantic_basis_v0_66"


def _calibration() -> dict:
    path = OUTPUT / "calibration_private.json"
    if not path.exists():
        pytest.skip("frozen v0.66 local artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def _orientation_case() -> tuple[dict, dict, dict, dict]:
    panel = _calibration()
    item = next(
        value
        for value in panel["public_surface"]["items"]
        if value["case_id"] == "EI-CAL-5842"
    )
    admission = panel["source_admission_receipts"][item["case_id"]]
    admitted = sorted(
        value["span_id"]
        for value in admission["decisions"]
        if value["decision"] == "ADMIT"
    )
    records = []
    for index, span_id in enumerate(admitted):
        records.append({
            "span_id": span_id,
            "outcome_binding": "EXACT",
            "timepoint_binding": "UNSPECIFIED_IN_OBJECT",
            "measurement_binding": "EXACT_OR_COMPATIBLE",
            "comparison_orientation": "COMPARATOR_VS_INTERVENTION",
            "observed_direction": "HIGHER",
            "significance_state": "SIGNIFICANT",
            "admissibility": "DECISIVE" if index == 0 else "SUPPORTING",
            "rationale": "Comparator has more pages, so intervention has fewer.",
        })
    refs = evidence_refs(item)
    basis = {
        "case_id": item["case_id"],
        "mechanism": "A2_SEMANTIC_BASIS",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "all_admitted_spans_assessed": True,
        "basis_records": records,
        "ambiguity_axes": [],
        "evidence_refs": list(refs),
    }
    synthesis = {
        "case_id": item["case_id"],
        "mechanism": "A2_SEMANTIC_SYNTHESIS",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_basis_hash": hash_payload(basis),
        "basis_records_consumed": True,
        "decision_state": "DECISIVE",
        "predicted_label": "DECREASED",
        "material_ambiguity": "NONE",
        "orientation_rule_applied": True,
        "significance_rule_applied": True,
        "primary_span_ids": admitted[:1],
        "corroborating_span_ids": admitted[1:],
        "counter_span_ids": [],
        "rejected_after_basis_span_ids": [],
        "rationale": "Comparator-first direction normalized.",
        "evidence_refs": list(refs),
    }
    return item, admission, basis, synthesis


def test_complete_typed_chain_normalizes_comparator_direction() -> None:
    item, admission, basis, synthesis = _orientation_case()
    refs = evidence_refs(item)
    assert validate_semantic_basis(
        receipt=basis, item=item, admission=admission, refs=refs
    ) == []
    assert validate_synthesis(
        receipt=synthesis,
        item=item,
        admission=admission,
        basis=basis,
        refs=refs,
    ) == []
    assert semantic_consistency_failures(
        basis=basis, synthesis=synthesis
    ) == []


def test_basis_omission_fails_structural_completeness() -> None:
    item, admission, basis, _ = _orientation_case()
    basis["basis_records"].pop()
    assert "BASIS_SPAN_COVERAGE_INVALID" in validate_semantic_basis(
        receipt=basis,
        item=item,
        admission=admission,
        refs=evidence_refs(item),
    )


def test_borderline_basis_cannot_support_directional_effect() -> None:
    _, _, basis, synthesis = _orientation_case()
    basis["basis_records"][0]["significance_state"] = (
        "TREND_OR_BORDERLINE"
    )
    synthesis["source_basis_hash"] = hash_payload(basis)
    assert "CONSISTENCY_EFFECT_NOT_SUPPORTED" in (
        semantic_consistency_failures(
            basis=basis, synthesis=synthesis
        )
    )


def test_basis_state_and_synthesis_partition_must_match() -> None:
    _, _, basis, synthesis = _orientation_case()
    first = synthesis["primary_span_ids"].pop()
    synthesis["counter_span_ids"].append(first)
    assert (
        "CONSISTENCY_COUNTER_SPAN_IDS_STATE_MISMATCH"
        in semantic_consistency_failures(
            basis=basis, synthesis=synthesis
        )
    )
