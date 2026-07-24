"""Fresh holdout for warrant-complete review replication v0.49."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "warrant_complete_holdout_v0_49"
CORPUS_ID = "local-warrant-complete-v0-49"
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
        "WC-WIND", "wind_turbine_control",
        "Resolve the source of power-conversion drift.",
        ("conversion drift", "pitch policy", "gust regime",
         "sensor supplier", "telemetry lag", "gearbox age"),
        ("Conversion drift followed the pitch-policy update.",
         "Gust regimes precede high-drift intervals.",
         "Sensor suppliers are balanced across turbine groups.",
         "Telemetry exports omit two clock corrections.",
         "Gearbox age differs without tracking conversion drift.",
         "Old-policy replay removes matched-wind drift.",
         "Supplier-matched turbines preserve the gust response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "WC-WARD", "hospital_bed_flow",
        "Resolve the source of discharge-time drift.",
        ("discharge drift", "triage policy", "case mix",
         "software vendor", "recording lag", "ward age"),
        ("Discharge drift followed the triage-policy revision.",
         "Case mix changed after the first drift interval.",
         "Software vendors are balanced across wards.",
         "Record exports reverse several handoff times.",
         "Ward age varies without matching discharge drift.",
         "Correcting event order removes residual drift.",
         "Old-policy replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "WC-COLD", "cold_chain_logistics",
        "Resolve the source of temperature-excursion drift.",
        ("excursion drift", "routing policy", "load pattern",
         "logger vendor", "scan lag", "container age"),
        ("Routing policy changed before excursion drift.",
         "Policy replay leaves mixed temperature residuals.",
         "Load patterns precede every high-drift route.",
         "Logger vendors are balanced across depots.",
         "Scan lag does not align with excursion drift.",
         "Older containers retain bias at matched load.",
         "Vendor-matched routes preserve the load response."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "WC-WATER", "water_treatment",
        "Resolve the source of filtration-score drift.",
        ("filtration drift", "dosing update", "inflow mix",
         "membrane vendor", "sample lag", "filter age"),
        ("Drift followed the dosing update.",
         "Inflow mix changed after drift was established.",
         "Membrane vendors are balanced across trains.",
         "Sample exports misorder several treatment steps.",
         "Filter ages differ but do not match affected trains.",
         "Correcting event order removes residual drift.",
         "Old-dose replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "WC-ROBOT", "warehouse_robotics",
        "Resolve the source of pick-cycle drift.",
        ("cycle drift", "dispatch policy", "aisle congestion",
         "camera vendor", "handoff lag", "battery age"),
        ("Dispatch policy changed before cycle drift.",
         "Policy replay does not explain congested-aisle residuals.",
         "Aisle congestion precedes normal-load drift.",
         "Camera vendors are balanced across zones.",
         "Handoff reports lag robot logs by seven minutes.",
         "Handoff correction removes congested-aisle residual drift.",
         "Battery age varies but matched-age zones still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "WC-FOREST", "forest_fire_monitoring",
        "Resolve the source of ignition-risk drift.",
        ("risk drift", "alert policy", "wind exposure",
         "sensor vendor", "maintenance lag", "tower age"),
        ("Drift followed the alert-policy update.",
         "Wind exposure explains only afternoon errors.",
         "Sensor vendors are balanced across monitoring blocks.",
         "Maintenance logs omit two sensor replacements.",
         "Tower age was proposed but block matching weakens it.",
         "Bench tests show aged towers do not alter risk scores.",
         "Old-policy replay reduces drift outside afternoon periods."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S2", "S3", "S4", "S6"),
    ),
    _case(
        "WC-RAIL", "rail_switch_control",
        "Resolve the source of switch-latency drift.",
        ("latency drift", "control schedule", "traffic cycle",
         "actuator supplier", "diagnostic lag", "motor age"),
        ("Drift followed the control-schedule change.",
         "Traffic cycles shifted during affected periods.",
         "Actuator suppliers are mixed across depots.",
         "Old-schedule replay removes drift at matched traffic.",
         "Complete logs show no diagnostic-lag effect.",
         "Motor ages vary across switches.",
         "Supplier-matched depots preserve the traffic response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "WC-DISPLAY", "display_manufacturing",
        "Resolve the source of luminance-estimate drift.",
        ("luminance drift", "calibration update", "panel regime",
         "camera vendor", "temperature skew", "line age"),
        ("Calibration policy changed, but replay is inconclusive.",
         "Panel regimes precede every high-drift interval.",
         "Camera vendors are balanced across factories.",
         "Temperature comparisons show persistent luminance skew.",
         "Line ages differ without tracking luminance drift.",
         "Correcting temperature skew removes residual drift.",
         "Vendor-matched factories preserve the panel response."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_warrant_complete_holdout():
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
            "FRESH_V0_49_FROZEN_BEFORE_WARRANT_COMPLETE_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_warrant_complete_holdout(artifact):
    if artifact != build_warrant_complete_holdout():
        raise ValueError("warrant_complete_holdout_invalid")


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
