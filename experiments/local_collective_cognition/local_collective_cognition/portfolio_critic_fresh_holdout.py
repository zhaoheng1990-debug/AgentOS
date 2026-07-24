"""Fresh three-topology PortfolioCritic holdout v0.61."""

from __future__ import annotations

import copy
from collections import Counter

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "portfolio_critic_fresh_holdout_v0_61"
CORPUS_ID = "local-portfolio-critic-fresh-v0-61"
REPAIR_VERSION = "portfolio_critic_fresh_holdout_v0_61_1"
REPAIR_ID = "local-portfolio-critic-fresh-v0-61-1"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")
TOPOLOGIES = (
    "UNIQUE_UNRESOLVED",
    "NO_UNRESOLVED",
    "MULTIPLE_UNRESOLVED",
)


def _spec(
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
    topology,
):
    case = _case(
        case_id,
        domain,
        f"Resolve the source of {outcome} drift.",
        (outcome, *labels),
        spans,
        supported=supported,
        informative_null=informative_null,
        unresolved=unresolved,
        counterevidence=tuple(
            f"S{int(value[1:]) - 1}" for value in informative_null
        ),
    )
    return {
        "case": case,
        "target": target,
        "active": active,
        "topology": topology,
    }


CASES = (
    _spec(
        "PC-AQUA",
        "recirculating_aquaculture",
        "oxygen stability",
        (
            "feed schedule",
            "tank coating",
            "aeration controller",
            "sensor supplier",
            "circulation policy",
        ),
        (
            "A matched feed-schedule intervention removed one component "
            "of oxygen-stability drift.",
            "Tank-coating swaps showed no measurable oxygen difference.",
            "Aeration-controller replacement removed another drift component.",
            "Sensor suppliers differ. No intervention or matched comparison "
            "has tested whether supplier changes oxygen stability; the "
            "effect is neither supported nor ruled out.",
            "A circulation-policy crossover removed residual oxygen drift.",
            "The schedule, controller, and circulation effects replicated.",
        ),
        supported=("O2", "O4", "O6"),
        informative_null=("O3",),
        unresolved=("O5",),
        target="O2",
        active=(("BASE:C1", "O4"), ("BASE:C3", "O5"), ("BASE:C2", "O6")),
        topology="UNIQUE_UNRESOLVED",
    ),
    _spec(
        "PC-PRINT",
        "metal_additive_manufacturing",
        "porosity",
        (
            "powder handling",
            "chamber age",
            "scan firmware",
            "gas-flow policy",
            "camera supplier",
        ),
        (
            "Powder-handling rollback removed one component of porosity drift.",
            "Chamber ages differ. No matched build has tested whether age "
            "changes porosity; the effect is neither supported nor ruled out.",
            "Randomized scan-firmware rollback removed another component.",
            "A gas-flow policy crossover removed residual porosity drift.",
            "Camera-supplier balancing showed no measurable difference.",
            "Handling, firmware, and gas-flow effects replicated on a new rig.",
        ),
        supported=("O2", "O4", "O5"),
        informative_null=("O6",),
        unresolved=("O3",),
        target="O5",
        active=(("BASE:C1", "O3"), ("BASE:C2", "O2"), ("BASE:C3", "O4")),
        topology="UNIQUE_UNRESOLVED",
    ),
    _spec(
        "PC-TRAFFIC",
        "adaptive_traffic_signals",
        "corridor delay",
        (
            "timing policy",
            "demand regime",
            "detector firmware",
            "camera supplier",
            "priority protocol",
        ),
        (
            "Timing-policy rollback removed one component of delay drift.",
            "A matched demand-regime intervention removed another component.",
            "Detector-firmware replacement removed residual corridor drift.",
            "Camera-supplier balancing showed no measurable delay difference.",
            "A priority-protocol crossover removed an independent component.",
            "All four supported effects replicated on a second corridor.",
        ),
        supported=("O2", "O3", "O4", "O6"),
        informative_null=("O5",),
        unresolved=(),
        target="O3",
        active=(("BASE:C3", "O2"), ("BASE:C1", "O4"), ("BASE:C2", "O6")),
        topology="NO_UNRESOLVED",
    ),
    _spec(
        "PC-GENOME",
        "clinical_genomics_pipeline",
        "variant concordance",
        (
            "library supplier",
            "alignment policy",
            "caller firmware",
            "coverage regime",
            "review protocol",
        ),
        (
            "Library-supplier balancing showed no concordance difference.",
            "Alignment-policy rollback removed one component of drift.",
            "Caller-firmware replacement removed another component.",
            "A matched coverage intervention removed residual drift.",
            "Review-protocol crossover removed an independent component.",
            "All four supported effects replicated on a second dataset.",
        ),
        supported=("O3", "O4", "O5", "O6"),
        informative_null=("O2",),
        unresolved=(),
        target="O4",
        active=(("BASE:C1", "O3"), ("BASE:C2", "O5"), ("BASE:C3", "O6")),
        topology="NO_UNRESOLVED",
    ),
    _spec(
        "PC-HVAC",
        "district_hvac_control",
        "thermal variance",
        (
            "building age",
            "meter supplier",
            "weather regime",
            "dispatch policy",
            "valve controller",
        ),
        (
            "Building ages differ. No intervention or matched comparison has "
            "tested whether age changes thermal variance; the effect is "
            "neither supported nor ruled out.",
            "Meter-supplier balancing showed no measurable variance difference.",
            "Weather regimes differ. No matched intervention has tested "
            "whether regime changes thermal variance; the effect is neither "
            "supported nor ruled out.",
            "Dispatch-policy rollback removed one component of variance drift.",
            "Valve-controller replacement removed residual thermal drift.",
            "The dispatch and controller effects replicated in another block.",
        ),
        supported=("O5", "O6"),
        informative_null=("O3",),
        unresolved=("O2", "O4"),
        target="O6",
        active=(("BASE:C2", "O5"), ("BASE:C1", "O2"), ("BASE:C3", "O4")),
        topology="MULTIPLE_UNRESOLVED",
    ),
    _spec(
        "PC-ROBOT",
        "robot_assisted_surgery",
        "trajectory error",
        (
            "calibration policy",
            "instrument age",
            "display supplier",
            "motion firmware",
            "staffing regime",
        ),
        (
            "Calibration-policy rollback removed one trajectory-drift component.",
            "Instrument ages differ. No matched procedure has tested whether "
            "age changes trajectory error; the effect is neither supported "
            "nor ruled out.",
            "Display-supplier balancing showed no measurable error difference.",
            "Motion-firmware replacement removed residual trajectory drift.",
            "Staffing regimes differ. No matched procedure has tested whether "
            "staffing changes trajectory error; the effect is neither "
            "supported nor ruled out.",
            "The calibration and firmware effects replicated on a simulator.",
        ),
        supported=("O2", "O5"),
        informative_null=("O4",),
        unresolved=("O3", "O6"),
        target="O5",
        active=(("BASE:C3", "O2"), ("BASE:C2", "O3"), ("BASE:C1", "O6")),
        topology="MULTIPLE_UNRESOLVED",
    ),
)


