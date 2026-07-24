"""Fresh portfolio-scarcity construction for v0.57."""

from __future__ import annotations

import copy

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "marginal_scarcity_holdout_v0_57"
CORPUS_ID = "local-marginal-scarcity-v0-57"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _scarcity_case(case_id, domain, outcome, labels):
    return _case(
        case_id, domain, f"Resolve the source of {outcome} drift.",
        (outcome, *labels),
        (
            f"Rollback of {labels[0]} removed the initial drift.",
            f"A matched {labels[1]} intervention removed another component.",
            f"Controlled replacement of {labels[2]} removed residual drift.",
            f"Balancing {labels[3]} showed no measurable difference.",
            f"{labels[4]} differs, but no matched test exists.",
            "The first three effects replicated at an independent site.",
        ),
        supported=("O2", "O3", "O4"),
        informative_null=("O5",),
        unresolved=("O6",),
        counterevidence=("S4",),
    )


CASES = (
    _scarcity_case("MS-GRID", "microgrid_dispatch", "frequency", (
        "dispatch policy", "load regime", "inverter controller",
        "meter vendor", "battery age",
    )),
    _scarcity_case("MS-FERMENT", "bioreactor_control", "yield", (
        "feed policy", "oxygen regime", "agitation controller",
        "probe vendor", "vessel age",
    )),
    _scarcity_case("MS-RAIL", "rail_signaling", "headway", (
        "routing policy", "traffic regime", "signal controller",
        "sensor vendor", "fleet age",
    )),
    _scarcity_case("MS-CLOUD", "cloud_scheduler", "latency", (
        "placement policy", "workload regime", "queue controller",
        "server vendor", "cluster age",
    )),
    _scarcity_case("MS-GLASS", "glass_furnace", "thickness", (
        "heating policy", "feed regime", "flow controller",
        "camera vendor", "furnace age",
    )),
    _scarcity_case("MS-STORE", "cold_storage", "energy use", (
        "dispatch policy", "weather regime", "compressor controller",
        "meter vendor", "building age",
    )),
)


def build_marginal_scarcity_holdout():
    items = []
    bindings = {}
    for case in CASES:
        item = _public_item(case)
        item["frozen_active_portfolio"] = [
            _public_relation("BASE:C1", "O2", "O1", ["S1"]),
            _public_relation("BASE:C2", "O3", "O1", ["S2"]),
            _public_relation("BASE:C3", "O6", "O1", ["S5"]),
        ]
        item["active_portfolio_capacity"] = 3
        items.append(item)
        bindings[case["case_id"]] = {
            "public_item_hash": hash_payload(item),
            "primary_object_ids": list(case["primary"]),
            "supported_targets": [
                {"source_object_id": s, "target_object_id": t}
                for s, t in case["supported"]
            ],
            "informative_null_targets": [
                {"source_object_id": s, "target_object_id": t}
                for s, t in case["informative_null"]
            ],
            "unresolved_targets": [
                {"source_object_id": "O6", "target_object_id": "O1"}
            ],
            "hidden_constraint_object_ids": list(case["constraints"]),
            "counterevidence_span_ids": list(case["counterevidence"]),
            "reference_relation_count": 5,
            "reference_is_exhaustive_over_focal_relations": True,
            "designed_drop_pool_id": "BASE:C3",
            "designed_target_relation": {
                "source_object_id": "O4", "target_object_id": "O1",
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
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(items),
        "domain_count": len(items),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {
            **surface, "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_57_CONSTRUCTION_AUDIT_ONLY",
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_marginal_scarcity_construction(corpus):
    validate_marginal_scarcity_holdout(corpus)
    cells = []
    for item in corpus["public_surface"]["items"]:
        binding = corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        active = {
            (value["source_object_id"], value["target_object_id"])
            for value in item["frozen_active_portfolio"]
        }
        target = (
            binding["designed_target_relation"]["source_object_id"],
            binding["designed_target_relation"]["target_object_id"],
        )
        unresolved = {
            (value["source_object_id"], value["target_object_id"])
            for value in binding["unresolved_targets"]
        }
        cells.append({
            "case_id": item["case_id"],
            "active_count": len(active),
            "capacity": item["active_portfolio_capacity"],
            "target_omitted": target not in active,
            "drop_is_unresolved": ("O6", "O1") in unresolved,
            "designed_gross_cbit_uplift": binding[
                "designed_gross_cbit_uplift"
            ],
            "construction_valid": (
                len(active) == item["active_portfolio_capacity"] == 3
                and target not in active
                and ("O6", "O1") in unresolved
                and binding["designed_gross_cbit_uplift"] > 0
            ),
        })
    commitment = {
        "audit_version": "marginal_scarcity_construction_audit_v0_57",
        "source_corpus_hash": corpus["artifact_hash"],
        "cell_count": len(cells),
        "valid_cell_count": sum(
            value["construction_valid"] for value in cells
        ),
        "minimum_designed_gross_cbit_uplift": min(
            value["designed_gross_cbit_uplift"] for value in cells
        ),
        "cells": cells,
        "provider_calls_added": 0,
        "formal_experiment_authorized": False,
        "private_target_available_to_provider": False,
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_marginal_scarcity_holdout(value):
    if value != build_marginal_scarcity_holdout():
        raise ValueError("marginal_scarcity_holdout_invalid")


def _public_relation(pool_id, source, target, spans):
    return {
        "pool_candidate_id": pool_id,
        "source_object_id": source,
        "target_object_id": target,
        "evidence_span_ids": list(spans),
    }
