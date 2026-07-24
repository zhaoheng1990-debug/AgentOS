"""Fresh v0.32 holdout for receipt-native lazy metacognition."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "lazy_metacognition_holdout_v0_32"
CORPUS_ID = "local-lazy-metacognition-v0-32"
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
        "LM-LAB",
        "laboratory_instrumentation",
        "Choose questions that explain assay-signal drift.",
        (
            ("O1", "assay signal"),
            ("O2", "sensor calibration"),
            ("O3", "reagent lot"),
            ("O4", "incubator temperature"),
            ("O5", "plate position"),
        ),
        (
            ("S1", "Signal drift began after a sensor-calibration update."),
            ("S2", "The affected runs use a newer reagent lot."),
            ("S3", "Incubator temperature stayed within its validated range."),
            ("S4", "Edge plate positions are overrepresented in recent runs."),
            ("S5", "Old calibration reduces drift within the new reagent lot."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-DEMAND",
        "retail_forecasting",
        "Choose questions that explain demand-forecast error.",
        (
            ("O1", "forecast error"),
            ("O2", "promotion calendar"),
            ("O3", "stockout censoring"),
            ("O4", "store cluster"),
            ("O5", "return lag"),
        ),
        (
            ("S1", "Forecast error rose after promotion-calendar changes."),
            ("S2", "Stockouts hide demand in the most affected products."),
            ("S3", "Store-cluster proportions remained stable."),
            ("S4", "Late returns are absent from the newest labels."),
            ("S5", "Old-calendar replay reduces error on stock-matched weeks."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-DRONE",
        "autonomous_navigation",
        "Choose questions that explain localization failures.",
        (
            ("O1", "localization failure"),
            ("O2", "visual feature threshold"),
            ("O3", "surface reflectance"),
            ("O4", "flight controller"),
            ("O5", "wind estimate"),
        ),
        (
            ("S1", "Failures rose after the feature threshold changed."),
            ("S2", "Reflective surfaces dominate the failed trajectories."),
            ("S3", "Flight-controller firmware is unchanged."),
            ("S4", "Wind estimates are missing for several failed flights."),
            ("S5", "Old-threshold replay recovers reflective trajectories."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-FLOOD",
        "hydrological_modeling",
        "Choose questions that explain flood-peak bias.",
        (
            ("O1", "flood-peak bias"),
            ("O2", "runoff coefficient"),
            ("O3", "soil saturation"),
            ("O4", "gauge model"),
            ("O5", "upstream release"),
        ),
        (
            ("S1", "Peak bias changed after runoff-coefficient revision."),
            ("S2", "Antecedent soil saturation was unusually high."),
            ("S3", "Gauge models are balanced across catchments."),
            ("S4", "Some upstream releases have delayed timestamps."),
            ("S5", "The old coefficient reduces bias at matched saturation."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-DEFECT",
        "software_quality",
        "Choose questions that explain defect-classifier drift.",
        (
            ("O1", "classifier error"),
            ("O2", "tokenization rule"),
            ("O3", "repository mix"),
            ("O4", "compiler version"),
            ("O5", "triage label"),
        ),
        (
            ("S1", "Errors rose after the tokenization rule changed."),
            ("S2", "The repository mix shifted toward generated code."),
            ("S3", "Compiler-version distribution remained stable."),
            ("S4", "Recent triage labels omit unresolved reports."),
            ("S5", "Old-tokenizer replay reduces errors within each repository."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-SLEEP",
        "wearable_health",
        "Choose questions that explain sleep-stage disagreement.",
        (
            ("O1", "stage disagreement"),
            ("O2", "motion filter"),
            ("O3", "skin contact"),
            ("O4", "device generation"),
            ("O5", "manual scorer"),
        ),
        (
            ("S1", "Disagreement rose after a motion-filter update."),
            ("S2", "Poor skin contact is common in affected nights."),
            ("S3", "Device generations are balanced across cohorts."),
            ("S4", "Manual scorers disagree on short wake episodes."),
            ("S5", "Old-filter replay improves agreement at matched contact."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-PRICING",
        "market_analytics",
        "Choose questions that explain elasticity-estimate instability.",
        (
            ("O1", "elasticity estimate"),
            ("O2", "price-bucket rule"),
            ("O3", "competitor discount"),
            ("O4", "region mapping"),
            ("O5", "coupon exposure"),
        ),
        (
            ("S1", "Elasticity shifted after price buckets were revised."),
            ("S2", "Competitor discounts increased in the same interval."),
            ("S3", "Region mapping is unchanged."),
            ("S4", "Coupon exposure is missing from some transactions."),
            ("S5", "Old-bucket replay reduces the shift at matched discounts."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
    _case(
        "LM-COATING",
        "advanced_manufacturing",
        "Choose questions that explain coating-thickness variation.",
        (
            ("O1", "coating thickness"),
            ("O2", "spray pressure"),
            ("O3", "substrate roughness"),
            ("O4", "nozzle supplier"),
            ("O5", "line speed"),
        ),
        (
            ("S1", "Variation rose after spray pressure was retuned."),
            ("S2", "Substrate roughness increased in affected batches."),
            ("S3", "Nozzle suppliers are balanced across batches."),
            ("S4", "Line-speed logs have gaps during changeovers."),
            ("S5", "Old-pressure replay narrows variation at matched roughness."),
        ),
        primary=("O1",),
        supported=(("O2", "O1"), ("O3", "O1")),
        informative_null=(("O4", "O1"),),
        constraints=("O5",),
        counterevidence=("S3", "S4", "S5"),
    ),
)


def build_lazy_metacognition_holdout():
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
            "FRESH_V0_32_FROZEN_BEFORE_LAZY_METACOGNITION_RUN"
        ),
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_lazy_metacognition_holdout(artifact):
    if artifact != build_lazy_metacognition_holdout():
        raise ValueError("lazy_metacognition_holdout_invalid")


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
