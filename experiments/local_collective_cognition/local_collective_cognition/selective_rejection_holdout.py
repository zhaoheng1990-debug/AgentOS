"""Fresh rotated-reference holdout for selective rejection v0.52."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "selective_rejection_holdout_v0_52"
CORPUS_ID = "local-selective-rejection-v0-52"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id,
    domain,
    goal,
    labels,
    spans,
    *,
    supported,
    informative_null,
    unresolved,
    counterevidence,
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
            for index, text in enumerate(spans, 1)
        ),
        "primary": ("O1",),
        "supported": tuple((value, "O1") for value in supported),
        "informative_null": tuple(
            (value, "O1") for value in informative_null
        ),
        "constraints": tuple(unresolved),
        "counterevidence": tuple(counterevidence),
    }


CASES = (
    _case(
        "SR-LAB",
        "cell_culture_lab",
        "Resolve the source of viability-estimate drift.",
        (
            "viability drift", "reagent batch", "incubator firmware",
            "sample handling", "analyst shift", "plate vendor",
        ),
        (
            "Matched reagent-batch replacement removed the drift while "
            "the original batch retained it.",
            "A randomized handling-protocol crossover removed the residual "
            "drift in both incubators.",
            "Firmware rollback and balanced replay showed no viability "
            "difference.",
            "Vendor-balanced plate swaps showed no drift difference.",
            "Analyst shifts differ, but no shift-matched test was run.",
            "The reagent and handling effects replicated in a second lab.",
        ),
        supported=("O2", "O4"),
        informative_null=("O3", "O6"),
        unresolved=("O5",),
        counterevidence=("S3", "S4"),
    ),
    _case(
        "SR-GRID",
        "microgrid_control",
        "Resolve the source of voltage-forecast drift.",
        (
            "forecast drift", "network topology", "control firmware",
            "weather regime", "sensor vendor", "clock skew",
        ),
        (
            "Topology differs between sites, but no topology-matched "
            "intervention has been run.",
            "Randomized firmware rollback removed the drift while current "
            "firmware retained it.",
            "A matched weather-regime intervention removed the residual "
            "forecast error.",
            "Sensor-vendor balancing and swap tests showed no difference.",
            "Clock-synchronized replay showed no clock-skew effect.",
            "Firmware and weather effects replicated on an isolated feeder.",
        ),
        supported=("O3", "O4"),
        informative_null=("O5", "O6"),
        unresolved=("O2",),
        counterevidence=("S4", "S5"),
    ),
    _case(
        "SR-PORT",
        "container_terminal",
        "Resolve the source of vessel-turnaround drift.",
        (
            "turnaround drift", "berth policy", "tide regime",
            "crane firmware", "scanner vendor", "terminal age",
        ),
        (
            "Randomized berth-policy rollback removed the drift on matched "
            "vessels.",
            "Tide-balanced arrivals showed no turnaround difference.",
            "A crane-firmware crossover removed the residual delay.",
            "Scanner-vendor balancing and swaps showed no delay effect.",
            "Terminal ages differ, but no age-matched comparison exists.",
            "Berth and firmware effects replicated across two terminals.",
        ),
        supported=("O2", "O4"),
        informative_null=("O3", "O5"),
        unresolved=("O6",),
        counterevidence=("S2", "S4"),
    ),
    _case(
        "SR-ROBOT",
        "warehouse_robotics",
        "Resolve the source of pick-cycle drift.",
        (
            "cycle drift", "calibration policy", "payload mix",
            "motor vendor", "vision firmware", "logging lag",
        ),
        (
            "Calibration-policy rollback left cycle drift unchanged.",
            "A matched payload-mix intervention removed one drift component.",
            "Motor vendors differ, but no vendor-balanced swap was run.",
            "Randomized vision-firmware rollback removed residual drift.",
            "Synchronized log replay showed no logging-lag effect.",
            "Payload and vision effects replicated in a second warehouse.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O6"),
        unresolved=("O4",),
        counterevidence=("S1", "S5"),
    ),
    _case(
        "SR-CLINIC",
        "outpatient_clinic",
        "Resolve the source of waiting-time drift.",
        (
            "waiting drift", "triage policy", "case mix",
            "device vendor", "handoff protocol", "timestamp lag",
        ),
        (
            "Randomized triage-policy rollback removed the initial drift.",
            "Case mix differs by day, but no matched case-mix test exists.",
            "Device-vendor balancing and swaps showed no waiting difference.",
            "A handoff-protocol crossover removed the residual delay.",
            "Clock-synchronized replay showed no timestamp-lag effect.",
            "Triage and handoff effects replicated at another clinic.",
        ),
        supported=("O2", "O5"),
        informative_null=("O4", "O6"),
        unresolved=("O3",),
        counterevidence=("S3", "S5"),
    ),
    _case(
        "SR-WAFER",
        "semiconductor_fabrication",
        "Resolve the source of overlay-error drift.",
        (
            "overlay drift", "recipe policy", "humidity regime",
            "metrology vendor", "chamber cleaning", "tool age",
        ),
        (
            "Recipe-policy rollback left overlay drift unchanged.",
            "A matched humidity intervention removed the initial error.",
            "Metrology-vendor balancing and swaps showed no error difference.",
            "Randomized chamber-cleaning timing removed the residual error.",
            "Tool ages differ, but no age-matched test has been run.",
            "Humidity and cleaning effects replicated on an independent line.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
    _case(
        "SR-FLEET",
        "electric_delivery_fleet",
        "Resolve the source of range-estimate drift.",
        (
            "range drift", "routing policy", "cargo mix",
            "tire vendor", "charging profile", "telemetry lag",
        ),
        (
            "Randomized routing-policy rollback removed the initial drift.",
            "Cargo-mix balancing showed no range-estimate difference.",
            "Tire vendors differ, but no vendor-balanced swap was run.",
            "A matched charging-profile intervention removed residual drift.",
            "Synchronized telemetry replay showed no lag effect.",
            "Routing and charging effects replicated in a second depot.",
        ),
        supported=("O2", "O5"),
        informative_null=("O3", "O6"),
        unresolved=("O4",),
        counterevidence=("S2", "S5"),
    ),
    _case(
        "SR-LEDGER",
        "distributed_ledger",
        "Resolve the source of confirmation-latency drift.",
        (
            "latency drift", "batching policy", "transaction regime",
            "node vendor", "retry protocol", "archive age",
        ),
        (
            "Batching-policy rollback left confirmation drift unchanged.",
            "A matched transaction-regime intervention removed initial drift.",
            "Node-vendor balancing and image swaps showed no difference.",
            "Randomized retry-protocol rollback removed residual drift.",
            "Archive ages differ, but no age-matched replay exists.",
            "Transaction and retry effects replicated on a second network.",
        ),
        supported=("O3", "O5"),
        informative_null=("O2", "O4"),
        unresolved=("O6",),
        counterevidence=("S1", "S3"),
    ),
)


def build_selective_rejection_holdout():
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
            "FRESH_V0_52_PENDING_DUAL_PROVIDER_COMPLETENESS_AUDIT"
        ),
        "prior_holdout_labels_reused": False,
        "relation_state_positions_rotated_across_cases": True,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selective_rejection_holdout(artifact):
    if artifact != build_selective_rejection_holdout():
        raise ValueError("selective_rejection_holdout_invalid")


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
