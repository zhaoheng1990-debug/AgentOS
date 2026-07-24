"""Fresh holdout for calibrated global plan-intent protocol v0.23."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .iterative_derivation_harness import IterativeDerivationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V21_BENCHMARK_ID = "local-reasoning-holdout-v0-21"
HOLDOUT_V21_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V21_BENCHMARK_ID}",)
HOLDOUT_V21_QUESTIONS = (
    BenchmarkQuestion("arithmetic-22", "What is (91 multiplied by 3) minus 38?", ("A: 225", "B: 235", "C: 245", "D: 255")),
    BenchmarkQuestion("rate-22", "A machine makes 4320 parts in 48 hours at a constant rate. How many in 3.6 hours?", ("A: 314", "B: 324", "C: 334", "D: 344")),
    BenchmarkQuestion("percent-22", "What is 12.5% of 744?", ("A: 88", "B: 93", "C: 98", "D: 103")),
    BenchmarkQuestion("sets-22", "Among 680 users, 405 use A, 330 use B, and 190 use both. How many use neither?", ("A: 125", "B: 130", "C: 135", "D: 140")),
    BenchmarkQuestion("probability-22", "A box has 14 good and 6 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 97/190", "B: 98/190", "C: 99/190", "D: 100/190")),
    BenchmarkQuestion("bayes-22", "A condition has 32% prevalence. A test has 85% sensitivity and 80% specificity. What fraction of positive tests are true positives?", ("A: 64/99", "B: 65/99", "C: 66/99", "D: 67/99")),
    BenchmarkQuestion("modular-22", "What is the remainder when 1775 is divided by 43?", ("A: 10", "B: 11", "C: 12", "D: 13")),
    BenchmarkQuestion("ratio-22", "Split 1344 in the ratio 3:5. What is the smaller share?", ("A: 484", "B: 494", "C: 504", "D: 514")),
    BenchmarkQuestion("average-22", "What is the arithmetic mean (the sum divided by 5) of 21, 27, 34, 38, and 45?", ("A: 31", "B: 32", "C: 33", "D: 34")),
    BenchmarkQuestion("code-22", "Start x = 4. For n in [7, 9, 12], replace x with 3*x+n. What is final x?", ("A: 204", "B: 206", "C: 208", "D: 210")),
    BenchmarkQuestion("string-22", "Start with QRSTUVWX. Swap the two halves, then reverse each adjacent pair. What results?", ("A: VUXWRQTS", "B: UVWXQRST", "C: XWVUTSRQ", "D: RQTSVUXW")),
    BenchmarkQuestion("unit-22", "A vehicle travels at 108 km/h for 2.5 hours. How far does it travel?", ("A: 250 km", "B: 260 km", "C: 270 km", "D: 280 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-22": "B", "rate-22": "B", "percent-22": "B", "sets-22": "C",
    "probability-22": "C", "bayes-22": "C", "modular-22": "C", "ratio-22": "C",
    "average-22": "C", "code-22": "D", "string-22": "A", "unit-22": "C",
}.items())
_VALUES = {
    "arithmetic-22": ("91", "3", "38"), "rate-22": ("4320", "48", "3.6"),
    "percent-22": ("12.5", "744"), "sets-22": ("680", "405", "330", "190"),
    "probability-22": ("14", "6"), "bayes-22": ("32", "85", "80"),
    "modular-22": ("1775", "43"), "ratio-22": ("1344", "3", "5"),
    "average-22": ("21", "27", "34", "38", "45", "5"),
    "code-22": ("4", "7", "9", "12", "3"), "string-22": ("QRSTUVWX",),
    "unit-22": ("108", "2.5"),
}
HOLDOUT_V21_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V21_QUESTIONS}
HOLDOUT_V21_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V21_QUESTIONS))
HOLDOUT_V21_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V21_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V21_ITEM_DOMAINS, HOLDOUT_V21_ITEM_FINGERPRINTS)


def build_holdout_v21_harness():
    return IterativeDerivationHarness(
        harness_id="local-reasoning-holdout-v21-harness", benchmark_id=HOLDOUT_V21_BENCHMARK_ID,
        questions=HOLDOUT_V21_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V21_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
