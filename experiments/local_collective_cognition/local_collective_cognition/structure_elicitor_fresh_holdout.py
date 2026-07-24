"""Unseen object structures for post-calibration elicitor validation."""

from __future__ import annotations

from .provider_telemetry import hash_payload
from .structure_elicitor_calibration_holdout import StructureElicitorCalibrationCase


BENCHMARK_ID = "local-structure-elicitor-fresh-holdout-v0-1"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)


CASES = (
    StructureElicitorCalibrationCase(
        "fresh-path", (
            "A route is written as nodes A-B-C-D and a system must emit one integer called path length. "
            "The specification does not say which unit is being counted. Elicit the competing object "
            "structures and the deciding clarification; do not solve."
        ),
        ("edge count", "number of edges", "transitions", "hops"),
        ("vertex count", "number of vertices", "nodes including endpoints", "node count"),
        ("edges", "vertices", "nodes", "hops", "path length"),
    ),
    StructureElicitorCalibrationCase(
        "fresh-time", (
            "A sensor records one sample every minute from 09:10 through 09:55, and a report requests "
            "one integer for the interval. It is unclear whether the integer is duration or the number "
            "of recorded timestamps. Elicit both object structures and the deciding clarification; do not solve."
        ),
        ("elapsed duration", "minutes elapsed", "time difference"),
        ("inclusive sample count", "number of timestamps", "count both endpoints", "samples"),
        ("duration", "samples", "timestamps", "endpoints", "minutes elapsed"),
    ),
    StructureElicitorCalibrationCase(
        "fresh-change", (
            "An inventory starts at 420 units and ends at 365 units, then a record asks for one integer "
            "called change. It does not specify whether direction is part of the quantity. Elicit both "
            "object structures and the deciding clarification; do not solve."
        ),
        ("signed difference", "net change", "decrease", "negative change"),
        ("absolute difference", "magnitude", "unsigned change", "amount changed"),
        ("signed", "absolute", "magnitude", "decrease", "direction"),
    ),
    StructureElicitorCalibrationCase(
        "fresh-rate", (
            "A service observes 360 requests during 90 seconds and must emit one number for traffic. "
            "The contract does not say whether this is the observed amount or a normalized measure. "
            "Elicit both object structures and the deciding clarification; do not solve."
        ),
        ("total count", "number of requests", "events observed"),
        ("rate", "requests per second", "normalized frequency", "throughput"),
        ("count", "rate", "requests per second", "throughput", "normalized"),
    ),
)


TRUTH_COMMITMENT = hash_payload([item.truth_commitment() for item in CASES])


def public_inputs(cases=CASES):
    return tuple(item.public_input() for item in cases)
