"""Fresh six-item holdout for selective contrastive structure expansion."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .structural_prior_pilot_harness import StructuralPriorPilotHarness


BENCHMARK_ID = "local-contrastive-structure-holdout-v0-2"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)
QUESTIONS = (
    BenchmarkQuestion("modular-26", "What is the remainder when 3749 is divided by 67?", ("A: 62", "B: 63", "C: 64", "D: 65")),
    BenchmarkQuestion("ratio-26", "Split 2475 in the ratio 3:8. What is the smaller share?", ("A: 655", "B: 665", "C: 675", "D: 685")),
    BenchmarkQuestion("sets-26", "Among 920 users, 560 use A, 470 use B, and 260 use both. How many use neither?", ("A: 140", "B: 145", "C: 150", "D: 155")),
    BenchmarkQuestion("bayes-26", "A condition has 40% prevalence. A test has 81% sensitivity and 86% specificity. What fraction of positive tests are true positives?", ("A: 3/4", "B: 27/34", "C: 4/5", "D: 5/6")),
    BenchmarkQuestion("string-26", "Start with YZABCDEF. Swap the two halves, then reverse each adjacent pair. What results?", ("A: FEDCBAZY", "B: CDEFYZAB", "C: EFCDAZYB", "D: DCFEZYBA")),
    BenchmarkQuestion("unit-26", "A vehicle travels at 88 km/h for 2.75 hours. How far does it travel?", ("A: 232 km", "B: 237 km", "C: 242 km", "D: 247 km")),
)
_ANSWERS = {"modular-26": "C", "ratio-26": "C", "sets-26": "C",
            "bayes-26": "B", "string-26": "D", "unit-26": "C"}
_VALUES = {
    "modular-26": ("3749", "67"), "ratio-26": ("2475", "3", "8"),
    "sets-26": ("920", "560", "470", "260"), "bayes-26": ("40", "81", "86"),
    "string-26": ("YZABCDEF",), "unit-26": ("88", "2.75"),
}
_PROBLEM_TRUTHS = {
    "modular-26": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-26": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "sets-26": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "bayes-26": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "string-26": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-26": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}


def build_contrastive_structural_harness():
    return StructuralPriorPilotHarness(
        harness_id="local-contrastive-structure-harness", benchmark_id=BENCHMARK_ID,
        questions=QUESTIONS,
        truths=tuple(BenchmarkAnswerTruth(key, value) for key, value in _ANSWERS.items()),
        evidence_refs=EVIDENCE_REFS, derivation_values=_VALUES,
        problem_truths=_PROBLEM_TRUTHS,
    )
