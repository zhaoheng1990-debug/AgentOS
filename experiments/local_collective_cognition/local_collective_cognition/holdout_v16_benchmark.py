"""Fresh holdout with public typed-derivation scaffolds for protocol v0.18."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains
from .typed_derivation_harness import TypedDerivationHarness


HOLDOUT_V16_BENCHMARK_ID = "local-reasoning-holdout-v0-16"
HOLDOUT_V16_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V16_BENCHMARK_ID}",)
HOLDOUT_V16_QUESTIONS = (
    BenchmarkQuestion("arithmetic-17", "What is (43 multiplied by 5) minus 68?", ("A: 145", "B: 146", "C: 147", "D: 148")),
    BenchmarkQuestion("rate-17", "A machine makes 2184 parts in 24 hours at a constant rate. How many in 4.5 hours?", ("A: 399.5", "B: 409.5", "C: 419.5", "D: 429.5")),
    BenchmarkQuestion("percent-17", "What is 17.5% of 640?", ("A: 102", "B: 112", "C: 122", "D: 132")),
    BenchmarkQuestion("sets-17", "Among 340 users, 210 use A, 175 use B, and 105 use both. How many use neither?", ("A: 50", "B: 55", "C: 60", "D: 65")),
    BenchmarkQuestion("probability-17", "A box has 9 good and 3 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 4/11", "B: 5/11", "C: 6/11", "D: 7/11")),
    BenchmarkQuestion("bayes-17", "A condition has 20% prevalence. A test has 85% sensitivity and 80% specificity. What fraction of positive tests are true positives?", ("A: 16/33", "B: 17/33", "C: 18/33", "D: 19/33")),
    BenchmarkQuestion("modular-17", "What is the remainder when 785 is divided by 23?", ("A: 1", "B: 2", "C: 3", "D: 4")),
    BenchmarkQuestion("ratio-17", "Split 630 in the ratio 4:5. What is the smaller share?", ("A: 270", "B: 280", "C: 290", "D: 300")),
    BenchmarkQuestion("average-17", "What is the arithmetic mean (the sum divided by 5) of 17, 20, 24, 29, and 35?", ("A: 23", "B: 24", "C: 25", "D: 26")),
    BenchmarkQuestion("code-17", "Start x = 6. For n in [1, 4, 7], replace x with 2*x+n. What is final x?", ("A: 63", "B: 65", "C: 67", "D: 69")),
    BenchmarkQuestion("string-17", "Start with QRSTUVWX. Swap the two halves, then reverse each adjacent pair. What results?", ("A: VUXWRQTS", "B: UVWXQRST", "C: XWVUTSRQ", "D: RQTSVUXW")),
    BenchmarkQuestion("unit-17", "A vehicle travels at 72 km/h for 2.75 hours. How far does it travel?", ("A: 188 km", "B: 193 km", "C: 198 km", "D: 203 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-17": "C", "rate-17": "B", "percent-17": "B", "sets-17": "C",
    "probability-17": "B", "bayes-17": "B", "modular-17": "C", "ratio-17": "B",
    "average-17": "C", "code-17": "C", "string-17": "A", "unit-17": "C",
}.items())
_VALUES = {
    "arithmetic-17": ("43", "5", "68"), "rate-17": ("2184", "24", "4.5"),
    "percent-17": ("17.5", "640"), "sets-17": ("340", "210", "175", "105"),
    "probability-17": ("9", "3"), "bayes-17": ("20", "85", "80"),
    "modular-17": ("785", "23"), "ratio-17": ("630", "4", "5"),
    "average-17": ("17", "20", "24", "29", "35", "5"),
    "code-17": ("6", "1", "4", "7", "2"), "string-17": ("QRSTUVWX",),
    "unit-17": ("72", "2.75"),
}
HOLDOUT_V16_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V16_QUESTIONS}
HOLDOUT_V16_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V16_QUESTIONS))
HOLDOUT_V16_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V16_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V16_ITEM_DOMAINS, HOLDOUT_V16_ITEM_FINGERPRINTS)


def build_holdout_v16_harness():
    return TypedDerivationHarness(
        harness_id="local-reasoning-holdout-v16-harness", benchmark_id=HOLDOUT_V16_BENCHMARK_ID,
        questions=HOLDOUT_V16_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V16_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
