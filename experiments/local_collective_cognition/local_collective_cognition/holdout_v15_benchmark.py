"""Fresh holdout for candidate belief revision protocol v0.17."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .opportunity_harness import OpportunityFrozenAnswerHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V15_BENCHMARK_ID = "local-reasoning-holdout-v0-15"
HOLDOUT_V15_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V15_BENCHMARK_ID}",)
HOLDOUT_V15_QUESTIONS = (
    BenchmarkQuestion("arithmetic-16", "What is (37 multiplied by 4) minus 59?", ("A: 87", "B: 88", "C: 89", "D: 90")),
    BenchmarkQuestion("rate-16", "A machine makes 1848 parts in 28 hours at a constant rate. How many in 6.5 hours?", ("A: 409", "B: 419", "C: 429", "D: 439")),
    BenchmarkQuestion("percent-16", "What is 22% of 650?", ("A: 133", "B: 138", "C: 143", "D: 148")),
    BenchmarkQuestion("sets-16", "Among 310 users, 190 use A, 165 use B, and 95 use both. How many use neither?", ("A: 45", "B: 50", "C: 55", "D: 60")),
    BenchmarkQuestion("probability-16", "A box has 8 good and 4 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 17/33", "B: 18/33", "C: 19/33", "D: 20/33")),
    BenchmarkQuestion("bayes-16", "A condition has 15% prevalence. A test has 90% sensitivity and 85% specificity. What fraction of positive tests are true positives?", ("A: 16/35", "B: 17/35", "C: 18/35", "D: 19/35")),
    BenchmarkQuestion("modular-16", "What is the remainder when 647 is divided by 19?", ("A: 1", "B: 2", "C: 3", "D: 4")),
    BenchmarkQuestion("ratio-16", "Split 528 in the ratio 5:6. What is the smaller share?", ("A: 230", "B: 240", "C: 250", "D: 260")),
    BenchmarkQuestion("average-16", "What is the arithmetic mean (the sum divided by 5) of 14, 18, 23, 27, and 33?", ("A: 21", "B: 22", "C: 23", "D: 24")),
    BenchmarkQuestion("code-16", "Start x = 5. For n in [2, 4, 6], replace x with 2*x+n. What is final x?", ("A: 58", "B: 60", "C: 62", "D: 64")),
    BenchmarkQuestion("string-16", "Start with ABCDEFGH. Swap the two halves, then reverse each adjacent pair. What results?", ("A: FEHGBADC", "B: EFGHABCD", "C: HGFEDCBA", "D: BADCFEHG")),
    BenchmarkQuestion("unit-16", "A vehicle travels at 96 km/h for 1.75 hours. How far does it travel?", ("A: 158 km", "B: 168 km", "C: 178 km", "D: 188 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-16": "C", "rate-16": "C", "percent-16": "C", "sets-16": "B",
    "probability-16": "C", "bayes-16": "C", "modular-16": "A", "ratio-16": "B",
    "average-16": "C", "code-16": "C", "string-16": "A", "unit-16": "B",
}.items())
HOLDOUT_V15_ITEM_DOMAINS = {
    item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative"
    for item in HOLDOUT_V15_QUESTIONS
}
HOLDOUT_V15_ITEM_FINGERPRINTS = build_item_fingerprints(
    tuple(item.item_id for item in HOLDOUT_V15_QUESTIONS)
)
HOLDOUT_V15_ROUTING_FINGERPRINTS = {
    item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate",
              "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence",
              "unit_rate": "constant_rate"}.get(fingerprint, fingerprint)
    for item_id, fingerprint in HOLDOUT_V15_ITEM_FINGERPRINTS.items()
}
validate_fingerprint_domains(HOLDOUT_V15_ITEM_DOMAINS, HOLDOUT_V15_ITEM_FINGERPRINTS)


def build_holdout_v15_harness():
    return OpportunityFrozenAnswerHarness(
        harness_id="local-reasoning-holdout-v15-harness", benchmark_id=HOLDOUT_V15_BENCHMARK_ID,
        questions=HOLDOUT_V15_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V15_EVIDENCE_REFS,
    )
