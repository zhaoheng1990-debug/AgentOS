"""Fresh holdout for single-expression adjudication and opportunity gate v0.16."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .opportunity_harness import OpportunityFrozenAnswerHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V14_BENCHMARK_ID = "local-reasoning-holdout-v0-14"
HOLDOUT_V14_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V14_BENCHMARK_ID}",)
HOLDOUT_V14_QUESTIONS = (
    BenchmarkQuestion("arithmetic-15", "What is (24 multiplied by 6) minus 47?", ("A: 95", "B: 96", "C: 97", "D: 98")),
    BenchmarkQuestion("rate-15", "A machine makes 1470 parts in 21 hours at a constant rate. How many in 5.5 hours?", ("A: 375", "B: 385", "C: 395", "D: 405")),
    BenchmarkQuestion("percent-15", "What is 18% of 750?", ("A: 125", "B: 130", "C: 135", "D: 140")),
    BenchmarkQuestion("sets-15", "Among 260 users, 155 use A, 130 use B, and 75 use both. How many use neither?", ("A: 45", "B: 50", "C: 55", "D: 60")),
    BenchmarkQuestion("probability-15", "A box has 7 good and 5 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 13/22", "B: 14/22", "C: 15/22", "D: 16/22")),
    BenchmarkQuestion("bayes-15", "A condition has 12% prevalence. A test has 80% sensitivity and 90% specificity. What fraction of positive tests are true positives?", ("A: 11/23", "B: 12/23", "C: 13/23", "D: 14/23")),
    BenchmarkQuestion("modular-15", "What is the remainder when 529 is divided by 17?", ("A: 1", "B: 2", "C: 3", "D: 4")),
    BenchmarkQuestion("ratio-15", "Split 420 in the ratio 3:4. What is the smaller share?", ("A: 170", "B: 180", "C: 190", "D: 200")),
    BenchmarkQuestion("average-15", "What is the arithmetic mean (the sum divided by 5) of 16, 19, 21, 24, and 30?", ("A: 21", "B: 22", "C: 23", "D: 24")),
    BenchmarkQuestion("code-15", "Start x = 4. For n in [1, 3, 5], replace x with 2*x+n. What is final x?", ("A: 43", "B: 45", "C: 47", "D: 49")),
    BenchmarkQuestion("string-15", "Start with IJKLMNOP. Swap the two halves, then reverse each adjacent pair. What results?", ("A: NMPOJILK", "B: MNOPIJKL", "C: PONMLKJI", "D: JILKNMPO")),
    BenchmarkQuestion("unit-15", "A vehicle travels at 84 km/h for 2.25 hours. How far does it travel?", ("A: 179 km", "B: 189 km", "C: 199 km", "D: 209 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-15": "C", "rate-15": "B", "percent-15": "C", "sets-15": "B",
    "probability-15": "C", "bayes-15": "B", "modular-15": "B", "ratio-15": "B",
    "average-15": "B", "code-15": "C", "string-15": "A", "unit-15": "B",
}.items())
HOLDOUT_V14_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V14_QUESTIONS}
HOLDOUT_V14_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V14_QUESTIONS))
HOLDOUT_V14_ROUTING_FINGERPRINTS = {
    item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate",
              "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence",
              "unit_rate": "constant_rate"}.get(fingerprint, fingerprint)
    for item_id, fingerprint in HOLDOUT_V14_ITEM_FINGERPRINTS.items()
}
validate_fingerprint_domains(HOLDOUT_V14_ITEM_DOMAINS, HOLDOUT_V14_ITEM_FINGERPRINTS)


def build_holdout_v14_harness():
    return OpportunityFrozenAnswerHarness(
        harness_id="local-reasoning-holdout-v14-harness", benchmark_id=HOLDOUT_V14_BENCHMARK_ID,
        questions=HOLDOUT_V14_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V14_EVIDENCE_REFS,
    )
