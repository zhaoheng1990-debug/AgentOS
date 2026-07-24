"""Fresh holdout for capability-routed structural elicitation."""

from fractions import Fraction

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .structural_prior_pilot_harness import StructuralPriorPilotHarness


BENCHMARK_ID = "local-capability-routed-structure-holdout-v0-4"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)
QUESTIONS = (
    BenchmarkQuestion("modular-28", "What is the remainder when 5387 is divided by 89?", ("A: 45", "B: 46", "C: 47", "D: 48")),
    BenchmarkQuestion("ratio-28", "Split 3456 in the ratio 7:9. What is the smaller share?", ("A: 1494", "B: 1512", "C: 1530", "D: 1548")),
    BenchmarkQuestion("sets-28", "Among 1280 users, 760 use A, 610 use B, and 350 use both. How many use neither?", ("A: 240", "B: 250", "C: 260", "D: 270")),
    BenchmarkQuestion("bayes-28", "A condition has 20% prevalence. A test has 95% sensitivity and 80% specificity. What fraction of positive tests are true positives?", ("A: 1/2", "B: 19/35", "C: 3/5", "D: 2/3")),
    BenchmarkQuestion("string-28", "Start with ABCDEFGH. Swap the two halves, then reverse each adjacent pair. What results?", ("A: HGFEDCBA", "B: EFGHABCD", "C: FEHGBADC", "D: GHEFCDAB")),
    BenchmarkQuestion("unit-28", "A vehicle travels at 84 km/h for 3.75 hours. How far does it travel?", ("A: 305 km", "B: 310 km", "C: 315 km", "D: 320 km")),
)
_ANSWERS = {"modular-28": "C", "ratio-28": "B", "sets-28": "C",
            "bayes-28": "B", "string-28": "C", "unit-28": "C"}
_VALUES = {
    "modular-28": ("5387", "89"), "ratio-28": ("3456", "7", "9"),
    "sets-28": ("1280", "760", "610", "350"), "bayes-28": ("20", "95", "80"),
    "string-28": ("ABCDEFGH",), "unit-28": ("84", "3.75"),
}
_PROBLEM_TRUTHS = {
    "modular-28": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-28": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "sets-28": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "bayes-28": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "string-28": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-28": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}


def build_capability_routed_structural_harness():
    return StructuralPriorPilotHarness(
        harness_id="local-capability-routed-structure-harness", benchmark_id=BENCHMARK_ID,
        questions=QUESTIONS,
        truths=tuple(BenchmarkAnswerTruth(key, value) for key, value in _ANSWERS.items()),
        evidence_refs=EVIDENCE_REFS, derivation_values=_VALUES, problem_truths=_PROBLEM_TRUTHS,
    )


def mechanical_truth_checks():
    return (
        5387 % 89 == 47,
        Fraction(3456 * 7, 16) == 1512,
        1280 - (760 + 610 - 350) == 260,
        Fraction(20 * 95, 20 * 95 + 80 * 20) == Fraction(19, 35),
        "".join("EFGHABCD"[i:i + 2][::-1] for i in range(0, 8, 2)) == "FEHGBADC",
        Fraction(84) * Fraction("3.75") == 315,
    )
