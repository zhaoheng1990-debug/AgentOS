"""Fresh holdout for problem-formulation protocol v0.24."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .problem_formulation_harness import ProblemFormulationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V22_BENCHMARK_ID = "local-reasoning-holdout-v0-22"
HOLDOUT_V22_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V22_BENCHMARK_ID}",)
HOLDOUT_V22_QUESTIONS = (
    BenchmarkQuestion("arithmetic-23", "What is (84 multiplied by 4) minus 57?", ("A: 269", "B: 279", "C: 289", "D: 299")),
    BenchmarkQuestion("rate-23", "A machine makes 3960 parts in 44 hours at a constant rate. How many in 3.2 hours?", ("A: 278", "B: 288", "C: 298", "D: 308")),
    BenchmarkQuestion("percent-23", "What is 18.75% of 640?", ("A: 110", "B: 115", "C: 120", "D: 125")),
    BenchmarkQuestion("sets-23", "Among 720 users, 410 use A, 365 use B, and 205 use both. How many use neither?", ("A: 140", "B: 145", "C: 150", "D: 155")),
    BenchmarkQuestion("probability-23", "A box has 15 good and 5 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 16/38", "B: 17/38", "C: 18/38", "D: 19/38")),
    BenchmarkQuestion("bayes-23", "A condition has 25% prevalence. A test has 88% sensitivity and 82% specificity. What fraction of positive tests are true positives?", ("A: 42/71", "B: 43/71", "C: 44/71", "D: 45/71")),
    BenchmarkQuestion("modular-23", "What is the remainder when 2147 is divided by 47?", ("A: 30", "B: 31", "C: 32", "D: 33")),
    BenchmarkQuestion("ratio-23", "Split 1536 in the ratio 5:7. What is the smaller share?", ("A: 630", "B: 640", "C: 650", "D: 660")),
    BenchmarkQuestion("average-23", "What is the arithmetic mean (the sum divided by 5) of 18, 26, 31, 39, and 46?", ("A: 31", "B: 32", "C: 33", "D: 34")),
    BenchmarkQuestion("code-23", "Start x = 5. For n in [6, 8, 11], replace x with 2*x+n. What is final x?", ("A: 87", "B: 89", "C: 91", "D: 93")),
    BenchmarkQuestion("string-23", "Start with ABCDEFGH. Swap the two halves, then reverse each adjacent pair. What results?", ("A: HGFEDCBA", "B: EFGHABCD", "C: BADCFEHG", "D: FEHGBADC")),
    BenchmarkQuestion("unit-23", "A vehicle travels at 96 km/h for 3.25 hours. How far does it travel?", ("A: 302 km", "B: 307 km", "C: 312 km", "D: 317 km")),
)
_TRUTH_LABELS = {"arithmetic-23": "B", "rate-23": "B", "percent-23": "C",
                 "sets-23": "C", "probability-23": "B", "bayes-23": "C",
                 "modular-23": "C", "ratio-23": "B", "average-23": "B",
                 "code-23": "C", "string-23": "D", "unit-23": "C"}
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in _TRUTH_LABELS.items())
_VALUES = {
    "arithmetic-23": ("84", "4", "57"), "rate-23": ("3960", "44", "3.2"),
    "percent-23": ("18.75", "640"), "sets-23": ("720", "410", "365", "205"),
    "probability-23": ("15", "5"), "bayes-23": ("25", "88", "82"),
    "modular-23": ("2147", "47"), "ratio-23": ("1536", "5", "7"),
    "average-23": ("18", "26", "31", "39", "46", "5"),
    "code-23": ("5", "6", "8", "11", "2"), "string-23": ("ABCDEFGH",),
    "unit-23": ("96", "3.25"),
}
_PROBLEM_TRUTHS = {
    "arithmetic-23": ("NUMERIC_DERIVATION", "ARITHMETIC_COMPOSITION", "FINAL_SCALAR", "ORDER_SENSITIVE"),
    "rate-23": ("NUMERIC_DERIVATION", "RATE_SCALING", "SCALED_QUANTITY", "CONSTANT_RATE"),
    "percent-23": ("NUMERIC_DERIVATION", "PERCENTAGE", "SCALED_QUANTITY", "PERCENT_NORMALIZATION"),
    "sets-23": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "probability-23": ("NUMERIC_DERIVATION", "WITHOUT_REPLACEMENT", "PROBABILITY", "COMPLEMENT_EVENT"),
    "bayes-23": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "modular-23": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-23": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "average-23": ("NUMERIC_DERIVATION", "ARITHMETIC_MEAN", "MEAN", "CARDINALITY_NORMALIZATION"),
    "code-23": ("NUMERIC_DERIVATION", "ITERATIVE_UPDATE", "FINAL_STATE", "ORDER_SENSITIVE"),
    "string-23": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-23": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}
HOLDOUT_V22_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V22_QUESTIONS}
HOLDOUT_V22_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V22_QUESTIONS))
HOLDOUT_V22_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V22_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V22_ITEM_DOMAINS, HOLDOUT_V22_ITEM_FINGERPRINTS)


def build_holdout_v22_harness():
    return ProblemFormulationHarness(
        harness_id="local-reasoning-holdout-v22-harness", benchmark_id=HOLDOUT_V22_BENCHMARK_ID,
        questions=HOLDOUT_V22_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V22_EVIDENCE_REFS,
        derivation_values=_VALUES, problem_truths=_PROBLEM_TRUTHS,
    )
