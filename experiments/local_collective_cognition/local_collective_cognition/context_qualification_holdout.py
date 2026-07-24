"""Fresh rotated holdout for context qualification v0.53."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "context_qualification_holdout_v0_53"
CORPUS_ID = "local-context-qualification-v0-53"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


CASES = (
    _case(
        "CQ-WIND", "wind_farm_control",
        "Resolve the source of power-forecast drift.",
        (
            "forecast drift", "yaw policy", "wake regime",
            "anemometer vendor", "curtailment protocol", "blade age",
        ),
        (
            "Randomized yaw-policy rollback removed the initial drift.",
            "A matched wake-regime intervention removed residual error.",
            "Anemometer-vendor balancing and swaps showed no difference.",
            "Curtailment-protocol replay showed no forecast effect.",
            "Blade ages differ, but no age-matched intervention exists.",
            "Yaw and wake effects replicated at an independent farm.",
        ),
        supported=("O2", "O3"),
        informative_null=("O4", "O5"),
        unresolved=("O6",),
        counterevidence=("S3", "S4"),
    ),
    _case(
        "CQ-BAKE", "industrial_bakery",
        "Resolve the source of fermentation-time drift.",
        (
            "fermentation drift", "mixing policy", "flour regime",
            "sensor vendor", "proofing protocol", "oven age",
        ),
        (
            "Mixing-policy rollback left fermentation drift unchanged.",
            "A matched flour-regime intervention removed the initial drift.",
            "Sensor-vendor balancing and swaps showed no timing difference.",
            "Randomized proofing-protocol rollback removed residual drift.",
            "Oven ages differ, but no age-matched test has been run.",
            "Flour and proofing effects replicated on another line.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "CQ-RAIL", "freight_rail",
        "Resolve the source of braking-distance drift.",
        (
            "braking drift", "dispatch policy", "load regime",
            "pad vendor", "control firmware", "wagon age",
        ),
        (
            "Dispatch-policy rollback showed no braking-distance change.",
            "A matched load-regime intervention removed the initial drift.",
            "Pad vendors differ, but no vendor-balanced swap was run.",
            "Randomized control-firmware rollback removed residual drift.",
            "Wagon-age matching showed no braking difference.",
            "Load and firmware effects replicated on a second route.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O6"),
        unresolved=("O4",),
        counterevidence=("S1", "S5"),
    ),
    _case(
        "CQ-DATA", "database_platform",
        "Resolve the source of query-latency drift.",
        (
            "latency drift", "cache policy", "query regime",
            "storage vendor", "retry firmware", "cluster age",
        ),
        (
            "Randomized cache-policy rollback removed the initial drift.",
            "Query-regime balancing showed no latency difference.",
            "Storage-vendor balancing and swaps showed no effect.",
            "Retry-firmware rollback removed residual latency drift.",
            "Cluster ages differ, but no age-matched replay exists.",
            "Cache and firmware effects replicated in another region.",
        ),
        supported=("O2", "O5"),
        informative_null=("O3", "O4"),
        unresolved=("O6",),
        counterevidence=("S2", "S3"),
    ),
    _case(
        "CQ-WATER", "water_treatment",
        "Resolve the source of filtration-yield drift.",
        (
            "yield drift", "backwash policy", "inflow regime",
            "membrane vendor", "sampling protocol", "plant age",
        ),
        (
            "Backwash-policy rollback left yield drift unchanged.",
            "A matched inflow-regime intervention removed initial drift.",
            "Membrane-vendor balancing and swaps showed no difference.",
            "Sampling-protocol crossover removed residual drift.",
            "Plant ages differ, but no age-matched trial exists.",
            "Inflow and sampling effects replicated at another plant.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "CQ-PRINT", "additive_manufacturing",
        "Resolve the source of dimensional-error drift.",
        (
            "dimension drift", "scan policy", "powder regime",
            "laser vendor", "cooling protocol", "machine age",
        ),
        (
            "Randomized scan-policy rollback removed initial drift.",
            "Powder-regime balancing showed no dimensional difference.",
            "Laser vendors differ, but no balanced swap was run.",
            "A cooling-protocol crossover removed residual error.",
            "Machine-age matching showed no error difference.",
            "Scan and cooling effects replicated on a second machine.",
        ),
        supported=("O2", "O5"),
        informative_null=("O3", "O6"),
        unresolved=("O4",),
        counterevidence=("S2", "S5"),
    ),
    _case(
        "CQ-CALL", "contact_center",
        "Resolve the source of demand-forecast drift.",
        (
            "demand drift", "staffing policy", "campaign regime",
            "telephony vendor", "handoff protocol", "site age",
        ),
        (
            "Staffing-policy rollback showed no demand-forecast change.",
            "A matched campaign-regime intervention removed initial drift.",
            "Telephony-vendor balancing and swaps showed no difference.",
            "Randomized handoff-protocol rollback removed residual drift.",
            "Site ages differ, but no age-matched comparison exists.",
            "Campaign and handoff effects replicated at another site.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "CQ-COLD", "cold_chain_logistics",
        "Resolve the source of temperature-estimate drift.",
        (
            "temperature drift", "routing policy", "cargo regime",
            "logger vendor", "defrost protocol", "container age",
        ),
        (
            "Randomized routing-policy rollback removed initial drift.",
            "A matched cargo-regime intervention removed residual drift.",
            "Logger-vendor balancing and swaps showed no difference.",
            "Defrost-protocol replay showed no estimate effect.",
            "Container ages differ, but no age-matched trial exists.",
            "Routing and cargo effects replicated across depots.",
        ),
        supported=("O2", "O3"),
        informative_null=("O4", "O5"),
        unresolved=("O6",),
        counterevidence=("S3", "S4"),
    ),
)


def build_context_qualification_holdout():
    items = [_public_item(value) for value in CASES]
    items.sort(key=lambda value: hash_payload(
        [CORPUS_VERSION, value["case_id"]]
    ))
    bindings = {
        value["case_id"]: {
            "public_item_hash": hash_payload(_public_item(value)),
            "primary_object_ids": list(value["primary"]),
            "supported_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in value["supported"]
            ],
            "informative_null_targets": [
                {"source_object_id": source, "target_object_id": target}
                for source, target in value["informative_null"]
            ],
            "hidden_constraint_object_ids": list(value["constraints"]),
            "counterevidence_span_ids": list(value["counterevidence"]),
            "reference_relation_count": 5,
            "reference_is_exhaustive_over_focal_relations": True,
        }
        for value in CASES
    }
    surface = {
        "surface_version": CORPUS_VERSION,
        "items": items,
        "private_outcomes_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(CASES),
        "domain_count": len({value["domain"] for value in CASES}),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {
            **surface, "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_EXHAUSTIVE_FOCAL_RELATIONS",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_53_PENDING_DUAL_PROVIDER_COMPLETENESS_AUDIT"
        ),
        "prior_holdout_labels_reused": False,
        "relation_state_positions_rotated_across_cases": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_context_qualification_holdout(artifact):
    if artifact != build_context_qualification_holdout():
        raise ValueError("context_qualification_holdout_invalid")
