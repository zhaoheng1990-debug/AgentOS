"""Fresh position-rotated marginal-scarcity transfer holdout v0.59."""

from __future__ import annotations

import copy
from collections import Counter

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "marginal_scarcity_transfer_holdout_v0_59"
CORPUS_ID = "local-marginal-scarcity-transfer-v0-59"
REPAIR_VERSION = "marginal_scarcity_transfer_holdout_v0_59_1"
REPAIR_ID = "local-marginal-scarcity-transfer-v0-59-1"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _transfer_case(
    case_id,
    domain,
    outcome,
    labels,
    spans,
    *,
    supported,
    informative_null,
    unresolved,
    target,
    active,
    drop,
):
    case = _case(
        case_id,
        domain,
        f"Resolve the source of {outcome} drift.",
        (outcome, *labels),
        spans,
        supported=supported,
        informative_null=informative_null,
        unresolved=(unresolved,),
        counterevidence=(f"S{int(informative_null[0][1:]) - 1}",),
    )
    return {
        "case": case,
        "target": target,
        "active": active,
        "drop": drop,
    }


CASES = (
    _transfer_case(
        "MT-ORBIT",
        "satellite_attitude_control",
        "pointing error",
        (
            "reaction-wheel profile",
            "thermal cycle",
            "star-tracker firmware",
            "ground-station vendor",
            "momentum-dump policy",
        ),
        (
            "A matched reaction-wheel profile intervention removed the "
            "initial pointing drift.",
            "Thermal-cycle balancing showed no measurable difference.",
            "Randomized star-tracker rollback removed another component.",
            "Ground-station vendors differ, but no matched handover exists.",
            "A momentum-dump policy crossover removed residual drift.",
            "All three effects replicated on an independent simulator.",
        ),
        supported=("O2", "O4", "O6"),
        informative_null=("O3",),
        unresolved="O5",
        target="O2",
        active=(("BASE:C1", "O5"), ("BASE:C2", "O4"), ("BASE:C3", "O6")),
        drop="BASE:C1",
    ),
    _transfer_case(
        "MT-WATER",
        "membrane_water_treatment",
        "permeate quality",
        (
            "cleaning schedule",
            "feed-pressure regime",
            "membrane supplier",
            "antiscalant dosage",
            "plant age",
        ),
        (
            "Cleaning-schedule rollback removed the initial quality drift.",
            "A matched feed-pressure intervention removed residual drift.",
            "Supplier-balanced membrane swaps showed no quality difference.",
            "Randomized antiscalant dosage removed another component.",
            "Plant ages differ, but no age-matched comparison exists.",
            "The schedule, pressure, and dosage effects replicated elsewhere.",
        ),
        supported=("O2", "O3", "O5"),
        informative_null=("O4",),
        unresolved="O6",
        target="O3",
        active=(("BASE:C3", "O5"), ("BASE:C2", "O6"), ("BASE:C1", "O2")),
        drop="BASE:C2",
    ),
    _transfer_case(
        "MT-CROP",
        "controlled_environment_agriculture",
        "growth rate",
        (
            "nutrient recipe",
            "light cycle",
            "airflow controller",
            "sensor vendor",
            "irrigation timing",
        ),
        (
            "Nutrient-recipe balancing showed no growth-rate difference.",
            "A matched light-cycle intervention removed the initial drift.",
            "Airflow-controller replacement removed another component.",
            "Sensor vendors differ, but no vendor-balanced swap exists.",
            "Randomized irrigation timing removed residual drift.",
            "Light, airflow, and irrigation effects replicated in a new bay.",
        ),
        supported=("O3", "O4", "O6"),
        informative_null=("O2",),
        unresolved="O5",
        target="O4",
        active=(("BASE:C2", "O6"), ("BASE:C1", "O3"), ("BASE:C3", "O5")),
        drop="BASE:C3",
    ),
    _transfer_case(
        "MT-TELESCOPE",
        "radio_telescope_array",
        "phase error",
        (
            "calibration cadence",
            "weather regime",
            "correlator firmware",
            "clock-distribution path",
            "antenna vendor",
        ),
        (
            "Calibration-cadence rollback removed the initial phase drift.",
            "Weather regimes differ, but no matched observation exists.",
            "Randomized correlator rollback removed another component.",
            "Clock-path replacement removed the residual phase error.",
            "Antenna-vendor balancing showed no measurable difference.",
            "Cadence, firmware, and clock effects replicated on a subarray.",
        ),
        supported=("O2", "O4", "O5"),
        informative_null=("O6",),
        unresolved="O3",
        target="O5",
        active=(("BASE:C1", "O3"), ("BASE:C3", "O4"), ("BASE:C2", "O2")),
        drop="BASE:C1",
    ),
    _transfer_case(
        "MT-DRONE",
        "autonomous_delivery_fleet",
        "route completion",
        (
            "package vendor",
            "wind regime",
            "navigation firmware",
            "charging policy",
            "handoff protocol",
        ),
        (
            "Package-vendor balancing showed no completion difference.",
            "A matched wind-regime intervention removed the initial drift.",
            "Navigation firmware differs, but no matched rollback exists.",
            "Charging-policy crossover removed another component.",
            "Randomized handoff-protocol rollback removed residual drift.",
            "Wind, charging, and handoff effects replicated in a second city.",
        ),
        supported=("O3", "O5", "O6"),
        informative_null=("O2",),
        unresolved="O4",
        target="O6",
        active=(("BASE:C3", "O5"), ("BASE:C1", "O3"), ("BASE:C2", "O4")),
        drop="BASE:C2",
    ),
    _transfer_case(
        "MT-PATH",
        "digital_pathology_pipeline",
        "grading consistency",
        (
            "stain-normalization policy",
            "scanner firmware",
            "tiling strategy",
            "display vendor",
            "review protocol",
        ),
        (
            "Stain-normalization rollback removed the initial grade drift.",
            "Scanner firmware differs, but no matched rescan exists.",
            "Randomized tiling-strategy replacement removed another component.",
            "Display-vendor balancing showed no consistency difference.",
            "A review-protocol crossover removed residual drift.",
            "Normalization, tiling, and review effects replicated at a new site.",
        ),
        supported=("O2", "O4", "O6"),
        informative_null=("O5",),
        unresolved="O3",
        target="O2",
        active=(("BASE:C1", "O4"), ("BASE:C3", "O3"), ("BASE:C2", "O6")),
        drop="BASE:C3",
    ),
)


