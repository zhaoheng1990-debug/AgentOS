"""Fresh hard/null holdout for zero-token Runtime escalation v0.33."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "runtime_escalation_holdout_v0_33"
CORPUS_ID = "local-runtime-escalation-v0-33"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(
    case_id,
    domain,
    goal,
    objects,
    spans,
    *,
    primary,
    supported,
    informative_null,
    constraints,
    counterevidence,
):
    return {
        "case_id": case_id,
        "domain": domain,
        "research_goal": goal,
        "objects": objects,
        "spans": spans,
        "primary": primary,
        "supported": supported,
        "informative_null": informative_null,
        "constraints": constraints,
        "counterevidence": counterevidence,
    }


CASES = (
    _case(
        "RE-BATTERY",
        "battery_diagnostics",
        "Choose questions that distinguish causes of capacity fade.",
        (
            ("O1", "capacity fade"), ("O2", "charge cutoff"),
            ("O3", "cell temperature"), ("O4", "electrolyte batch"),
            ("O5", "cycler channel"), ("O6", "rest duration"),
        ),
        (
            ("S1", "Fade increased after the charge cutoff changed."),
            ("S2", "Affected cells also ran at higher temperature."),
            ("S3", "Electrolyte batches are balanced across groups."),
            ("S4", "One cycler channel reports intermittent voltage offsets."),
            ("S5", "Rest duration differs between old and recent protocols."),
            ("S6", "Old-cutoff replay reduces fade at matched temperature."),
            ("S7", "Reference-channel cells show the same batch ordering."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-QUEUE",
        "distributed_systems",
        "Choose questions that distinguish causes of queue latency.",
        (
            ("O1", "queue latency"), ("O2", "batch size"),
            ("O3", "request burstiness"), ("O4", "client library"),
            ("O5", "clock skew"), ("O6", "retry policy"),
        ),
        (
            ("S1", "Latency rose after batch size was increased."),
            ("S2", "Request bursts became sharper in the same release."),
            ("S3", "Client-library versions are balanced across services."),
            ("S4", "Clock skew obscures several event-order measurements."),
            ("S5", "Retry policies differ for two high-latency services."),
            ("S6", "Old-batch replay lowers latency at matched burstiness."),
            ("S7", "Library-matched traces preserve the latency ranking."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-CROP",
        "precision_agriculture",
        "Choose questions that distinguish causes of yield-map drift.",
        (
            ("O1", "yield-map drift"), ("O2", "moisture correction"),
            ("O3", "soil texture"), ("O4", "seed variety"),
            ("O5", "harvester speed"), ("O6", "field boundary"),
        ),
        (
            ("S1", "Drift rose after moisture correction was revised."),
            ("S2", "Affected zones have a different soil texture."),
            ("S3", "Seed varieties are balanced across comparison fields."),
            ("S4", "Harvester speed is missing near several field edges."),
            ("S5", "Boundary polygons changed between mapping seasons."),
            ("S6", "Old-correction replay reduces drift within soil strata."),
            ("S7", "Variety-matched plots retain the same drift pattern."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-SCAN",
        "medical_imaging",
        "Choose questions that distinguish causes of segmentation drift.",
        (
            ("O1", "segmentation drift"), ("O2", "reconstruction kernel"),
            ("O3", "lesion contrast"), ("O4", "scanner vendor"),
            ("O5", "reader correction"), ("O6", "slice thickness"),
        ),
        (
            ("S1", "Drift rose after the reconstruction kernel changed."),
            ("S2", "Low-contrast lesions dominate the affected scans."),
            ("S3", "Scanner vendors are balanced across evaluation sets."),
            ("S4", "Reader corrections are absent from recent labels."),
            ("S5", "Slice thickness differs between two acquisition sites."),
            ("S6", "Old-kernel replay reduces drift at matched contrast."),
            ("S7", "Vendor-matched scans preserve the contrast effect."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-TURBINE",
        "wind_operations",
        "Choose questions that distinguish causes of power-curve error.",
        (
            ("O1", "power-curve error"), ("O2", "pitch schedule"),
            ("O3", "air density"), ("O4", "blade coating"),
            ("O5", "yaw offset"), ("O6", "wake exposure"),
        ),
        (
            ("S1", "Error rose after the pitch schedule changed."),
            ("S2", "Air density was lower in the affected periods."),
            ("S3", "Blade coatings are balanced across turbines."),
            ("S4", "Yaw offsets are uncertain for several nacelles."),
            ("S5", "Wake exposure differs across comparison turbines."),
            ("S6", "Old-schedule replay reduces error at matched density."),
            ("S7", "Coating-matched turbines retain the same error ordering."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-CHURN",
        "subscription_analytics",
        "Choose questions that distinguish causes of churn-score drift.",
        (
            ("O1", "churn-score drift"), ("O2", "feature window"),
            ("O3", "plan migration"), ("O4", "billing region"),
            ("O5", "support backlog"), ("O6", "label maturity"),
        ),
        (
            ("S1", "Drift rose after the feature window changed."),
            ("S2", "Plan migrations increased in the same cohort."),
            ("S3", "Billing-region shares remained stable."),
            ("S4", "Support backlog delays several behavioral signals."),
            ("S5", "Recent labels omit customers still in grace periods."),
            ("S6", "Old-window replay reduces drift within migration strata."),
            ("S7", "Region-matched cohorts preserve the migration effect."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-POLYMER",
        "polymer_processing",
        "Choose questions that distinguish causes of viscosity drift.",
        (
            ("O1", "viscosity drift"), ("O2", "mixing duration"),
            ("O3", "feed moisture"), ("O4", "additive supplier"),
            ("O5", "sampling delay"), ("O6", "reactor residue"),
        ),
        (
            ("S1", "Drift rose after mixing duration was shortened."),
            ("S2", "Feed moisture increased in affected batches."),
            ("S3", "Additive suppliers are balanced across batches."),
            ("S4", "Sampling delay varies during high-throughput runs."),
            ("S5", "Reactor residue differs after product changeovers."),
            ("S6", "Old-duration replay reduces drift at matched moisture."),
            ("S7", "Supplier-matched batches retain the moisture ordering."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
    _case(
        "RE-TRAFFIC",
        "urban_mobility",
        "Choose questions that distinguish causes of travel-time bias.",
        (
            ("O1", "travel-time bias"), ("O2", "map-matching rule"),
            ("O3", "incident mix"), ("O4", "vehicle class"),
            ("O5", "signal timing"), ("O6", "probe density"),
        ),
        (
            ("S1", "Bias rose after the map-matching rule changed."),
            ("S2", "Incident mix shifted toward lane closures."),
            ("S3", "Vehicle classes are balanced across samples."),
            ("S4", "Signal timings changed on several affected corridors."),
            ("S5", "Probe density falls during severe incidents."),
            ("S6", "Old-rule replay reduces bias at matched incident mix."),
            ("S7", "Class-matched probes preserve the incident effect."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5", "O6"),
        counterevidence=("S3", "S4", "S5", "S7"),
    ),
)


def build_runtime_escalation_holdout():
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
            **surface,
            "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "truth_coordinate": "SYNTHETIC_OUTCOME_METADATA",
            "available_to_provider": False,
        },
        "reference_state": (
            "FRESH_V0_33_FROZEN_BEFORE_RUNTIME_ESCALATION_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_runtime_escalation_holdout(artifact):
    if artifact != build_runtime_escalation_holdout():
        raise ValueError("runtime_escalation_holdout_invalid")


def _public_item(value):
    return {
        "case_id": value["case_id"],
        "domain": value["domain"],
        "research_goal": value["research_goal"],
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
