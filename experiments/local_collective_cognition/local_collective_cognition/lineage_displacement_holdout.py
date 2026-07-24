"""Fresh holdout for lineage-bound displacement validation v0.47."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "lineage_displacement_holdout_v0_47"
CORPUS_ID = "local-lineage-displacement-v0-47"
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
        "LD-COLDCHAIN", "vaccine_cold_chain",
        "Resolve the source of potency-estimate drift.",
        ("potency drift", "cooling policy", "door exposure",
         "logger vendor", "upload lag", "compressor age"),
        ("Potency drift followed the cooling-policy update.",
         "Door exposure peaks precede warm-route drift.",
         "Logger vendors are balanced across depots.",
         "Upload logs omit two synchronization resets.",
         "Compressor age differs without matching drift.",
         "Old-policy replay removes closed-door drift.",
         "Vendor-matched depots preserve the exposure effect."),
        (("O2", "O1"), ("O3", "O1")),
        (("O4", "O1"),), ("O5", "O6"), ("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LD-TEXTILE", "textile_dyeing",
        "Resolve the source of color-estimate drift.",
        ("color drift", "dyeing recipe", "fiber blend",
         "camera supplier", "sample lag", "nozzle wear"),
        ("Drift followed the dyeing-recipe revision.",
         "Fiber blend changed after the first drift interval.",
         "Camera suppliers are balanced across lines.",
         "Sample exports reverse several inspection times.",
         "Nozzle wear varies without tracking drift.",
         "Correcting sample order removes residual drift.",
         "Old-recipe replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5", "S7"),
    ),
    _case(
        "LD-WIND", "wind_farm",
        "Resolve the source of power-curve drift.",
        ("power drift", "yaw policy", "wake exposure",
         "anemometer vendor", "telemetry lag", "blade age"),
        ("The yaw policy changed before drift.",
         "Policy replay gives mixed power residuals.",
         "Wake exposure precedes every high-drift turbine.",
         "Anemometer vendors are balanced across farms.",
         "Telemetry lag does not align with power drift.",
         "Older blades retain bias at matched wake exposure.",
         "Vendor-matched turbines preserve the wake effect."),
        (("O3", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O2", "O5"), ("S1", "S4", "S5", "S7"),
    ),
    _case(
        "LD-LIBRARY", "digital_library",
        "Resolve the source of retrieval-score drift.",
        ("retrieval drift", "ranking update", "query mix",
         "index vendor", "event lag", "archive age"),
        ("Drift followed the ranking update.",
         "Query mix changed after drift was established.",
         "Index vendors are balanced across collections.",
         "Event exports misorder several ingestion steps.",
         "Archive ages differ but do not match affected sets.",
         "Correcting event order removes residual drift.",
         "Old-ranker replay reduces the remaining drift."),
        (("O2", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O3", "O6"), ("S2", "S3", "S5"),
    ),
    _case(
        "LD-AQUACULTURE", "aquaculture_control",
        "Resolve the source of oxygen-demand drift.",
        ("demand drift", "feeding policy", "water regime",
         "probe vendor", "lab lag", "aerator age"),
        ("Feeding policy changed before demand drift.",
         "Policy replay does not explain hot-day residuals.",
         "Water regimes precede dry-day drift.",
         "Probe vendors are balanced across tanks.",
         "Lab reports lag inline probes by eight minutes.",
         "Lag correction removes hot-day residual drift.",
         "Aerator age varies but matched-age tanks still drift."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S2", "S4", "S7"),
    ),
    _case(
        "LD-ROBOT", "warehouse_robotics",
        "Resolve the source of localization-score drift.",
        ("localization drift", "planner policy", "floor vibration",
         "lidar vendor", "service lag", "wheel age"),
        ("Drift followed the planner-policy update.",
         "Floor vibration explains only loading-zone errors.",
         "Lidar vendors are balanced across robot fleets.",
         "Service logs omit two lidar replacements.",
         "Wheel age was proposed but route matching weakens it.",
         "Bench tests show aged wheels shift localization score.",
         "Old-policy replay reduces drift outside loading zones."),
        (("O2", "O1"), ("O6", "O1")),
        (("O4", "O1"),), ("O3", "O5"), ("S2", "S3", "S4", "S5"),
    ),
    _case(
        "LD-FOUNDRY", "metal_foundry",
        "Resolve the source of hardness-estimate drift.",
        ("hardness drift", "cooling schedule", "alloy cycle",
         "furnace supplier", "sampling lag", "probe age"),
        ("Drift followed the cooling-schedule change.",
         "Alloy cycles shifted during affected lots.",
         "Furnace suppliers are mixed across plants.",
         "Old-schedule replay removes drift at matched alloy.",
         "Complete logs show no sampling-lag effect.",
         "Probe ages vary across furnaces.",
         "Supplier-matched plants preserve the alloy response."),
        (("O2", "O1"), ("O3", "O1")),
        (("O5", "O1"),), ("O4", "O6"), ("S3", "S5", "S6", "S7"),
    ),
    _case(
        "LD-RADAR", "weather_radar",
        "Resolve the source of rainfall-estimate drift.",
        ("rainfall drift", "filter update", "storm regime",
         "receiver vendor", "clock skew", "antenna age"),
        ("Filter policy changed, but replay is inconclusive.",
         "Storm regimes precede every high-drift interval.",
         "Receiver vendors are balanced across sites.",
         "Clock comparisons show persistent radar skew.",
         "Antenna ages differ without tracking rainfall drift.",
         "Correcting clock skew removes residual drift.",
         "Vendor-matched sites preserve the storm effect."),
        (("O3", "O1"), ("O5", "O1")),
        (("O4", "O1"),), ("O2", "O6"), ("S1", "S3", "S5", "S7"),
    ),
)


def build_lineage_displacement_holdout():
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
            "FRESH_V0_47_FROZEN_BEFORE_LINEAGE_DISPLACEMENT_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_lineage_displacement_holdout(artifact):
    if artifact != build_lineage_displacement_holdout():
        raise ValueError("lineage_displacement_holdout_invalid")


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

