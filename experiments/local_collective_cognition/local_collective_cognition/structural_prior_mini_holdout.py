"""Six-item fresh holdout for the ephemeral structural-prior pilot."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .structural_prior_pilot_harness import StructuralPriorPilotHarness


STRUCTURAL_PRIOR_MINI_BENCHMARK_ID = "local-structural-prior-mini-holdout-v0-1"
STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS = (f"benchmark://{STRUCTURAL_PRIOR_MINI_BENCHMARK_ID}",)
STRUCTURAL_PRIOR_MINI_QUESTIONS = (
    BenchmarkQuestion("modular-25", "What is the remainder when 3187 is divided by 61?", ("A: 13", "B: 14", "C: 15", "D: 16")),
    BenchmarkQuestion("ratio-25", "Split 2310 in the ratio 4:7. What is the smaller share?", ("A: 820", "B: 830", "C: 840", "D: 850")),
    BenchmarkQuestion("sets-25", "Among 850 users, 510 use A, 430 use B, and 240 use both. How many use neither?", ("A: 140", "B: 145", "C: 150", "D: 155")),
    BenchmarkQuestion("bayes-25", "A condition has 30% prevalence. A test has 84% sensitivity and 88% specificity. What fraction of positive tests are true positives?", ("A: 2/3", "B: 3/4", "C: 4/5", "D: 5/6")),
    BenchmarkQuestion("string-25", "Start with QRSTUVWX. Swap the two halves, then reverse each adjacent pair. What results?", ("A: XWVUTSRQ", "B: UVWXQRST", "C: RQTSVUXW", "D: VUXWRQTS")),
    BenchmarkQuestion("unit-25", "A vehicle travels at 72 km/h for 4.25 hours. How far does it travel?", ("A: 296 km", "B: 301 km", "C: 306 km", "D: 311 km")),
)
_TRUTH_LABELS = {"modular-25": "C", "ratio-25": "C", "sets-25": "C",
                 "bayes-25": "B", "string-25": "D", "unit-25": "C"}
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in _TRUTH_LABELS.items())
_VALUES = {
    "modular-25": ("3187", "61"), "ratio-25": ("2310", "4", "7"),
    "sets-25": ("850", "510", "430", "240"), "bayes-25": ("30", "84", "88"),
    "string-25": ("QRSTUVWX",), "unit-25": ("72", "4.25"),
}
_PROBLEM_TRUTHS = {
    "modular-25": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-25": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "sets-25": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "bayes-25": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "string-25": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-25": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}


def build_structural_prior_mini_harness():
    return StructuralPriorPilotHarness(
        harness_id="local-structural-prior-mini-harness",
        benchmark_id=STRUCTURAL_PRIOR_MINI_BENCHMARK_ID,
        questions=STRUCTURAL_PRIOR_MINI_QUESTIONS, truths=_TRUTHS,
        evidence_refs=STRUCTURAL_PRIOR_MINI_EVIDENCE_REFS,
        derivation_values=_VALUES, problem_truths=_PROBLEM_TRUTHS,
    )
