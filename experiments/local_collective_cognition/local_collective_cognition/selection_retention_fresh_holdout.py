"""Fresh typed-evidence and selection-retention holdout v0.64."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .portfolio_critic_fresh_holdout import CASES as V061_CASES
from .provider_telemetry import hash_payload


CORPUS_VERSION = "selection_retention_fresh_holdout_v0_64"
CORPUS_ID = "local-selection-retention-fresh-v0-64"
EVIDENCE_REFS = (f"benchmark://{CORPUS_ID}",)
STATE_MAP = {
    "E": ("SUPPORTED_EFFECT", "INTERVENTION_OR_ROLLBACK"),
    "N": ("SUPPORTED_NULL", "MATCHED_NULL_COMPARISON"),
    "U": ("UNRESOLVED", "UNTESTED_DIFFERENCE"),
}


def _spec(
    case_id: str,
    domain: str,
    outcome: str,
    labels: tuple[str, ...],
    spans: tuple[str, ...],
    states: tuple[str, ...],
    *,
    corroborated: tuple[str, ...],
    auxiliary_source: str,
    auxiliary_type: str,
    selected_source: str,
    distractor_source: str,
    validity_state: str,
    observed_cbit: float,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "domain": domain,
        "outcome": outcome,
        "labels": labels,
        "spans": spans,
        "states": states,
        "corroborated": corroborated,
        "auxiliary_source": auxiliary_source,
        "auxiliary_type": auxiliary_type,
        "selected_source": selected_source,
        "distractor_source": distractor_source,
        "validity_state": validity_state,
        "observed_cbit": observed_cbit,
    }


CASES = (
    _spec(
        "SR64-BATTERY",
        "battery_cell_formation",
        "cell impedance variance",
        (
            "formation temperature",
            "electrolyte supplier",
            "dry-room humidity",
            "formation firmware",
            "fixture age",
        ),
        (
            "A randomized formation-temperature rollback reduced cell-impedance variance.",
            "Supplier-balanced electrolyte lots showed no impedance difference.",
            "Dry-room humidity differed, but no humidity-matched test measured impedance variance.",
            "Formation-firmware rollback reduced an independent impedance-drift component.",
            "Fixture ages differed, but no fixture-matched intervention was run.",
            "The temperature and firmware effects replicated on a second formation line.",
            "An uncontrolled seasonal comparison showed no temperature association, but did not preserve the randomized intervention.",
        ),
        ("E", "N", "U", "E", "U"),
        corroborated=("O2", "O5"),
        auxiliary_source="O2",
        auxiliary_type="counter",
        selected_source="O5",
        distractor_source="O4",
        validity_state="CURRENT",
        observed_cbit=0.82,
    ),
    _spec(
        "SR64-CLOUD",
        "distributed_database",
        "tail latency",
        (
            "storage vendor",
            "scheduler policy",
            "replication firmware",
            "traffic geography",
            "rack age",
        ),
        (
            "Storage-vendor balancing showed no measurable tail-latency difference.",
            "A scheduler-policy crossover removed one component of tail-latency drift.",
            "Replication-firmware rollback removed the residual latency component.",
            "Traffic geographies differed, but no geography-matched replay was run.",
            "Rack ages differed, but no age-matched latency comparison exists.",
            "The scheduler and replication effects reproduced in an isolated cluster.",
            "The rack-age comparison omitted peak traffic and therefore cannot resolve the untested age relation.",
        ),
        ("N", "E", "E", "U", "U"),
        corroborated=("O3", "O4"),
        auxiliary_source="O6",
        auxiliary_type="gap",
        selected_source="O4",
        distractor_source="O5",
        validity_state="CURRENT",
        observed_cbit=0.74,
    ),
    _spec(
        "SR64-FERMENT",
        "precision_fermentation",
        "yield stability",
        (
            "feed-rate policy",
            "inoculum age",
            "sensor supplier",
            "agitation firmware",
            "operator shift",
        ),
        (
            "A feed-rate crossover removed one component of yield instability.",
            "Inoculum ages differed, but no age-matched fermentation was run.",
            "Sensor-supplier balancing showed no yield-stability difference.",
            "Agitation-firmware rollback removed the residual yield drift.",
            "Operator shifts differed, but no shift-matched trial exists.",
            "Feed-rate and agitation effects replicated in a second bioreactor.",
            "A nonrandomized pilot associated agitation firmware with no change, but used a different strain and cannot overturn the matched rollback.",
        ),
        ("E", "U", "N", "E", "U"),
        corroborated=("O2", "O5"),
        auxiliary_source="O5",
        auxiliary_type="counter",
        selected_source="O2",
        distractor_source="O3",
        validity_state="CURRENT",
        observed_cbit=0.69,
    ),
    _spec(
        "SR64-WIND",
        "offshore_wind_control",
        "power volatility",
        (
            "foundation age",
            "yaw policy",
            "sensor supplier",
            "wave regime",
            "converter firmware",
        ),
        (
            "Foundation ages differed, but no age-matched intervention measured power volatility.",
            "A randomized yaw-policy crossover reduced one volatility component.",
            "Sensor-supplier swaps showed no measurable volatility difference.",
            "Wave regimes differed, but no regime-matched control replay was run.",
            "Converter-firmware rollback removed the residual volatility component.",
            "Yaw and converter effects replicated across a second turbine row.",
            "The foundation comparison excluded high-wave periods and leaves the age relation untested.",
        ),
        ("U", "E", "N", "U", "E"),
        corroborated=("O3", "O6"),
        auxiliary_source="O2",
        auxiliary_type="gap",
        selected_source="O6",
        distractor_source="O2",
        validity_state="CURRENT",
        observed_cbit=0.77,
    ),
    _spec(
        "SR64-SATELLITE",
        "satellite_image_pipeline",
        "geolocation error",
        (
            "orbit-correction policy",
            "camera supplier",
            "cloud regime",
            "ground-station vendor",
            "navigation firmware",
        ),
        (
            "Orbit-correction rollback reduced one component of geolocation error.",
            "Camera-supplier balancing showed no geolocation difference.",
            "Cloud regimes differed, but no cloud-matched replay measured geolocation error.",
            "Ground-station vendor swaps showed no measurable error difference.",
            "Navigation-firmware rollback removed the residual geolocation drift.",
            "Orbit-correction and navigation effects replicated on another pass.",
            "An uncontrolled polar-orbit subset showed no navigation association, but did not preserve the rollback conditions.",
        ),
        ("E", "N", "U", "N", "E"),
        corroborated=("O2", "O6"),
        auxiliary_source="O6",
        auxiliary_type="counter",
        selected_source="O2",
        distractor_source="O4",
        validity_state="CURRENT",
        observed_cbit=0.71,
    ),
    _spec(
        "SR64-QUANTUM",
        "quantum_readout_control",
        "readout fidelity",
        (
            "amplifier supplier",
            "pulse policy",
            "cryostat age",
            "readout firmware",
            "operator shift",
        ),
        (
            "Amplifier-supplier balancing showed no readout-fidelity difference.",
            "A pulse-policy crossover increased readout fidelity.",
            "Cryostat ages differed, but no age-matched readout trial was run.",
            "Readout-firmware rollback restored an independent fidelity loss.",
            "Operator-shift balancing showed no measurable fidelity difference.",
            "Pulse and firmware effects replicated on a second qubit array.",
            "The cryostat comparison omitted warm-start cycles and leaves age applicability unresolved.",
        ),
        ("N", "E", "U", "E", "N"),
        corroborated=("O3", "O5"),
        auxiliary_source="O4",
        auxiliary_type="gap",
        selected_source="O3",
        distractor_source="O4",
        validity_state="STALE",
        observed_cbit=0.88,
    ),
    _spec(
        "SR64-WATER",
        "membrane_water_treatment",
        "membrane flux",
        (
            "cleaning policy",
            "feedwater season",
            "pump firmware",
            "membrane supplier",
            "plant age",
        ),
        (
            "A cleaning-policy crossover restored one component of membrane flux.",
            "Feedwater seasons differed, but no season-matched intervention was run.",
            "Pump-firmware rollback restored the residual flux loss.",
            "Membrane-supplier balancing showed no measurable flux difference.",
            "Plant ages differed, but no age-matched comparison measured flux.",
            "Cleaning and pump effects replicated on a second treatment train.",
            "An uncontrolled maintenance month showed no pump association, but changed feedwater chemistry and cannot overturn the rollback.",
        ),
        ("E", "U", "E", "N", "U"),
        corroborated=("O2", "O4"),
        auxiliary_source="O4",
        auxiliary_type="counter",
        selected_source="O4",
        distractor_source="O3",
        validity_state="DRIFTED",
        observed_cbit=0.79,
    ),
    _spec(
        "SR64-CHIP",
        "advanced_chip_packaging",
        "thermal resistance",
        (
            "substrate age",
            "bonding policy",
            "inspection vendor",
            "cure firmware",
            "operator shift",
        ),
        (
            "Substrate ages differed, but no age-matched package test measured thermal resistance.",
            "A bonding-policy crossover reduced thermal resistance.",
            "Inspection-vendor balancing showed no measurable resistance difference.",
            "Cure-firmware rollback removed an independent resistance increase.",
            "Operator shifts differed, but no shift-matched package trial exists.",
            "Bonding and cure effects replicated on a second packaging line.",
            "The operator comparison omitted night-shift rework and leaves the shift relation untested.",
        ),
        ("U", "E", "N", "E", "U"),
        corroborated=("O3", "O5"),
        auxiliary_source="O6",
        auxiliary_type="gap",
        selected_source="O5",
        distractor_source="O6",
        validity_state="CURRENT",
        observed_cbit=-0.18,
    ),
)


def build_selection_retention_fresh_holdout() -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    bindings: dict[str, dict[str, Any]] = {}
    for spec in CASES:
        item = _public_item(spec)
        relation_reference = {}
        for index, state_code in enumerate(spec["states"], start=2):
            relation_id = f"REL-O{index}-O1"
            state, design = STATE_MAP[state_code]
            relation_reference[relation_id] = {
                "relation_truth_state": state,
                "evidence_design": design,
                "primary_evidence_span_ids": [f"S{index - 1}"],
                "corroborating_evidence_span_ids": (
                    ["S6"] if f"O{index}" in spec["corroborated"] else []
                ),
                "counterevidence_span_ids": (
                    ["S7"]
                    if spec["auxiliary_type"] == "counter"
                    and spec["auxiliary_source"] == f"O{index}"
                    else []
                ),
                "gap_evidence_span_ids": (
                    ["S7"]
                    if spec["auxiliary_type"] == "gap"
                    and spec["auxiliary_source"] == f"O{index}"
                    else []
                ),
            }
        alternatives = _alternatives(spec)
        item["selection_alternatives"] = alternatives
        items.append(item)
        selected_ref = next(
            value["alternative_ref"]
            for value in alternatives
            if value["source_object_id"] == spec["selected_source"]
        )
        distractor_ref = next(
            value["alternative_ref"]
            for value in alternatives
            if value["source_object_id"] == spec["distractor_source"]
        )
        baseline_ref = next(
            value["alternative_ref"]
            for value in alternatives
            if value["action_kind"] == "PRESERVE_BASELINE"
        )
        expected_retention = (
            "QUARANTINED_SELECTION_EVIDENCE"
            if spec["validity_state"] in {"STALE", "DRIFTED"}
            else "PENDING_RETENTION_REVIEW"
            if spec["observed_cbit"] > 0
            else "PENDING_SELECTION_EVIDENCE"
        )
        bindings[spec["case_id"]] = {
            "public_item_hash": hash_payload(item),
            "typed_relation_reference": relation_reference,
            "expected_selected_ref": selected_ref,
            "expected_rejected_refs": [baseline_ref],
            "expected_deferred_refs": [distractor_ref],
            "validity_state": spec["validity_state"],
            "observed_cbit_gain": spec["observed_cbit"],
            "observed_cost": 0.2,
            "applicability_delta": (
                0.4 if spec["observed_cbit"] > 0 else -0.2
            ),
            "expected_retention_candidate_state": expected_retention,
            "consequence_ref": (
                f"harness://selection-retention-v0-64/"
                f"{spec['case_id']}"
            ),
        }
    items.sort(
        key=lambda value: hash_payload(
            [CORPUS_VERSION, value["case_id"]]
        )
    )
    surface = {
        "surface_version": CORPUS_VERSION,
        "items": items,
        "private_outcomes_exposed": False,
        "reference_states_exposed": False,
        "expected_selection_exposed": False,
        "validity_states_exposed": False,
    }
    commitment = {
        "artifact_version": CORPUS_VERSION,
        "corpus_id": CORPUS_ID,
        "case_count": len(items),
        "domain_count": len(items),
        "relation_count": len(items) * 5,
        "public_surface": {
            **surface,
            "surface_hash": hash_payload(surface),
        },
        "private_provenance": {
            "bindings": bindings,
            "available_to_provider": False,
        },
        "reference_state": "FRESH_V0_64_PREREGISTRATION_ONLY",
        "prior_holdout_cases_reused": False,
        "prior_holdout_labels_reused": False,
        "evidence_refs": list(EVIDENCE_REFS),
        "selection_authority": False,
        "retention_authority": False,
        "baseline_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def audit_selection_retention_fresh_holdout(
    corpus: dict[str, Any],
) -> dict[str, Any]:
    validate_selection_retention_fresh_holdout(corpus)
    state_counts = Counter()
    design_counts = Counter()
    auxiliary_counts = Counter()
    validity_counts = Counter()
    cells = []
    for item in corpus["public_surface"]["items"]:
        private = corpus["private_provenance"]["bindings"][
            item["case_id"]
        ]
        relations = private["typed_relation_reference"]
        for relation in relations.values():
            state_counts[relation["relation_truth_state"]] += 1
            design_counts[relation["evidence_design"]] += 1
            for field in (
                "corroborating_evidence_span_ids",
                "counterevidence_span_ids",
                "gap_evidence_span_ids",
            ):
                auxiliary_counts[field] += len(relation[field])
        validity_counts[private["validity_state"]] += 1
        alternative_refs = {
            value["alternative_ref"]
            for value in item["selection_alternatives"]
        }
        expected_partition = {
            private["expected_selected_ref"],
            *private["expected_rejected_refs"],
            *private["expected_deferred_refs"],
        }
        cells.append({
            "case_id": item["case_id"],
            "relation_count": len(relations),
            "alternative_count": len(alternative_refs),
            "selection_partition_complete": (
                expected_partition == alternative_refs
                and len(expected_partition) == 3
            ),
            "public_hash_valid": (
                private["public_item_hash"] == hash_payload(item)
            ),
        })
    prior_domains = {value["case"]["domain"] for value in V061_CASES}
    commitment = {
        "audit_version": "selection_retention_fresh_audit_v0_64",
        "source_corpus_hash": corpus["artifact_hash"],
        "case_count": len(cells),
        "relation_count": sum(value["relation_count"] for value in cells),
        "valid_cell_count": sum(
            value["relation_count"] == 5
            and value["alternative_count"] == 3
            and value["selection_partition_complete"]
            and value["public_hash_valid"]
            for value in cells
        ),
        "state_counts": dict(sorted(state_counts.items())),
        "design_counts": dict(sorted(design_counts.items())),
        "auxiliary_counts": dict(sorted(auxiliary_counts.items())),
        "validity_counts": dict(sorted(validity_counts.items())),
        "prior_v0_61_domain_overlap": sorted(
            prior_domains.intersection(
                value["domain"]
                for value in corpus["public_surface"]["items"]
            )
        ),
        "cells": cells,
        "provider_calls_added": 0,
        "formal_execution_authorized": (
            len(cells) == 8
            and all(
                value["relation_count"] == 5
                and value["alternative_count"] == 3
                and value["selection_partition_complete"]
                and value["public_hash_valid"]
                for value in cells
            )
            and not prior_domains.intersection(
                value["domain"]
                for value in corpus["public_surface"]["items"]
            )
        ),
        "selection_authority": False,
        "retention_authority": False,
        "production_authority": False,
    }
    return {**commitment, "artifact_hash": hash_payload(commitment)}


def validate_selection_retention_fresh_holdout(
    value: dict[str, Any],
) -> None:
    if value != build_selection_retention_fresh_holdout():
        raise ValueError("selection_retention_fresh_holdout_invalid")


def _public_item(spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": spec["case_id"],
        "domain": spec["domain"],
        "research_goal": (
            f"Resolve the source of {spec['outcome']} drift."
        ),
        "focal_object_id": "O1",
        "object_registry": [
            {"object_id": "O1", "label": spec["outcome"]},
            *[
                {"object_id": f"O{index}", "label": label}
                for index, label in enumerate(spec["labels"], start=2)
            ],
        ],
        "evidence_spans": [
            {
                "span_id": f"S{index}",
                "text": text,
                "text_hash": hash_payload(text),
            }
            for index, text in enumerate(spec["spans"], start=1)
        ],
    }


def _alternatives(spec: dict[str, Any]) -> list[dict[str, Any]]:
    selected_state_index = int(spec["selected_source"][1:]) - 2
    selected_span = f"S{selected_state_index + 1}"
    choices = [
        {
            "alternative_ref": "ALT:BASE",
            "action_kind": "PRESERVE_BASELINE",
            "source_object_id": "O1",
            "evidence_span_ids": [],
            "description": "Preserve the current workflow without changing a source relation.",
        },
        {
            "alternative_ref": "ALT:SHIFT",
            "action_kind": "CHANGE_SOURCE_POLICY",
            "source_object_id": spec["selected_source"],
            "evidence_span_ids": [selected_span],
            "description": (
                "Change the workflow around the source relation supported by "
                f"{selected_span}."
            ),
        },
        {
            "alternative_ref": "ALT:PROBE",
            "action_kind": "CHANGE_SOURCE_POLICY",
            "source_object_id": spec["distractor_source"],
            "evidence_span_ids": [
                f"S{int(spec['distractor_source'][1:]) - 1}"
            ],
            "description": (
                "Change the workflow around a relation that still requires "
                "additional discrimination."
            ),
        },
    ]
    return sorted(
        choices,
        key=lambda value: hash_payload(
            [CORPUS_VERSION, spec["case_id"], value["alternative_ref"]]
        ),
    )
