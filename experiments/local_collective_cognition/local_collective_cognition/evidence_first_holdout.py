"""Fresh rotated holdout for evidence-first arbitration v0.54."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "evidence_first_holdout_v0_54"
CORPUS_ID = "local-evidence-first-v0-54"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


CASES = (
    _case(
        "EF-SOLAR", "solar_farm_control",
        "Resolve the source of yield-estimate drift.",
        (
            "yield drift", "tracking policy", "irradiance regime",
            "inverter vendor", "cleaning protocol", "panel age",
        ),
        (
            "Tracking-policy rollback removed the initial drift.",
            "A matched irradiance intervention removed residual drift.",
            "Inverter-vendor balancing showed no estimate difference.",
            "Cleaning-protocol replay showed no effect.",
            "Panel ages differ, but no age-matched trial exists.",
            "Tracking and irradiance effects replicated at another farm.",
        ),
        supported=("O2", "O3"),
        informative_null=("O4", "O5"),
        unresolved=("O6",),
        counterevidence=("S3", "S4"),
    ),
    _case(
        "EF-DAIRY", "dairy_processing",
        "Resolve the source of separation-time drift.",
        (
            "separation drift", "feed policy", "fat regime",
            "sensor vendor", "chilling protocol", "separator age",
        ),
        (
            "Feed-policy rollback left separation drift unchanged.",
            "A matched fat-regime intervention removed initial drift.",
            "Sensor-vendor balancing and swaps showed no difference.",
            "Chilling-protocol crossover removed residual drift.",
            "Separator ages differ, but no age-matched test exists.",
            "Fat and chilling effects replicated on another line.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "EF-AIR", "airport_ground_control",
        "Resolve the source of turnaround-time drift.",
        (
            "turnaround drift", "gate policy", "traffic regime",
            "scanner vendor", "handoff protocol", "fleet age",
        ),
        (
            "Gate-policy rollback showed no turnaround change.",
            "A matched traffic-regime intervention removed initial drift.",
            "Scanner vendors differ, but no balanced swap was run.",
            "Handoff-protocol rollback removed residual drift.",
            "Fleet-age matching showed no turnaround difference.",
            "Traffic and handoff effects replicated at another airport.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O6"),
        unresolved=("O4",),
        counterevidence=("S1", "S5"),
    ),
    _case(
        "EF-MINE", "mineral_processing",
        "Resolve the source of recovery-rate drift.",
        (
            "recovery drift", "crusher policy", "ore regime",
            "camera vendor", "flotation protocol", "plant age",
        ),
        (
            "Crusher-policy rollback removed the initial drift.",
            "Ore-regime balancing showed no recovery difference.",
            "Camera-vendor balancing and swaps showed no effect.",
            "Flotation-protocol crossover removed residual drift.",
            "Plant ages differ, but no age-matched trial exists.",
            "Crusher and flotation effects replicated at another site.",
        ),
        supported=("O2", "O5"),
        informative_null=("O3", "O4"),
        unresolved=("O6",),
        counterevidence=("S2", "S3"),
    ),
    _case(
        "EF-CLAIM", "insurance_claims",
        "Resolve the source of settlement-time drift.",
        (
            "settlement drift", "routing policy", "claim regime",
            "data vendor", "review protocol", "portfolio age",
        ),
        (
            "Routing-policy rollback left settlement drift unchanged.",
            "A matched claim-regime intervention removed initial drift.",
            "Data-vendor balancing and swaps showed no difference.",
            "Review-protocol rollback removed residual drift.",
            "Portfolio ages differ, but no matched replay exists.",
            "Claim and review effects replicated in another region.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "EF-PACK", "parcel_sorting",
        "Resolve the source of sorting-error drift.",
        (
            "sorting drift", "queue policy", "parcel regime",
            "camera vendor", "retry protocol", "belt age",
        ),
        (
            "Queue-policy rollback removed initial drift.",
            "Parcel-regime balancing showed no sorting difference.",
            "Camera vendors differ, but no balanced swap was run.",
            "Retry-protocol crossover removed residual drift.",
            "Belt-age matching showed no error difference.",
            "Queue and retry effects replicated at another hub.",
        ),
        supported=("O2", "O5"),
        informative_null=("O3", "O6"),
        unresolved=("O4",),
        counterevidence=("S2", "S5"),
    ),
    _case(
        "EF-HEAT", "district_heating",
        "Resolve the source of demand-estimate drift.",
        (
            "demand drift", "dispatch policy", "weather regime",
            "meter vendor", "balancing protocol", "network age",
        ),
        (
            "Dispatch-policy rollback showed no demand-estimate change.",
            "A matched weather-regime intervention removed initial drift.",
            "Meter-vendor balancing and swaps showed no difference.",
            "Balancing-protocol rollback removed residual drift.",
            "Network ages differ, but no age-matched test exists.",
            "Weather and balancing effects replicated in another district.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "EF-NET", "content_delivery_network",
        "Resolve the source of cache-hit drift.",
        (
            "cache drift", "routing policy", "traffic regime",
            "server vendor", "refresh protocol", "cluster age",
        ),
        (
            "Routing-policy rollback removed initial drift.",
            "A matched traffic-regime intervention removed residual drift.",
            "Server-vendor balancing and swaps showed no difference.",
            "Refresh-protocol replay showed no cache-hit effect.",
            "Cluster ages differ, but no age-matched replay exists.",
            "Routing and traffic effects replicated in another region.",
        ),
        supported=("O2", "O3"),
        informative_null=("O4", "O5"),
        unresolved=("O6",),
        counterevidence=("S3", "S4"),
    ),
)


def build_evidence_first_holdout():
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
            "FRESH_V0_54_PENDING_DUAL_PROVIDER_COMPLETENESS_AUDIT"
        ),
        "prior_holdout_labels_reused": False,
        "relation_state_positions_rotated_across_cases": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_evidence_first_holdout(artifact):
    if artifact != build_evidence_first_holdout():
        raise ValueError("evidence_first_holdout_invalid")
