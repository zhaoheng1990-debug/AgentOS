"""Fresh six-item holdout for Provider-backed structural-packet quality gating."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .structural_prior_pilot_harness import StructuralPriorPilotHarness


BENCHMARK_ID = "local-quality-gated-structure-holdout-v0-3"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)
QUESTIONS = (
    BenchmarkQuestion("modular-27", "What is the remainder when 4213 is divided by 73?", ("A: 50", "B: 51", "C: 52", "D: 53")),
    BenchmarkQuestion("ratio-27", "Split 2990 in the ratio 5:8. What is the smaller share?", ("A: 1130", "B: 1140", "C: 1150", "D: 1160")),
    BenchmarkQuestion("sets-27", "Among 1040 users, 630 use A, 520 use B, and 310 use both. How many use neither?", ("A: 180", "B: 190", "C: 200", "D: 210")),
    BenchmarkQuestion("bayes-27", "A condition has 25% prevalence. A test has 90% sensitivity and 85% specificity. What fraction of positive tests are true positives?", ("A: 3/5", "B: 2/3", "C: 5/7", "D: 3/4")),
    BenchmarkQuestion("string-27", "Start with GHIJKLMN. Swap the two halves, then reverse each adjacent pair. What results?", ("A: NMLKJIHG", "B: KLMNGHIJ", "C: LKNMHGJI", "D: MLNKIGHJ")),
    BenchmarkQuestion("unit-27", "A vehicle travels at 96 km/h for 3.125 hours. How far does it travel?", ("A: 288 km", "B: 294 km", "C: 300 km", "D: 306 km")),
)
_ANSWERS = {"modular-27": "C", "ratio-27": "C", "sets-27": "C",
            "bayes-27": "B", "string-27": "C", "unit-27": "C"}
_VALUES = {
    "modular-27": ("4213", "73"), "ratio-27": ("2990", "5", "8"),
    "sets-27": ("1040", "630", "520", "310"), "bayes-27": ("25", "90", "85"),
    "string-27": ("GHIJKLMN",), "unit-27": ("96", "3.125"),
}
_PROBLEM_TRUTHS = {
    "modular-27": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-27": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "sets-27": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "bayes-27": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "string-27": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-27": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}


def build_quality_gated_structural_harness():
    return StructuralPriorPilotHarness(
        harness_id="local-quality-gated-structure-harness", benchmark_id=BENCHMARK_ID,
        questions=QUESTIONS,
        truths=tuple(BenchmarkAnswerTruth(key, value) for key, value in _ANSWERS.items()),
        evidence_refs=EVIDENCE_REFS, derivation_values=_VALUES,
        problem_truths=_PROBLEM_TRUTHS,
    )
