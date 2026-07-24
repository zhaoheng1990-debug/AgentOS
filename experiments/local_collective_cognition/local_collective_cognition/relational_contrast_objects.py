"""Mechanical arm catalog derived from the benchmark object."""

from __future__ import annotations

from typing import Any

from .provider_telemetry import hash_payload


def arm_catalog(item: dict[str, Any]) -> dict[str, Any]:
    commitment = {
        "catalog_version": "relational_arm_catalog_v0_68",
        "case_id": item["case_id"],
        "arms": [
            {
                "arm_id": "FOCAL_INTERVENTION",
                "canonical_text": item["object"]["intervention"],
            },
            {
                "arm_id": "FOCAL_COMPARATOR",
                "canonical_text": item["object"]["comparator"],
            },
        ],
        "semantic_inference_performed": False,
    }
    return {**commitment, "catalog_hash": hash_payload(commitment)}
