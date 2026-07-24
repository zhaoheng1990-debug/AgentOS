"""Fresh holdout for non-destructive portfolio displacement v0.50."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "portfolio_displacement_holdout_v0_50"
CORPUS_ID = "local-portfolio-displacement-v0-50"
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
        "PD-SOLAR", "solar_inverter_control",
        "Resolve the source of conversion-efficiency drift.",
        ("efficiency drift", "inverter policy", "irradiance regime",
         "meter vendor", "telemetry skew", "module age"),
        ("Efficiency drift followed the inverter-policy update.",
         "Irradiance regimes precede high-drift intervals.",
         "Meter vendors are balanced across solar fields.",
         "Telemetry exports omit two clock corrections.",
         "Module age differs without tracking efficiency drift.",
         "Old-policy replay removes matched-irradiance drift.",
         "Vendor-matched fields preserve the irradiance response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "PD-LAB", "clinical_laboratory",
        "Resolve the source of turnaround-time drift.",
        ("turnaround drift", "intake policy", "sample mix",
         "software vendor", "timestamp lag", "analyzer age"),
        ("Turnaround drift followed the intake-policy revision.",
         "Sample mix changed after the first drift interval.",
         "Software vendors are balanced across laboratories.",
         "Record exports reverse several processing times.",
         "Analyzer age varies without matching turnaround drift.",
         "Correcting event order removes residual drift.",
         "Old-policy replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "PD-PORT", "container_port",
        "Resolve the source of crane-cycle drift.",
        ("cycle drift", "dispatch policy", "vessel pattern",
         "scanner vendor", "handoff lag", "crane age"),
        ("Dispatch policy changed before crane-cycle drift.",
         "Policy replay leaves mixed cycle residuals.",
         "Vessel patterns precede every high-drift shift.",
         "Scanner vendors are balanced across terminals.",
         "Handoff lag does not align with cycle drift.",
         "Older cranes retain bias at matched vessel load.",
         "Vendor-matched terminals preserve the vessel response."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "PD-IRRIGATION", "precision_irrigation",
        "Resolve the source of moisture-score drift.",
        ("moisture drift", "watering update", "soil mix",
         "probe vendor", "sampling lag", "valve age"),
        ("Drift followed the watering update.",
         "Soil mix changed after drift was established.",
         "Probe vendors are balanced across plots.",
         "Sample exports misorder several watering steps.",
         "Valve ages differ but do not match affected plots.",
         "Correcting event order removes residual drift.",
         "Old-schedule replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "PD-DRONE", "drone_delivery",
        "Resolve the source of route-time drift.",
        ("route drift", "routing policy", "wind pattern",
         "camera vendor", "handoff lag", "battery age"),
        ("Routing policy changed before route-time drift.",
         "Policy replay does not explain crosswind residuals.",
         "Wind patterns precede normal-load drift.",
         "Camera vendors are balanced across hubs.",
         "Handoff reports lag flight logs by six minutes.",
         "Handoff correction removes crosswind residual drift.",
         "Battery age varies but matched-age hubs still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "PD-REACTOR", "chemical_reactor",
        "Resolve the source of reaction-yield drift.",
        ("yield drift", "feed policy", "ambient exposure",
         "sensor vendor", "maintenance lag", "impeller age"),
        ("Drift followed the feed-policy update.",
         "Ambient exposure explains only afternoon errors.",
         "Sensor vendors are balanced across reactor blocks.",
         "Maintenance logs omit two sensor replacements.",
         "Impeller age was proposed but block matching weakens it.",
         "Bench tests show aged impellers do not alter yield scores.",
         "Old-policy replay reduces drift outside afternoon periods."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S2", "S3", "S4", "S6"),
    ),
    _case(
        "PD-DATACENTER", "data_center_cooling",
        "Resolve the source of cooling-latency drift.",
        ("latency drift", "fan schedule", "workload cycle",
         "chiller supplier", "diagnostic lag", "pump age"),
        ("Drift followed the fan-schedule change.",
         "Workload cycles shifted during affected periods.",
         "Chiller suppliers are mixed across halls.",
         "Old-schedule replay removes drift at matched workload.",
         "Complete logs show no diagnostic-lag effect.",
         "Pump ages vary across halls.",
         "Supplier-matched halls preserve the workload response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "PD-CLAIMS", "insurance_claims",
        "Resolve the source of settlement-estimate drift.",
        ("estimate drift", "scoring update", "claim regime",
         "data vendor", "currency skew", "policy age"),
        ("Scoring policy changed, but replay is inconclusive.",
         "Claim regimes precede every high-drift interval.",
         "Data vendors are balanced across regions.",
         "Currency comparisons show persistent estimate skew.",
         "Policy ages differ without tracking estimate drift.",
         "Correcting currency skew removes residual drift.",
         "Vendor-matched regions preserve the claim response."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_portfolio_displacement_holdout():
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
            "FRESH_V0_50_FROZEN_BEFORE_PORTFOLIO_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_portfolio_displacement_holdout(artifact):
    if artifact != build_portfolio_displacement_holdout():
        raise ValueError("portfolio_displacement_holdout_invalid")


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