def build_marginal_scarcity_transfer_holdout():
    items = []
    bindings = {}
    for specification in CASES:
        case = specification["case"]
        item = _public_item(case)
        item["frozen_active_portfolio"] = [
            _public_relation(pool_id, source)
            for pool_id, source in specification["active"]
        ]
        item["active_portfolio_capacity"] = 3
        items.append(item)
        supported = [
            {"source_object_id": source, "target_object_id": target}
            for source, target in case["supported"]
        ]
        nulls = [
            {"source_object_id": source, "target_object_id": target}
            for source, target in case["informative_null"]
        ]
        protected = [
            pool_id
            for pool_id, _source in specification["active"]
            if pool_id != specification["drop"]
        ]
        bindings[case["case_id"]] = {
            "public_item_hash": hash_payload(item),
            "primary_object_ids": list(case["primary"]),
            "supported_targets": supported,
            "informative_null_targets": nulls,
            "unresolved_targets": [{
                "source_object_id": case["constraints"][0],
                "target_object_id": "O1",
            }],
            "hidden_constraint_object_ids": list(case["constraints"]),
            "counterevidence_span_ids": list(case["counterevidence"]),
            "reference_relation_count": 5,
            "reference_is_exhaustive_over_focal_relations": True,
            "designed_drop_pool_id": specification["drop"],
            "protected_pool_ids": protected,
            "designed_target_relation": {
                "source_object_id": specification["target"],
                "target_object_id": "O1",
            },
            "designed_target_state": "SUPPORTED_EFFECT",
            "designed_gross_cbit_uplift": 2.0,
        }
    items.sort(key=lambda value: hash_payload(
        [CORPUS_VERSION, value["case_id"]]
    ))
    surface = {
        "surface_version": CORPUS_VERSION,
        "items": items,
        "private_outcomes_exposed": False,
        "designed_target_relation_exposed": False,
        "designed_drop_pool_id_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(items),
        "domain_count": len(items),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {**surface, "surface_hash": hash_payload(surface)},
        "private_provenance": {
            "bindings": bindings,
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_59_CONSTRUCTION_AUDIT_ONLY",
        "prior_holdout_labels_reused": False,
        "target_source_positions_rotated_across_cases": True,
        "drop_pool_ids_balanced_across_cases": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_marginal_scarcity_transfer(corpus):
    validate_marginal_scarcity_transfer_holdout(corpus)
    return _audit_transfer(
        corpus,
        audit_version="marginal_scarcity_transfer_audit_v0_59",
    )


def build_marginal_scarcity_transfer_holdout_v0_59_1():
    original = build_marginal_scarcity_transfer_holdout()
    commitment = {
        key: copy.deepcopy(value)
        for key, value in original.items()
        if key != "artifact_hash"
    }
    items = {
        value["case_id"]: value
        for value in commitment["public_surface"]["items"]
    }
    repairs = {
        ("MT-CROP", "S3"): (
            "Replacing the airflow controller removed an independently "
            "measured component of the growth-rate drift."
        ),
        ("MT-ORBIT", "S4"): (
            "Ground-station vendors differ. No intervention, matched "
            "comparison, or replay has tested whether vendor changes "
            "pointing error; the vendor effect is neither supported nor "
            "ruled out."
        ),
    }
    for (case_id, span_id), text in repairs.items():
        span = next(
            value for value in items[case_id]["evidence_spans"]
            if value["span_id"] == span_id
        )
        span["text"] = text
        span["text_hash"] = hash_payload(text)
    commitment["artifact_version"] = REPAIR_VERSION
    commitment["corpus_id"] = REPAIR_ID
    commitment["reference_state"] = (
        "V0_59_1_CONSTRUCTION_REPAIR_AUDIT_ONLY"
    )
    commitment["prior_holdout_labels_reused"] = True
    commitment["repair_reuses_failed_construction_cases"] = True
    commitment["formal_discovery_labels_previously_exposed"] = False
    commitment["source_failed_corpus_hash"] = original["artifact_hash"]
    commitment["construction_repairs"] = [
        {
            "case_id": case_id,
            "span_id": span_id,
            "repair_kind": (
                "FOCAL_OUTCOME_BINDING"
                if case_id == "MT-CROP"
                else "ABSENCE_IS_NOT_NULL"
            ),
        }
        for case_id, span_id in sorted(repairs)
    ]
    commitment["evidence_refs"] = [f"benchmark://{REPAIR_ID}"]
    for item in commitment["public_surface"]["items"]:
        commitment["private_provenance"]["bindings"][
            item["case_id"]
        ]["public_item_hash"] = hash_payload(item)
    surface = {
        key: value
        for key, value in commitment["public_surface"].items()
        if key != "surface_hash"
    }
    surface["surface_version"] = REPAIR_VERSION
    commitment["public_surface"] = {
        **surface,
        "surface_hash": hash_payload(surface),
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_marginal_scarcity_transfer_v0_59_1(corpus):
    validate_marginal_scarcity_transfer_holdout_v0_59_1(corpus)
    return _audit_transfer(
        corpus,
        audit_version="marginal_scarcity_transfer_audit_v0_59_1",
    )


def validate_marginal_scarcity_transfer_holdout_v0_59_1(value):
    if value != build_marginal_scarcity_transfer_holdout_v0_59_1():
        raise ValueError("marginal_scarcity_transfer_holdout_v0_59_1_invalid")


def _audit_transfer(corpus, *, audit_version):
    target_positions = Counter()
    drop_pools = Counter()
    cells = []
    for item in corpus["public_surface"]["items"]:
        binding = corpus["private_provenance"]["bindings"][item["case_id"]]
        active_by_pool = {
            value["pool_candidate_id"]: value["source_object_id"]
            for value in item["frozen_active_portfolio"]
        }
        target = binding["designed_target_relation"]["source_object_id"]
        drop = binding["designed_drop_pool_id"]
        unresolved = binding["unresolved_targets"][0]["source_object_id"]
        protected = set(binding["protected_pool_ids"])
        valid = (
            len(active_by_pool) == item["active_portfolio_capacity"] == 3
            and target not in active_by_pool.values()
            and active_by_pool.get(drop) == unresolved
            and protected == set(active_by_pool) - {drop}
            and binding["designed_gross_cbit_uplift"] == 2.0
        )
        target_positions[target] += 1
        drop_pools[drop] += 1
        cells.append({
            "case_id": item["case_id"],
            "target_source_object_id": target,
            "designed_drop_pool_id": drop,
            "target_omitted": target not in active_by_pool.values(),
            "drop_relation_is_unresolved": active_by_pool.get(drop) == unresolved,
            "protected_pool_ids": sorted(protected),
            "construction_valid": valid,
        })
    commitment = {
        "audit_version": audit_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "cell_count": len(cells),
        "valid_cell_count": sum(value["construction_valid"] for value in cells),
        "target_position_counts": dict(sorted(target_positions.items())),
        "target_position_coverage": len(target_positions),
        "drop_pool_counts": dict(sorted(drop_pools.items())),
        "drop_pool_balance_valid": set(drop_pools.values()) == {2},
        "cells": cells,
        "provider_calls_added": 0,
        "formal_experiment_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_marginal_scarcity_transfer_holdout(value):
    if value != build_marginal_scarcity_transfer_holdout():
        raise ValueError("marginal_scarcity_transfer_holdout_invalid")


def _public_relation(pool_id, source):
    return {
        "pool_candidate_id": pool_id,
        "source_object_id": source,
        "target_object_id": "O1",
        "evidence_span_ids": [f"S{int(source[1:]) - 1}"],
    }
