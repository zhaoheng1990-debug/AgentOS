"""Fresh holdout for problem-dialogue protocol v0.25."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .problem_dialogue_harness import ProblemDialogueHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V23_BENCHMARK_ID = "local-reasoning-holdout-v0-23"
HOLDOUT_V23_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V23_BENCHMARK_ID}",)
HOLDOUT_V23_QUESTIONS = (
    BenchmarkQuestion("arithmetic-24", "What is (73 multiplied by 5) minus 46?", ("A: 309", "B: 314", "C: 319", "D: 324")),
    BenchmarkQuestion("rate-24", "A machine makes 4550 parts in 35 hours at a constant rate. How many in 2.6 hours?", ("A: 328", "B: 338", "C: 348", "D: 358")),
    BenchmarkQuestion("percent-24", "What is 17.5% of 720?", ("A: 116", "B: 121", "C: 126", "D: 131")),
    BenchmarkQuestion("sets-24", "Among 680 users, 390 use A, 340 use B, and 180 use both. How many use neither?", ("A: 125", "B: 130", "C: 135", "D: 140")),
    BenchmarkQuestion("probability-24", "A box has 14 good and 6 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 96/190", "B: 97/190", "C: 98/190", "D: 99/190")),
    BenchmarkQuestion("bayes-24", "A condition has 20% prevalence. A test has 90% sensitivity and 85% specificity. What fraction of positive tests are true positives?", ("A: 9/20", "B: 1/2", "C: 11/20", "D: 3/5")),
    BenchmarkQuestion("modular-24", "What is the remainder when 2639 is divided by 53?", ("A: 39", "B: 40", "C: 41", "D: 42")),
    BenchmarkQuestion("ratio-24", "Split 1872 in the ratio 5:8. What is the smaller share?", ("A: 700", "B: 710", "C: 720", "D: 730")),
    BenchmarkQuestion("average-24", "What is the arithmetic mean (the sum divided by 5) of 22, 29, 35, 41, and 48?", ("A: 33", "B: 34", "C: 35", "D: 36")),
    BenchmarkQuestion("code-24", "Start x = 4. For n in [7, 9, 12], replace x with 2*x+n. What is final x?", ("A: 84", "B: 86", "C: 88", "D: 90")),
    BenchmarkQuestion("string-24", "Start with IJKLMNOP. Swap the two halves, then reverse each adjacent pair. What results?", ("A: PONMLKJI", "B: MNOPIJKL", "C: JILKNMPO", "D: NMPOJILK")),
    BenchmarkQuestion("unit-24", "A vehicle travels at 84 km/h for 3.75 hours. How far does it travel?", ("A: 305 km", "B: 310 km", "C: 315 km", "D: 320 km")),
)
_TRUTH_LABELS = {
    "arithmetic-24": "C", "rate-24": "B", "percent-24": "C", "sets-24": "B",
    "probability-24": "D", "bayes-24": "D", "modular-24": "D", "ratio-24": "C",
    "average-24": "C", "code-24": "D", "string-24": "D", "unit-24": "C",
}
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in _TRUTH_LABELS.items())
_VALUES = {
    "arithmetic-24": ("73", "5", "46"), "rate-24": ("4550", "35", "2.6"),
    "percent-24": ("17.5", "720"), "sets-24": ("680", "390", "340", "180"),
    "probability-24": ("14", "6"), "bayes-24": ("20", "90", "85"),
    "modular-24": ("2639", "53"), "ratio-24": ("1872", "5", "8"),
    "average-24": ("22", "29", "35", "41", "48", "5"),
    "code-24": ("4", "7", "9", "12", "2"), "string-24": ("IJKLMNOP",),
    "unit-24": ("84", "3.75"),
}
_PROBLEM_TRUTHS = {
    "arithmetic-24": ("NUMERIC_DERIVATION", "ARITHMETIC_COMPOSITION", "FINAL_SCALAR", "ORDER_SENSITIVE"),
    "rate-24": ("NUMERIC_DERIVATION", "RATE_SCALING", "SCALED_QUANTITY", "CONSTANT_RATE"),
    "percent-24": ("NUMERIC_DERIVATION", "PERCENTAGE", "SCALED_QUANTITY", "PERCENT_NORMALIZATION"),
    "sets-24": ("NUMERIC_DERIVATION", "SET_COMPLEMENT", "COMPLEMENT_COUNT", "INCLUSION_EXCLUSION"),
    "probability-24": ("NUMERIC_DERIVATION", "WITHOUT_REPLACEMENT", "PROBABILITY", "COMPLEMENT_EVENT"),
    "bayes-24": ("NUMERIC_DERIVATION", "BAYES_POSTERIOR", "POSTERIOR_PROBABILITY", "BASE_RATE_AND_FALSE_POSITIVE"),
    "modular-24": ("NUMERIC_DERIVATION", "MODULAR_REMAINDER", "REMAINDER", "DIVISION_REMAINDER"),
    "ratio-24": ("NUMERIC_DERIVATION", "RATIO_ALLOCATION", "ALLOCATED_SHARE", "RATIO_NORMALIZATION"),
    "average-24": ("NUMERIC_DERIVATION", "ARITHMETIC_MEAN", "MEAN", "CARDINALITY_NORMALIZATION"),
    "code-24": ("NUMERIC_DERIVATION", "ITERATIVE_UPDATE", "FINAL_STATE", "ORDER_SENSITIVE"),
    "string-24": ("STRING_TRANSFORMATION", "STRING_COMPOSITION", "TRANSFORMED_STRING", "ORDER_SENSITIVE"),
    "unit-24": ("NUMERIC_DERIVATION", "UNIT_DISTANCE", "DISTANCE", "UNIT_COMPOSITION"),
}
HOLDOUT_V23_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V23_QUESTIONS}
HOLDOUT_V23_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V23_QUESTIONS))
HOLDOUT_V23_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V23_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V23_ITEM_DOMAINS, HOLDOUT_V23_ITEM_FINGERPRINTS)


def build_holdout_v23_harness():
    return ProblemDialogueHarness(
        harness_id="local-reasoning-holdout-v23-harness", benchmark_id=HOLDOUT_V23_BENCHMARK_ID,
        questions=HOLDOUT_V23_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V23_EVIDENCE_REFS,
        derivation_values=_VALUES, problem_truths=_PROBLEM_TRUTHS,
    )
