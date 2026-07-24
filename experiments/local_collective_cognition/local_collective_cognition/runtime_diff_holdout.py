"""Fresh hard/null holdout for Runtime-derived candidate diff v0.35."""

from __future__ import annotations

from .provider_telemetry import hash_payload


CORPUS_VERSION = "runtime_diff_holdout_v0_35"
CORPUS_ID = "local-runtime-diff-v0-35"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
REPLICATION_IDS = ("R1", "R2", "R3")


def _case(case_id, domain, goal, labels, texts):
    return {
        "case_id": case_id, "domain": domain, "research_goal": goal,
        "objects": tuple(
            (f"O{index}", label)
            for index, label in enumerate(labels, 1)
        ),
        "spans": tuple(
            (f"S{index}", text)
            for index, text in enumerate(texts, 1)
        ),
        "primary": ("O1",),
        "supported": (("O2", "O1"), ("O3", "O1")),
        "informative_null": (("O4", "O1"),),
        "constraints": ("O5", "O6"),
        "counterevidence": ("S3", "S4", "S5", "S7"),
    }


CASES = (
    _case("RD-CHIP", "semiconductor_test",
          "Distinguish causes of leakage-test drift.",
          ("leakage drift", "test voltage", "wafer temperature",
           "probe-card vendor", "contact retry", "lot maturity"),
          ("Drift rose after test voltage changed.",
           "Wafer temperature increased in affected lots.",
           "Probe-card vendors are balanced across lots.",
           "Contact retries are missing for several dies.",
           "Recent lots have incomplete final-bin labels.",
           "Old-voltage replay reduces drift at matched temperature.",
           "Vendor-matched lots preserve the temperature effect.")),
    _case("RD-FOREST", "forest_monitoring",
          "Distinguish causes of biomass-estimate bias.",
          ("biomass bias", "allometry rule", "canopy moisture",
           "sensor vendor", "plot boundary", "survey age"),
          ("Bias rose after allometry rules changed.",
           "Canopy moisture differs in affected plots.",
           "Sensor vendors are balanced across plots.",
           "Plot boundaries changed between surveys.",
           "Survey ages differ across forest strata.",
           "Old-rule replay reduces bias at matched moisture.",
           "Vendor-matched plots preserve the moisture effect.")),
    _case("RD-CREDIT", "credit_risk",
          "Distinguish causes of default-score drift.",
          ("score drift", "history window", "borrower mix",
           "bureau vendor", "payment lag", "label maturity"),
          ("Drift rose after history windows changed.",
           "Borrower mix shifted toward new firms.",
           "Bureau vendors are balanced across samples.",
           "Payment lags hide recent delinquencies.",
           "Newest loans have immature default labels.",
           "Old-window replay reduces drift within borrower strata.",
           "Vendor-matched loans preserve the mix effect.")),
    _case("RD-FERMENT", "bioprocess_control",
          "Distinguish causes of fermentation-yield variation.",
          ("yield variation", "feed schedule", "inoculum age",
           "vessel maker", "sampling delay", "oxygen calibration"),
          ("Variation rose after feed scheduling changed.",
           "Inoculum age increased in affected batches.",
           "Vessel makers are balanced across batches.",
           "Sampling delays vary during peak operation.",
           "Oxygen calibration is unresolved for two vessels.",
           "Old-schedule replay reduces variation at matched age.",
           "Maker-matched batches preserve the age effect.")),
    _case("RD-RAIL", "rail_operations",
          "Distinguish causes of arrival-time bias.",
          ("arrival bias", "dispatch rule", "traffic density",
           "train model", "platform conflict", "timestamp lag"),
          ("Bias rose after dispatch rules changed.",
           "Traffic density increased in affected corridors.",
           "Train models are balanced across samples.",
           "Platform conflicts are missing from some logs.",
           "Timestamps lag control events at two stations.",
           "Old-rule replay reduces bias at matched density.",
           "Model-matched runs preserve the density effect.")),
    _case("RD-CLOUD", "cloud_reliability",
          "Distinguish causes of timeout-rate drift.",
          ("timeout drift", "connection policy", "request fanout",
           "runtime vendor", "retry overlap", "trace sampling"),
          ("Drift rose after connection policy changed.",
           "Request fanout increased in affected services.",
           "Runtime vendors are balanced across services.",
           "Retry overlap is missing from aggregate logs.",
           "Trace sampling differs during incident windows.",
           "Old-policy replay reduces drift at matched fanout.",
           "Vendor-matched services preserve the fanout effect.")),
    _case("RD-CELL", "cell_culture",
          "Distinguish causes of growth-rate drift.",
          ("growth drift", "media exchange", "passage number",
           "flask supplier", "imaging delay", "density estimate"),
          ("Drift rose after media exchange changed.",
           "Passage number increased in affected cultures.",
           "Flask suppliers are balanced across cultures.",
           "Imaging delays differ during weekend runs.",
           "Density estimates are missing for two plates.",
           "Old-exchange replay reduces drift at matched passage.",
           "Supplier-matched cultures preserve the passage effect.")),
    _case("RD-ROOF", "building_energy",
          "Distinguish causes of cooling-load bias.",
          ("cooling-load bias", "roof coefficient", "solar exposure",
           "meter vendor", "occupancy lag", "ventilation mode"),
          ("Bias rose after roof coefficients changed.",
           "Solar exposure increased in affected buildings.",
           "Meter vendors are balanced across buildings.",
           "Occupancy logs lag several demand peaks.",
           "Ventilation modes differ during retrofit periods.",
           "Old-coefficient replay reduces bias at matched exposure.",
           "Vendor-matched buildings preserve the exposure effect.")),
)


def build_runtime_diff_holdout():
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
        "reference_state": "FRESH_V0_35_FROZEN_BEFORE_RUNTIME_DIFF_RUN",
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False, "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_runtime_diff_holdout(artifact):
    if artifact != build_runtime_diff_holdout():
        raise ValueError("runtime_diff_holdout_invalid")


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
