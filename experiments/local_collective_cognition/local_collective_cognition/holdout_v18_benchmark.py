"""Fresh holdout for two-stage action-specific derivation protocol v0.20."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .iterative_derivation_harness import IterativeDerivationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V18_BENCHMARK_ID = "local-reasoning-holdout-v0-18"
HOLDOUT_V18_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V18_BENCHMARK_ID}",)
HOLDOUT_V18_QUESTIONS = (
    BenchmarkQuestion("arithmetic-19", "What is (64 multiplied by 4) minus 39?", ("A: 207", "B: 217", "C: 227", "D: 237")),
    BenchmarkQuestion("rate-19", "A machine makes 2970 parts in 33 hours at a constant rate. How many in 3.5 hours?", ("A: 305", "B: 315", "C: 325", "D: 335")),
    BenchmarkQuestion("percent-19", "What is 17.5% of 640?", ("A: 102", "B: 107", "C: 112", "D: 117")),
    BenchmarkQuestion("sets-19", "Among 460 users, 280 use A, 210 use B, and 140 use both. How many use neither?", ("A: 100", "B: 105", "C: 110", "D: 115")),
    BenchmarkQuestion("probability-19", "A box has 11 good and 3 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 35/91", "B: 36/91", "C: 37/91", "D: 38/91")),
    BenchmarkQuestion("bayes-19", "A condition has 30% prevalence. A test has 90% sensitivity and 80% specificity. What fraction of positive tests are true positives?", ("A: 25/41", "B: 26/41", "C: 27/41", "D: 28/41")),
    BenchmarkQuestion("modular-19", "What is the remainder when 1047 is divided by 31?", ("A: 22", "B: 23", "C: 24", "D: 25")),
    BenchmarkQuestion("ratio-19", "Split 840 in the ratio 5:9. What is the smaller share?", ("A: 290", "B: 300", "C: 310", "D: 320")),
    BenchmarkQuestion("average-19", "What is the arithmetic mean (the sum divided by 5) of 16, 23, 27, 35, and 39?", ("A: 26", "B: 27", "C: 28", "D: 29")),
    BenchmarkQuestion("code-19", "Start x = 6. For n in [3, 7, 9], replace x with 2*x+n. What is final x?", ("A: 79", "B: 81", "C: 83", "D: 85")),
    BenchmarkQuestion("string-19", "Start with QRSTUVWX. Swap the two halves, then reverse each adjacent pair. What results?", ("A: VUXWRQTS", "B: UVWXQRST", "C: XWVUTSRQ", "D: RQTSVUXW")),
    BenchmarkQuestion("unit-19", "A vehicle travels at 96 km/h for 2.75 hours. How far does it travel?", ("A: 244 km", "B: 254 km", "C: 264 km", "D: 274 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-19": "B", "rate-19": "B", "percent-19": "C", "sets-19": "C",
    "probability-19": "B", "bayes-19": "C", "modular-19": "C", "ratio-19": "B",
    "average-19": "C", "code-19": "C", "string-19": "A", "unit-19": "C",
}.items())
_VALUES = {
    "arithmetic-19": ("64", "4", "39"), "rate-19": ("2970", "33", "3.5"),
    "percent-19": ("17.5", "640"), "sets-19": ("460", "280", "210", "140"),
    "probability-19": ("11", "3"), "bayes-19": ("30", "90", "80"),
    "modular-19": ("1047", "31"), "ratio-19": ("840", "5", "9"),
    "average-19": ("16", "23", "27", "35", "39", "5"),
    "code-19": ("6", "3", "7", "9", "2"), "string-19": ("QRSTUVWX",),
    "unit-19": ("96", "2.75"),
}
HOLDOUT_V18_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V18_QUESTIONS}
HOLDOUT_V18_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V18_QUESTIONS))
HOLDOUT_V18_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V18_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V18_ITEM_DOMAINS, HOLDOUT_V18_ITEM_FINGERPRINTS)


def build_holdout_v18_harness():
    return IterativeDerivationHarness(
        harness_id="local-reasoning-holdout-v18-harness", benchmark_id=HOLDOUT_V18_BENCHMARK_ID,
        questions=HOLDOUT_V18_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V18_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
