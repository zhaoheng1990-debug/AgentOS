"""Fresh hard/null holdout for lineage-aware revision v0.34."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "lineage_revision_holdout_v0_34"
CORPUS_ID = "local-lineage-revision-v0-34"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id, domain, goal, objects, spans, *, primary, supported,
    informative_null, constraints, counterevidence,
):
    return {
        "case_id": case_id, "domain": domain, "research_goal": goal,
        "objects": objects, "spans": spans, "primary": primary,
        "supported": supported, "informative_null": informative_null,
        "constraints": constraints, "counterevidence": counterevidence,
    }


CASES = (
    _case(
        "LR-SOLAR", "solar_operations",
        "Choose questions that distinguish causes of output-estimate bias.",
        (("O1", "output bias"), ("O2", "irradiance correction"),
         ("O3", "panel soiling"), ("O4", "inverter vendor"),
         ("O5", "curtailment log"), ("O6", "string mismatch")),
        (("S1", "Bias rose after irradiance correction was revised."),
         ("S2", "Panel soiling increased in affected arrays."),
         ("S3", "Inverter vendors are balanced across arrays."),
         ("S4", "Curtailment logs omit several short dispatch events."),
         ("S5", "String mismatch differs after recent maintenance."),
         ("S6", "Old-correction replay reduces bias at matched soiling."),
         ("S7", "Vendor-matched arrays retain the soiling effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-FRAUD", "payment_risk",
        "Choose questions that distinguish causes of fraud-score drift.",
        (("O1", "fraud-score drift"), ("O2", "velocity window"),
         ("O3", "merchant mix"), ("O4", "card network"),
         ("O5", "chargeback delay"), ("O6", "device linking")),
        (("S1", "Drift rose after the velocity window changed."),
         ("S2", "Merchant mix shifted toward cross-border sellers."),
         ("S3", "Card networks are balanced across evaluation sets."),
         ("S4", "Recent chargebacks have not matured into labels."),
         ("S5", "Device links are missing for some guest checkouts."),
         ("S6", "Old-window replay reduces drift within merchant strata."),
         ("S7", "Network-matched payments preserve the merchant effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-ALLOY", "materials_processing",
        "Choose questions that distinguish causes of hardness variation.",
        (("O1", "hardness variation"), ("O2", "heat-treatment dwell"),
         ("O3", "carbon content"), ("O4", "furnace supplier"),
         ("O5", "quench delay"), ("O6", "sample orientation")),
        (("S1", "Variation rose after dwell time was shortened."),
         ("S2", "Carbon content is higher in affected heats."),
         ("S3", "Furnace suppliers are balanced across heats."),
         ("S4", "Quench delays vary during high-throughput periods."),
         ("S5", "Sample orientation differs across two laboratories."),
         ("S6", "Old-dwell replay reduces variation at matched carbon."),
         ("S7", "Supplier-matched heats retain the carbon ordering.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-VOICE", "speech_systems",
        "Choose questions that distinguish causes of recognition drift.",
        (("O1", "recognition drift"), ("O2", "normalization rule"),
         ("O3", "channel noise"), ("O4", "microphone brand"),
         ("O5", "speaker overlap"), ("O6", "transcript maturity")),
        (("S1", "Drift rose after normalization rules changed."),
         ("S2", "Channel noise increased in affected recordings."),
         ("S3", "Microphone brands are balanced across test sets."),
         ("S4", "Speaker overlap is underreported in recent sessions."),
         ("S5", "Recent transcripts omit unresolved utterances."),
         ("S6", "Old-rule replay reduces drift at matched noise."),
         ("S7", "Brand-matched recordings retain the noise effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-PORT", "port_logistics",
        "Choose questions that distinguish causes of berth-delay bias.",
        (("O1", "berth-delay bias"), ("O2", "scheduling rule"),
         ("O3", "vessel mix"), ("O4", "terminal operator"),
         ("O5", "tide window"), ("O6", "arrival timestamp")),
        (("S1", "Bias rose after the scheduling rule changed."),
         ("S2", "Vessel mix shifted toward larger container ships."),
         ("S3", "Terminal operators are balanced across samples."),
         ("S4", "Tide windows constrain several delayed arrivals."),
         ("S5", "Arrival timestamps lag pilot boarding for some vessels."),
         ("S6", "Old-rule replay reduces bias within vessel classes."),
         ("S7", "Operator-matched calls retain the vessel-mix effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-WATER", "water_treatment",
        "Choose questions that distinguish causes of turbidity drift.",
        (("O1", "turbidity drift"), ("O2", "coagulant dose"),
         ("O3", "raw-water algae"), ("O4", "filter supplier"),
         ("O5", "backwash timing"), ("O6", "sensor fouling")),
        (("S1", "Drift rose after coagulant dosing was retuned."),
         ("S2", "Algae counts increased in affected intake periods."),
         ("S3", "Filter suppliers are balanced across treatment trains."),
         ("S4", "Backwash timing differs during peak demand."),
         ("S5", "Sensor fouling is unresolved for two affected trains."),
         ("S6", "Old-dose replay reduces drift at matched algae counts."),
         ("S7", "Supplier-matched trains retain the algae effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-MEMORY", "compute_hardware",
        "Choose questions that distinguish causes of memory-error inflation.",
        (("O1", "memory-error inflation"), ("O2", "refresh policy"),
         ("O3", "module temperature"), ("O4", "DIMM supplier"),
         ("O5", "workload burst"), ("O6", "telemetry sampling")),
        (("S1", "Errors rose after the refresh policy changed."),
         ("S2", "Module temperatures are higher in affected racks."),
         ("S3", "DIMM suppliers are balanced across racks."),
         ("S4", "Workload bursts coincide with missing diagnostics."),
         ("S5", "Telemetry sampling differs across firmware groups."),
         ("S6", "Old-policy replay reduces errors at matched temperature."),
         ("S7", "Supplier-matched racks retain the temperature effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "LR-DELIVERY", "last_mile_logistics",
        "Choose questions that distinguish causes of ETA bias.",
        (("O1", "ETA bias"), ("O2", "route-batching rule"),
         ("O3", "stop density"), ("O4", "vehicle type"),
         ("O5", "driver handoff"), ("O6", "scan latency")),
        (("S1", "Bias rose after route batching changed."),
         ("S2", "Stop density increased in affected routes."),
         ("S3", "Vehicle types are balanced across route groups."),
         ("S4", "Driver handoffs are missing from several route logs."),
         ("S5", "Scan latency rises during depot changeovers."),
         ("S6", "Old-rule replay reduces bias at matched stop density."),
         ("S7", "Vehicle-matched routes retain the density effect.")),
        primary=("O1",), supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),), constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
)


def build_lineage_revision_holdout():
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
        "surface_version": CORPUS_VERSION, "items": items,
        "private_outcomes_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION, "corpus_id": CORPUS_ID,
        "case_count": len(CASES),
        "domain_count": len({value["domain"] for value in CASES}),
        "replication_ids": list(REPLICATION_IDS),
        "public_surface": {**surface, "surface_hash": hash_payload(surface)},
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_34_FROZEN_BEFORE_LINEAGE_REVISION_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_lineage_revision_holdout(artifact):
    if artifact != build_lineage_revision_holdout():
        raise ValueError("lineage_revision_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"], "domain": value["domain"],
        "research_goal": value["research_goal"],
        "object_registry": [
            {"object_id": object_id, "label": label}
            for object_id, label in value["objects"]
        ],
        "evidence_spans": [
            {"span_id": span_id, "text": text,
             "text_hash": hash_payload(text)}
            for span_id, text in value["spans"]
        ],
    }
