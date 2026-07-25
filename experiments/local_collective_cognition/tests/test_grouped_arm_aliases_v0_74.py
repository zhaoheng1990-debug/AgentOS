import json
from pathlib import Path

from local_collective_cognition.benchmark_bridge_tasks import evidence_refs
from local_collective_cognition.grouped_arm_aliases import (
    build_grouped_alias_catalog,
    validate_grouped_witness_frame,
)
from local_collective_cognition.relation_witness_contracts import (
    validate_witness_frame,
)


ROOT = Path(__file__).parents[3]
V073 = ROOT / "outputs" / "prospective_surface_v0_73"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_grouped_aliases_are_catalog_bounded():
    catalog = {
        "catalog_hash": "catalog-hash",
        "arms": [
            {
                "arm_id": "FOCAL_INTERVENTION",
                "canonical_text": "Kuntai, Tibolone, Control",
            },
            {
                "arm_id": "FOCAL_COMPARATOR",
                "canonical_text": "baseline",
            },
        ],
    }
    aliases = build_grouped_alias_catalog(catalog)
    assert aliases["arms"][0]["accepted_aliases"] == [
        "Kuntai, Tibolone, Control",
        "Kuntai",
        "Tibolone",
        "Control",
    ]
    assert aliases["arms"][1]["accepted_aliases"] == ["baseline"]
    assert aliases["semantic_synonyms_allowed"] is False
    assert aliases["provider_alias_expansion_allowed"] is False


def test_grouped_alias_contract_repairs_only_the_v073_grounding_failure():
    panel = read(V073 / "calibration_private.json")
    run = read(V073 / "calibration_candidate_run.json")
    item = next(
        value
        for value in panel["public_surface"]["items"]
        if value["case_id"] == "EI-CAL-3189"
    )
    admission = panel["source_admission_receipts"]["EI-CAL-3189"]
    catalog = run["arm_catalogs"]["EI-CAL-3189"]
    receipt = run["contract_failures"][0]["invalid_receipt"]
    refs = evidence_refs(item)

    assert validate_witness_frame(
        receipt=receipt,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
    ) == ["WITNESS_INTERVENTION_ALIASES_UNGROUNDED"]
    assert validate_grouped_witness_frame(
        receipt=receipt,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
        alias_catalog=build_grouped_alias_catalog(catalog),
    ) == []

    receipt["intervention_aliases"] = ["unlisted synonym"]
    assert validate_grouped_witness_frame(
        receipt=receipt,
        item=item,
        admission=admission,
        catalog=catalog,
        refs=refs,
        alias_catalog=build_grouped_alias_catalog(catalog),
    ) == ["WITNESS_INTERVENTION_ALIASES_UNGROUNDED"]
