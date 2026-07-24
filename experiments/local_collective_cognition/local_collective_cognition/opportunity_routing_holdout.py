"""Fresh holdout for admission-opportunity routing validation v0.46."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "opportunity_routing_holdout_v0_46"
CORPUS_ID = "local-opportunity-routing-v0-46"
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
        "OR-RAIL", "rail_signal",
        "Resolve the source of braking-margin drift.",
        ("margin drift", "control patch", "rail moisture",
         "sensor maker", "clock lag", "pad age"),
        ("Margin drift followed the control patch.",
         "Rail moisture peaks precede wet-route drift.",
         "Sensor makers are balanced across train sets.",
         "Clock exports omit two synchronization resets.",
         "Pad age differs without matching margin drift.",
         "Old-patch replay removes dry-route drift.",
         "Maker-matched trains preserve the moisture effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "OR-GLASS", "glass_furnace",
        "Resolve the source of thickness-estimate drift.",
        ("thickness drift", "annealing recipe", "silica mix",
         "camera vendor", "sample lag", "roller wear"),
        ("Drift followed the annealing-recipe revision.",
         "Silica mix changed after the first drift interval.",
         "Camera vendors are balanced across lines.",
         "Sample exports reverse several inspection times.",
         "Roller wear varies without tracking drift.",
         "Correcting sample order removes residual drift.",
         "Old-recipe replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "OR-ORCHARD", "orchard_irrigation",
        "Resolve the source of yield-forecast drift.",
        ("forecast drift", "irrigation policy", "heat exposure",
         "probe vendor", "upload lag", "tree age"),
        ("The irrigation policy changed before drift.",
         "Policy replay gives mixed forecast residuals.",
         "Heat exposure precedes every high-drift block.",
         "Probe vendors are balanced across orchards.",
         "Upload lag does not align with forecast drift.",
         "Older trees retain bias at matched heat.",
         "Vendor-matched blocks preserve the heat effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "OR-PORT", "port_logistics",
        "Resolve the source of berth-delay score drift.",
        ("delay drift", "dispatch policy", "cargo mix",
         "scanner vendor", "event lag", "crane age"),
        ("Delay drift followed the dispatch-policy update.",
         "Cargo mix changed after drift was established.",
         "Scanner vendors are balanced across terminals.",
         "Event exports misorder several handoffs.",
         "Crane ages differ but do not match affected berths.",
         "Correcting event order removes residual drift.",
         "Old-policy replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "OR-DISTRICT", "district_heating",
        "Resolve the source of demand-model drift.",
        ("demand drift", "pump policy", "weather regime",
         "meter vendor", "billing lag", "pipe age"),
        ("Pump policy changed before demand drift.",
         "Policy replay does not explain cold-day residuals.",
         "Weather regimes precede dry-day drift.",
         "Meter vendors are balanced across districts.",
         "Billing reports lag inline meters by nine minutes.",
         "Lag correction removes cold-day residual drift.",
         "Pipe age varies but matched-age districts still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "OR-SATELLITE", "satellite_attitude",
        "Resolve the source of pointing-score drift.",
        ("pointing drift", "filter policy", "solar pressure",
         "tracker vendor", "maintenance lag", "wheel age"),
        ("Pointing drift followed the filter-policy update.",
         "Solar pressure explains only eclipse exits.",
         "Tracker vendors are balanced across spacecraft.",
         "Maintenance logs omit two tracker swaps.",
         "Wheel age was proposed but orbit matching weakens it.",
         "Bench tests show aged wheels shift pointing score.",
         "Old-policy replay reduces drift outside eclipse exits."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "OR-PAPER", "paper_mill",
        "Resolve the source of tensile-estimate drift.",
        ("tensile drift", "drying schedule", "pulp cycle",
         "machine supplier", "sampling lag", "roller age"),
        ("Drift followed the drying-schedule change.",
         "Pulp cycles shifted during affected lots.",
         "Machine suppliers are mixed across mills.",
         "Old-schedule replay removes drift at matched pulp.",
         "Complete logs show no sampling-lag effect.",
         "Roller ages vary across machines.",
         "Supplier-matched mills preserve the pulp response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "OR-SONAR", "sonar_array",
        "Resolve the source of range-estimate drift.",
        ("range drift", "filter update", "current burst",
         "modem vendor", "clock skew", "cable age"),
        ("Filter policy changed, but replay is inconclusive.",
         "Current bursts precede every high-drift interval.",
         "Modem vendors are balanced across arrays.",
         "Clock comparisons show persistent array skew.",
         "Cable ages differ without tracking range drift.",
         "Correcting clock skew removes residual drift.",
         "Vendor-matched arrays preserve the current effect."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_opportunity_routing_holdout():
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
            "FRESH_V0_46_FROZEN_BEFORE_OPPORTUNITY_ROUTING_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_opportunity_routing_holdout(artifact):
    if artifact != build_opportunity_routing_holdout():
        raise ValueError("opportunity_routing_holdout_invalid")


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