def build_portfolio_critic_fresh_holdout():
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
        supported_sources = {
            source for source, _target in case["supported"]
        }
        unresolved_sources = set(case["constraints"])
        active_by_pool = dict(specification["active"])
        protected = [
            pool_id for pool_id, source in specification["active"]
            if source in supported_sources
        ]
        eligible = [
            pool_id for pool_id, source in specification["active"]
            if source in unresolved_sources
        ]
        expected_action = {
            "UNIQUE_UNRESOLVED": "REPLACE_UNIQUE_UNRESOLVED",
            "NO_UNRESOLVED": "ABSTAIN_NO_ELIGIBLE",
            "MULTIPLE_UNRESOLVED": "ABSTAIN_AMBIGUOUS_ELIGIBLE",
        }[specification["topology"]]
        bindings[case["case_id"]] = {
            "public_item_hash": hash_payload(item),
            "primary_object_ids": list(case["primary"]),
            "supported_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in case["supported"]
            ],
            "informative_null_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in case["informative_null"]
            ],
            "unresolved_targets": [
                {"source_object_id": source, "target_object_id": "O1"}
                for source in case["constraints"]
            ],
            "hidden_constraint_object_ids": list(case["constraints"]),
            "counterevidence_span_ids": list(case["counterevidence"]),
            "reference_relation_count": 5,
            "reference_is_exhaustive_over_focal_relations": True,
            "topology": specification["topology"],
            "expected_kernel_action": expected_action,
            "eligible_pool_ids": eligible,
            "protected_pool_ids": protected,
            "designed_drop_pool_id": (
                eligible[0] if len(eligible) == 1 else None
            ),
            "active_source_by_pool": active_by_pool,
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
        "topology_labels_exposed": False,
        "expected_actions_exposed": False,
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
        "reference_state": "FRESH_V0_61_CONSTRUCTION_AUDIT_ONLY",
        "prior_holdout_labels_reused": False,
        "target_source_positions_rotated_across_cases": True,
        "topologies_balanced_across_cases": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_portfolio_critic_fresh_holdout(corpus):
    validate_portfolio_critic_fresh_holdout(corpus)
    return _audit_fresh_holdout(
        corpus,
        audit_version="portfolio_critic_fresh_audit_v0_61",
    )


