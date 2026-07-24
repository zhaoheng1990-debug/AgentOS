"""Fresh holdout for bounded iterative derivation protocol v0.19."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .iterative_derivation_harness import IterativeDerivationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V17_BENCHMARK_ID = "local-reasoning-holdout-v0-17"
HOLDOUT_V17_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V17_BENCHMARK_ID}",)
HOLDOUT_V17_QUESTIONS = (
    BenchmarkQuestion("arithmetic-18", "What is (52 multiplied by 3) minus 47?", ("A: 99", "B: 109", "C: 119", "D: 129")),
    BenchmarkQuestion("rate-18", "A machine makes 2520 parts in 35 hours at a constant rate. How many in 4.25 hours?", ("A: 286", "B: 296", "C: 306", "D: 316")),
    BenchmarkQuestion("percent-18", "What is 12.5% of 880?", ("A: 100", "B: 110", "C: 120", "D: 130")),
    BenchmarkQuestion("sets-18", "Among 400 users, 245 use A, 190 use B, and 120 use both. How many use neither?", ("A: 75", "B: 80", "C: 85", "D: 90")),
    BenchmarkQuestion("probability-18", "A box has 10 good and 2 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 6/22", "B: 7/22", "C: 8/22", "D: 9/22")),
    BenchmarkQuestion("bayes-18", "A condition has 25% prevalence. A test has 88% sensitivity and 75% specificity. What fraction of positive tests are true positives?", ("A: 87/163", "B: 88/163", "C: 89/163", "D: 90/163")),
    BenchmarkQuestion("modular-18", "What is the remainder when 913 is divided by 29?", ("A: 12", "B: 13", "C: 14", "D: 15")),
    BenchmarkQuestion("ratio-18", "Split 720 in the ratio 7:8. What is the smaller share?", ("A: 326", "B: 336", "C: 346", "D: 356")),
    BenchmarkQuestion("average-18", "What is the arithmetic mean (the sum divided by 5) of 18, 22, 25, 31, and 34?", ("A: 24", "B: 25", "C: 26", "D: 27")),
    BenchmarkQuestion("code-18", "Start x = 7. For n in [2, 5, 8], replace x with 2*x+n. What is final x?", ("A: 78", "B: 80", "C: 82", "D: 84")),
    BenchmarkQuestion("string-18", "Start with YZABCDEF. Swap the two halves, then reverse each adjacent pair. What results?", ("A: DCFEZYBA", "B: CDEFYZAB", "C: FEDCBAZY", "D: ZYBADCFE")),
    BenchmarkQuestion("unit-18", "A vehicle travels at 88 km/h for 2.5 hours. How far does it travel?", ("A: 200 km", "B: 210 km", "C: 220 km", "D: 230 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-18": "B", "rate-18": "C", "percent-18": "B", "sets-18": "C",
    "probability-18": "B", "bayes-18": "B", "modular-18": "C", "ratio-18": "B",
    "average-18": "C", "code-18": "C", "string-18": "A", "unit-18": "C",
}.items())
_VALUES = {
    "arithmetic-18": ("52", "3", "47"), "rate-18": ("2520", "35", "4.25"),
    "percent-18": ("12.5", "880"), "sets-18": ("400", "245", "190", "120"),
    "probability-18": ("10", "2"), "bayes-18": ("25", "88", "75"),
    "modular-18": ("913", "29"), "ratio-18": ("720", "7", "8"),
    "average-18": ("18", "22", "25", "31", "34", "5"),
    "code-18": ("7", "2", "5", "8"), "string-18": ("YZABCDEF",),
    "unit-18": ("88", "2.5"),
}
HOLDOUT_V17_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V17_QUESTIONS}
HOLDOUT_V17_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V17_QUESTIONS))
HOLDOUT_V17_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V17_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V17_ITEM_DOMAINS, HOLDOUT_V17_ITEM_FINGERPRINTS)


def build_holdout_v17_harness():
    return IterativeDerivationHarness(
        harness_id="local-reasoning-holdout-v17-harness", benchmark_id=HOLDOUT_V17_BENCHMARK_ID,
        questions=HOLDOUT_V17_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V17_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
