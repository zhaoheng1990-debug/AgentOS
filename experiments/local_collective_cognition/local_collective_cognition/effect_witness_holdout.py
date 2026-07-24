"""Fresh EFFECT-rich holdout for v0.56."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .selective_rejection_holdout import _case, _public_item


CORPUS_VERSION = "effect_witness_holdout_v0_56"
CORPUS_ID = "local-effect-witness-v0-56"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _effect_case(case_id, domain, outcome, labels):
    return _case(
        case_id,
        domain,
        f"Resolve the source of {outcome} drift.",
        (outcome, *labels),
        (
            f"Rollback of {labels[0]} removed one component of drift.",
            f"A matched {labels[1]} intervention removed a second component.",
            f"Controlled replacement of {labels[2]} removed residual drift.",
            f"A crossover of {labels[3]} removed a separate residual.",
            f"Balancing {labels[4]} showed no measurable difference.",
            "All four positive effects replicated at an independent site.",
        ),
        supported=("O2", "O3", "O4", "O5"),
        informative_null=("O6",),
        unresolved=(),
        counterevidence=("S5",),
    )


CASES = (
    _effect_case(
        "EW-WATER", "desalination_control", "membrane yield",
        (
            "pressure policy", "salinity regime", "pump controller",
            "flush protocol", "membrane age",
        ),
    ),
    _effect_case(
        "EW-ORBIT", "satellite_attitude_control", "pointing error",
        (
            "slew policy", "thermal regime", "wheel controller",
            "calibration protocol", "bus age",
        ),
    ),
    _effect_case(
        "EW-COLD", "vaccine_cold_chain", "temperature excursion",
        (
            "routing policy", "load regime", "logger controller",
            "handoff protocol", "container age",
        ),
    ),
    _effect_case(
        "EW-ETCH", "semiconductor_etch", "etch-depth",
        (
            "recipe policy", "plasma regime", "flow controller",
            "cleaning protocol", "chamber age",
        ),
    ),
    _effect_case(
        "EW-PORT", "container_port", "crane cycle-time",
        (
            "dispatch policy", "traffic regime", "vision controller",
            "handoff protocol", "crane age",
        ),
    ),
    _effect_case(
        "EW-CELL", "battery_recycling", "recovery yield",
        (
            "sorting policy", "feed regime", "sensor controller",
            "leaching protocol", "reactor age",
        ),
    ),
)


def build_effect_witness_holdout():
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
        "domain_count": len(CASES),
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
            "FRESH_V0_56_PENDING_DUAL_PROVIDER_COMPLETENESS_AUDIT"
        ),
        "prior_holdout_labels_reused": False,
        "effect_rich_construction_frozen_before_inference": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_effect_witness_holdout(artifact):
    if artifact != build_effect_witness_holdout():
        raise ValueError("effect_witness_holdout_invalid")
