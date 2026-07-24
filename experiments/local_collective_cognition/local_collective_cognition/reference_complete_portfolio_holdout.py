"""Fresh exhaustive-reference holdout for portfolio validation v0.51."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "reference_complete_portfolio_holdout_v0_51"
CORPUS_ID = "local-reference-complete-portfolio-v0-51"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(case_id, domain, goal, labels, spans):
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
            for index, text in enumerate(spans, 1)
        ),
        "primary": ("O1",),
        "supported": (("O2", "O1"), ("O3", "O1")),
        "informative_null": (("O4", "O1"), ("O5", "O1")),
        "constraints": ("O6",),
        "counterevidence": ("S3", "S4", "S5"),
    }


CASES = (
    _case(
        "RC-HYDRO", "hydroelectric_control",
        "Resolve the source of turbine-efficiency drift.",
        ("efficiency drift", "gate policy", "flow regime",
         "meter vendor", "telemetry lag", "turbine age"),
        ("A randomized rollback to the old gate policy removed drift while "
         "matched new-policy turbines retained it.",
         "Within the new policy, a matched flow intervention normalized the "
         "flow regime and removed the remaining drift.",
         "Vendor-balanced and meter-swapped trials showed no drift "
         "difference.",
         "Clock-synchronized replay showed no telemetry-lag effect.",
         "Turbine ages differ, but no matched-age test has been run.",
         "The policy and flow effects replicate at two independent plants."),
    ),
    _case(
        "RC-PHARMACY", "hospital_pharmacy",
        "Resolve the source of dispensing-time drift.",
        ("dispensing drift", "queue policy", "prescription regime",
         "software vendor", "timestamp lag", "robot age"),
        ("A randomized rollback to the old queue policy removed drift while "
         "matched new-policy pharmacies retained it.",
         "Within the new policy, a matched prescription-regime intervention "
         "removed the remaining drift.",
         "Vendor-balanced and software-swapped trials showed no drift "
         "difference.",
         "Clock-synchronized replay showed no timestamp-lag effect.",
         "Robot ages differ, but no matched-age test has been run.",
         "The policy and prescription effects replicate across hospitals."),
    ),
    _case(
        "RC-METRO", "metro_platform_control",
        "Resolve the source of dwell-time drift.",
        ("dwell drift", "dispatch policy", "passenger regime",
         "sensor vendor", "handoff lag", "train age"),
        ("A randomized rollback to the old dispatch policy removed drift "
         "while matched new-policy lines retained it.",
         "Within the new policy, a matched passenger-flow intervention "
         "removed the remaining drift.",
         "Vendor-balanced and sensor-swapped trials showed no drift "
         "difference.",
         "Synchronized event replay showed no handoff-lag effect.",
         "Train ages differ, but no matched-age test has been run.",
         "The policy and passenger effects replicate across lines."),
    ),
    _case(
        "RC-AQUA", "aquaculture_control",
        "Resolve the source of growth-score drift.",
        ("growth drift", "feeding policy", "oxygen regime",
         "probe vendor", "sampling lag", "tank age"),
        ("A randomized rollback to the old feeding policy removed drift "
         "while matched new-policy tanks retained it.",
         "Within the new policy, a matched oxygen intervention removed the "
         "remaining drift.",
         "Vendor-balanced and probe-swapped trials showed no drift "
         "difference.",
         "Synchronized sample replay showed no sampling-lag effect.",
         "Tank ages differ, but no matched-age test has been run.",
         "The feeding and oxygen effects replicate across farms."),
    ),
    _case(
        "RC-SAT", "satellite_thermal_control",
        "Resolve the source of thermal-estimate drift.",
        ("thermal drift", "control policy", "orbit regime",
         "sensor vendor", "telemetry lag", "panel age"),
        ("A randomized simulator rollback to the old control policy removed "
         "drift while matched new-policy runs retained it.",
         "Within the new policy, a matched orbit-regime intervention removed "
         "the remaining drift.",
         "Vendor-balanced and sensor-swapped trials showed no drift "
         "difference.",
         "Clock-synchronized replay showed no telemetry-lag effect.",
         "Panel ages differ, but no matched-age test has been run.",
         "The policy and orbit effects replicate in independent simulators."),
    ),
    _case(
        "RC-FOUNDRY", "metal_casting",
        "Resolve the source of casting-yield drift.",
        ("yield drift", "furnace policy", "alloy regime",
         "camera vendor", "inspection lag", "mold age"),
        ("A randomized rollback to the old furnace policy removed drift "
         "while matched new-policy lines retained it.",
         "Within the new policy, a matched alloy intervention removed the "
         "remaining drift.",
         "Vendor-balanced and camera-swapped trials showed no drift "
         "difference.",
         "Synchronized inspection replay showed no inspection-lag effect.",
         "Mold ages differ, but no matched-age test has been run.",
         "The furnace and alloy effects replicate across foundries."),
    ),
    _case(
        "RC-CLOUD", "cloud_resource_control",
        "Resolve the source of scheduling-latency drift.",
        ("latency drift", "scheduler policy", "workload regime",
         "host vendor", "logging lag", "cluster age"),
        ("A randomized rollback to the old scheduler policy removed drift "
         "while matched new-policy clusters retained it.",
         "Within the new policy, a matched workload intervention removed the "
         "remaining drift.",
         "Vendor-balanced and host-swapped trials showed no drift "
         "difference.",
         "Clock-synchronized replay showed no logging-lag effect.",
         "Cluster ages differ, but no matched-age test has been run.",
         "The scheduler and workload effects replicate across regions."),
    ),
    _case(
        "RC-CREDIT", "credit_risk_monitoring",
        "Resolve the source of risk-estimate drift.",
        ("estimate drift", "scoring policy", "borrower regime",
         "data vendor", "currency lag", "portfolio age"),
        ("A randomized rollback to the old scoring policy removed drift "
         "while matched new-policy portfolios retained it.",
         "Within the new policy, a matched borrower-regime intervention "
         "removed the remaining drift.",
         "Vendor-balanced and data-swapped trials showed no drift "
         "difference.",
         "Synchronized currency replay showed no currency-lag effect.",
         "Portfolio ages differ, but no matched-age test has been run.",
         "The scoring and borrower effects replicate across regions."),
    ),
)


def build_reference_complete_portfolio_holdout():
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
            "FRESH_V0_51_PENDING_DUAL_PROVIDER_COMPLETENESS_AUDIT"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_reference_complete_portfolio_holdout(artifact):
    if artifact != build_reference_complete_portfolio_holdout():
        raise ValueError("reference_complete_portfolio_holdout_invalid")


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
