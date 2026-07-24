from __future__ import annotations

import json
from pathlib import Path

import pytest

from local_collective_cognition.benchmark_bridge_contracts import (
    admission_partition,
)
from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.provider_telemetry import hash_payload
from local_collective_cognition.relational_basis_compiler import (
    compile_relational_basis,
)
from local_collective_cognition.relational_contrast_contracts import (
    validate_relational_basis,
)
from local_collective_cognition.relational_contrast_objects import arm_catalog


REPO_ROOT = Path(__file__).parents[3]
OUTPUT = REPO_ROOT / "outputs" / "relational_contrast_v0_68"


def read(name: str) -> dict:
    path = OUTPUT / name
    if not path.exists():
        pytest.skip("frozen v0.68 artifacts are not present")
    return json.loads(path.read_text(encoding="utf-8"))


def inputs(case_id: str):
    panel = read("calibration_private.json")
    item = next(
        value for value in panel["public_surface"]["items"]
        if value["case_id"] == case_id
    )
    admission = panel["source_admission_receipts"][case_id]
    catalog = arm_catalog(item)
    frame = {
        "case_id": case_id,
        "mechanism": "A4_RELATIONAL_FRAME",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "intervention_aliases": [item["object"]["intervention"]],
        "comparator_aliases": [item["object"]["comparator"]],
        "relation_mode": "BINARY_BETWEEN_GROUPS",
        "timepoint_requirement": {"mode": "UNCONSTRAINED", "value": ""},
        "measurement_requirement": {"mode": "UNCONSTRAINED", "value": ""},
        "frame_status": "RESOLVED",
        "ambiguity_axes": [],
        "rationale": "fixture",
        "evidence_refs": list(evidence_refs(item)),
    }
    return item, admission, catalog, frame


def basis(item, admission, catalog, frame, subject, reference, relation, sig):
    admitted, _ = admission_partition(admission)
    records = []
    for index, span_id in enumerate(admitted):
        records.append({
            "span_id": span_id,
            "evidence_relevance": "EXACT_OBJECT",
            "subject_group_id": subject,
            "reference_group_id": reference,
            "timepoint_binding": "ALLOWED_BY_UNCONSTRAINED",
            "measurement_binding": "ALLOWED_BY_UNCONSTRAINED",
            "observed_relation": relation,
            "significance_state": sig,
            "evidence_role": "DECISIVE" if index == 0 else "SUPPORTING",
            "rationale": "fixture",
        })
    return {
        "case_id": item["case_id"],
        "mechanism": "A4_RELATIONAL_BASIS",
        "source_item_hash": hash_payload(item),
        "source_admission_hash": hash_payload(admission),
        "source_arm_catalog_hash": catalog["catalog_hash"],
        "source_frame_hash": hash_payload(frame),
        "frame_consumed": True,
        "all_admitted_spans_assessed": True,
        "basis_records": records,
        "evidence_refs": list(evidence_refs(item)),
    }


@pytest.mark.parametrize(
    ("case_id", "subject", "reference", "relation", "sig", "expected"),
    (
        (
            "EI-CAL-5842",
            "FOCAL_COMPARATOR",
            "FOCAL_INTERVENTION",
            "SUBJECT_HIGHER",
            "SIGNIFICANT",
            "DECREASED",
        ),
        (
            "EI-CAL-5791",
            "FOCAL_INTERVENTION",
            "FOCAL_COMPARATOR",
            "SUBJECT_LOWER",
            "SIGNIFICANT",
            "DECREASED",
        ),
        (
            "EI-CAL-11179",
            "FOCAL_INTERVENTION",
            "FOCAL_COMPARATOR",
            "SUBJECT_LOWER",
            "NOT_SIGNIFICANT",
            "NO_DIFFERENCE",
        ),
    ),
)
def test_explicit_relations_compile_without_orientation(
    case_id, subject, reference, relation, sig, expected
) -> None:
    item, admission, catalog, frame = inputs(case_id)
    typed = basis(
        item, admission, catalog, frame, subject, reference, relation, sig
    )
    receipt = compile_relational_basis(
        item=item,
        admission=admission,
        catalog=catalog,
        frame=frame,
        basis=typed,
    )
    assert receipt["predicted_label"] == expected
    assert "comparison_orientation" not in json.dumps(typed)


def test_exact_non_significant_evidence_cannot_be_excluded() -> None:
    item, admission, catalog, frame = inputs("EI-CAL-11179")
    typed = basis(
        item,
        admission,
        catalog,
        frame,
        "FOCAL_INTERVENTION",
        "FOCAL_COMPARATOR",
        "SUBJECT_LOWER",
        "NOT_SIGNIFICANT",
    )
    typed["basis_records"][0]["evidence_role"] = "EXCLUDE_UNRELATED"
    assert "RELATIONAL_BASIS_EXACT_EVIDENCE_EXCLUDED" in (
        validate_relational_basis(
            receipt=typed,
            item=item,
            admission=admission,
            catalog=catalog,
            frame=frame,
            refs=evidence_refs(item),
        )
    )
