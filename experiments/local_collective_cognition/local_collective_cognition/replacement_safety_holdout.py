"""Fresh holdout for compact-delta replacement safety v0.43."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "replacement_safety_holdout_v0_43"
CORPUS_ID = "local-replacement-safety-v0-43"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id, domain, goal, labels, texts, supported,
    informative_null, constraints, counterevidence,
):
    return {
        "case_id": case_id,
        "domain": domain,
        "research_goal": goal,
        "objects": tuple(
            (f"O{index}", label)
            for index, label in enumerate(labels, 1)
        ),
        "spans": tuple(
            (f"S{index}", text)
            for index, text in enumerate(texts, 1)
        ),
        "primary": ("O1",),
        "supported": tuple(supported),
        "informative_null": tuple(informative_null),
        "constraints": tuple(constraints),
        "counterevidence": tuple(counterevidence),
    }


CASES = (
    _case(
        "RS-WATER", "water_treatment",
        "Resolve the source of residual-estimate drift.",
        ("residual drift", "backwash schedule", "turbidity load",
         "membrane supplier", "calibration gap", "probe age"),
        ("Residual drift began after the backwash schedule update.",
         "Turbidity loads rose during the affected windows.",
         "Membrane suppliers are balanced across trains.",
         "Calibration logs are absent for several shifts.",
         "Probe ages vary between treatment trains.",
         "The old schedule reduces drift at matched turbidity.",
         "Supplier-matched trains retain the turbidity effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RS-HOSPITAL", "hospital_operations",
        "Resolve the source of wait-time forecast drift.",
        ("wait-time drift", "triage protocol", "arrival acuity",
         "platform vendor", "timestamp reconciliation", "scanner age"),
        ("Forecast drift followed the triage protocol revision.",
         "Arrival acuity changed, but only on two wards.",
         "Platform vendors are balanced across wards.",
         "Raw timestamps disagree with exported queue events.",
         "Scanner ages differ without matching the drift pattern.",
         "Reconciled timestamps remove drift within protocol strata.",
         "Vendor-matched wards preserve the timestamp discrepancy."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "RS-SATELLITE", "satellite_telemetry",
        "Resolve the source of orbit-residual drift.",
        ("orbit residual drift", "filter update", "thermal cycle",
         "component batch", "telemetry gap", "oscillator age"),
        ("Residuals changed immediately after the filter update.",
         "Thermal cycles align with the largest residual excursions.",
         "Component batches are mixed across affected spacecraft.",
         "Telemetry gaps obscure two maneuvers.",
         "Oscillator age was proposed as a cause.",
         "Matched-age spacecraft show no oscillator-age effect.",
         "Old-filter replay reduces residuals at matched temperature."),
        (("O2", "O1"), ("O3", "O1")),
        (("O6", "O1"),), ("O4", "O5"), ("S3", "S4", "S5", "S6"),
    ),
    _case(
        "RS-COLD", "cold_chain",
        "Resolve the source of excursion-risk drift.",
        ("risk drift", "loading policy", "door-open pattern",
         "logger vendor", "handoff lag", "battery age"),
        ("The loading policy changed before the drift appeared.",
         "Policy reversion alone does not remove the drift.",
         "Door-open bursts precede the affected intervals.",
         "Logger vendors are balanced across routes.",
         "Handoff records lag the physical transfer by hours.",
         "Correcting handoff lag removes residual route drift.",
         "Battery age differs, but matched-age routes still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "RS-BRIDGE", "bridge_monitoring",
        "Resolve the source of strain-baseline drift.",
        ("strain drift", "filter policy", "thermal gradient",
         "sensor vendor", "maintenance gap", "adhesive age"),
        ("Drift began after the filter policy deployment.",
         "Thermal gradients explain only daytime excursions.",
         "Sensor vendors are balanced across spans.",
         "Maintenance records omit two recalibrations.",
         "Adhesive age does not track drift across spans.",
         "Coupon tests show aged adhesive shifts strain response.",
         "Old-filter replay reduces drift outside thermal peaks."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "RS-ALGAE", "algae_cultivation",
        "Resolve the source of biomass-estimate drift.",
        ("biomass drift", "lighting schedule", "nutrient pulse",
         "reactor supplier", "sampling lag", "sensor age"),
        ("Biomass drift followed the lighting schedule change.",
         "Nutrient pulses shifted in the same week.",
         "Reactor suppliers are mixed across affected lines.",
         "Old-schedule replay removes drift at matched nutrients.",
         "Sampling lag was proposed but complete logs show no effect.",
         "Sensor ages vary across lines.",
         "Supplier-matched reactors preserve the nutrient response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "RS-RAIL", "rail_signaling",
        "Resolve the source of braking-margin drift.",
        ("margin drift", "control-table revision", "traffic density",
         "interlocking vendor", "event-order lag", "relay age"),
        ("Margin drift followed the control-table revision.",
         "Traffic density changed only after drift was established.",
         "Interlocking vendors are balanced across sectors.",
         "Event exports reverse two command timestamps.",
         "Relay ages differ but do not align with affected sectors.",
         "Correct event ordering removes the residual margin drift.",
         "Old-table replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "RS-BATTERY", "battery_recycling",
        "Resolve the source of recovery-score drift.",
        ("recovery drift", "sorting policy", "feed chemistry",
         "assay vendor", "queue delay", "fixture wear"),
        ("Sorting policy changed, but replay gives mixed results.",
         "Feed chemistry shifts precede every high-drift batch.",
         "Assay vendors are balanced across plants.",
         "Queue delay affects freshness but not recovery residuals.",
         "Fixture wear differs substantially across plants.",
         "Matched-chemistry tests retain the fixture-wear effect.",
         "Vendor-matched assays preserve the chemistry effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S3", "S4", "S7"),
    ),
)


def build_replacement_safety_holdout():
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
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_43_FROZEN_BEFORE_REPLACEMENT_SAFETY_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_replacement_safety_holdout(artifact):
    if artifact != build_replacement_safety_holdout():
        raise ValueError("replacement_safety_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"],
        "domain": value["domain"],
        "research_goal": value["research_goal"],
        "focal_object_id": value["primary"][0],
        "object_registry": [
            {"object_id": object_id, "label": label}
            for object_id, label in value["objects"]
        ],
        "evidence_spans": [
            {
                "span_id": span_id,
                "text": text,
                "text_hash": hash_payload(text),
            }
            for span_id, text in value["spans"]
        ],
    }
