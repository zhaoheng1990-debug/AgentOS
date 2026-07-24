from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.provider_telemetry import hash_payload  # noqa: E402
from local_collective_cognition.relation_stability_audit import (  # noqa: E402
    audit_relation_stability,
)


def _artifact(value, field="artifact_hash"):
    return {**value, field: hash_payload(value)}


def _projection(source):
    value = {
        "candidate_components": [{
            "disposition": "ADMITTED_COMPONENT",
            "normalized_candidate": {
                "source_object_id": source,
                "target_object_id": "O1",
            },
        }]
    }
    return value


def test_valid_diversity_is_not_classified_as_unsupported_drift():
    corpus = _artifact({
        "replication_ids": ["R1", "R2", "R3"],
        "public_surface": {
            "items": [{
                "case_id": "CASE",
                "object_registry": [
                    {"object_id": value}
                    for value in ("O1", "O2", "O3", "O4")
                ],
            }],
        },
        "private_provenance": {
            "bindings": {
                "CASE": {
                    "primary_object_ids": ["O1"],
                    "supported_targets": [{
                        "source_object_id": "O2",
                        "target_object_id": "O1",
                    }],
                    "informative_null_targets": [{
                        "source_object_id": "O3",
                        "target_object_id": "O1",
                    }],
                },
            },
        },
    })
    projections = {}
    for rep in ("R1", "R2", "R3"):
        projections[f"{rep}:A1_BASELINE:CASE"] = _projection("O2")
    for rep, source in zip(
        ("R1", "R2", "R3"), ("O2", "O3", "O4")
    ):
        projections[f"{rep}:A2_COMPACT_DELTA:CASE"] = _projection(
            source
        )
    run = _artifact({"final_projections": projections}, "run_hash")
    posthoc = _artifact({
        "cells": [{"classification": "BENEFICIAL_ACCEPTED"}],
    })
    audit = audit_relation_stability(
        corpus=corpus, run=run, posthoc=posthoc
    )
    delta = audit["arm_summaries"]["A2_COMPACT_DELTA"]
    assert audit["diagnosis"] == "PRODUCTIVE_REFERENCE_VALID_DIVERSITY"
    assert delta["mean_pairwise_relation_jaccard"] == 0
    assert delta["mean_union_reference_coverage"] == 1
    assert delta["unsupported_relation_occurrence_rate"] == 0
    assert audit["provider_calls_added"] == 0
    assert audit["formal_v0_54_decision_unchanged"] is True