def build_portfolio_critic_fresh_holdout_v0_61_1():
    original = build_portfolio_critic_fresh_holdout()
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
        ("PC-TRAFFIC", "S2"): (
            "A matched demand-regime intervention removed an independently "
            "measured component of corridor-delay drift."
        ),
        ("PC-GENOME", "S3"): (
            "Caller-firmware replacement removed an independently measured "
            "component of variant-concordance drift."
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
        "V0_61_1_CONSTRUCTION_REPAIR_AUDIT_ONLY"
    )
    commitment["prior_holdout_labels_reused"] = True
    commitment["repair_reuses_failed_construction_cases"] = True
    commitment["formal_discovery_labels_previously_exposed"] = False
    commitment["source_failed_corpus_hash"] = original["artifact_hash"]
    commitment["construction_repairs"] = [
        {
            "case_id": case_id,
            "span_id": span_id,
            "repair_kind": "FOCAL_OUTCOME_BINDING",
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


def audit_portfolio_critic_fresh_holdout_v0_61_1(corpus):
    validate_portfolio_critic_fresh_holdout_v0_61_1(corpus)
    return _audit_fresh_holdout(
        corpus,
        audit_version="portfolio_critic_fresh_audit_v0_61_1",
    )


def validate_portfolio_critic_fresh_holdout_v0_61_1(value):
    if value != build_portfolio_critic_fresh_holdout_v0_61_1():
        raise ValueError("portfolio_critic_fresh_holdout_v0_61_1_invalid")


def _audit_fresh_holdout(corpus, *, audit_version):
    topology_counts = Counter()
    target_positions = Counter()
    cells = []
    for item in corpus["public_surface"]["items"]:
        binding = corpus["private_provenance"]["bindings"][item["case_id"]]
        active_pools = {
            value["pool_candidate_id"]
            for value in item["frozen_active_portfolio"]
        }
        target_source = binding["designed_target_relation"][
            "source_object_id"
        ]
        active_sources = {
            value["source_object_id"]
            for value in item["frozen_active_portfolio"]
        }
        eligible = set(binding["eligible_pool_ids"])
        protected = set(binding["protected_pool_ids"])
        topology = binding["topology"]
        expected_eligible = {
            "UNIQUE_UNRESOLVED": 1,
            "NO_UNRESOLVED": 0,
            "MULTIPLE_UNRESOLVED": 2,
        }[topology]
        valid = (
            len(active_pools) == item["active_portfolio_capacity"] == 3
            and target_source not in active_sources
            and len(eligible) == expected_eligible
            and not eligible.intersection(protected)
            and eligible.union(protected) == active_pools
        )
        topology_counts[topology] += 1
        target_positions[target_source] += 1
        cells.append({
            "case_id": item["case_id"],
            "topology": topology,
            "target_source_object_id": target_source,
            "eligible_pool_ids": sorted(eligible),
            "protected_pool_ids": sorted(protected),
            "construction_valid": valid,
        })
    commitment = {
        "audit_version": audit_version,
        "source_corpus_hash": corpus["artifact_hash"],
        "cell_count": len(cells),
        "valid_cell_count": sum(value["construction_valid"] for value in cells),
        "topology_counts": dict(sorted(topology_counts.items())),
        "topology_balance_valid": set(topology_counts.values()) == {2},
        "target_position_counts": dict(sorted(target_positions.items())),
        "target_position_coverage": len(target_positions),
        "cells": cells,
        "provider_calls_added": 0,
        "formal_experiment_authorized": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_portfolio_critic_fresh_holdout(value):
    if value != build_portfolio_critic_fresh_holdout():
        raise ValueError("portfolio_critic_fresh_holdout_invalid")


def _public_relation(pool_id, source):
    return {
        "pool_candidate_id": pool_id,
        "source_object_id": source,
        "target_object_id": "O1",
        "evidence_span_ids": [f"S{int(source[1:]) - 1}"],
    }
