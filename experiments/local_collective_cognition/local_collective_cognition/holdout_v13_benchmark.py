"""Fresh exact-replay holdout for argument verification protocol v0.15."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V13_BENCHMARK_ID = "local-reasoning-holdout-v0-13"
HOLDOUT_V13_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V13_BENCHMARK_ID}",)
HOLDOUT_V13_QUESTIONS = (
    BenchmarkQuestion("arithmetic-14", "What is (18 multiplied by 7) minus 35?", ("A: 87", "B: 89", "C: 91", "D: 93")),
    BenchmarkQuestion("rate-14", "A machine makes 1260 parts in 21 hours at a constant rate. How many in 6.5 hours?", ("A: 375", "B: 390", "C: 405", "D: 420")),
    BenchmarkQuestion("percent-14", "What is 15% of 860?", ("A: 119", "B: 124", "C: 129", "D: 134")),
    BenchmarkQuestion("sets-14", "Among 240 users, 150 use A, 125 use B, and 80 use both. How many use neither?", ("A: 35", "B: 40", "C: 45", "D: 50")),
    BenchmarkQuestion("probability-14", "A box has 8 good and 4 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 17/33", "B: 18/33", "C: 19/33", "D: 20/33")),
    BenchmarkQuestion("bayes-14", "A condition has 10% prevalence. A test has 85% sensitivity and 90% specificity. What fraction of positive tests are true positives?", ("A: 8/17", "B: 17/35", "C: 1/2", "D: 18/35")),
    BenchmarkQuestion("modular-14", "What is the remainder when 347 is divided by 13?", ("A: 7", "B: 8", "C: 9", "D: 10")),
    BenchmarkQuestion("ratio-14", "Split 360 in the ratio 5:7. What is the smaller share?", ("A: 140", "B: 150", "C: 160", "D: 170")),
    BenchmarkQuestion("average-14", "What is the arithmetic mean (the sum divided by 5) of 14, 18, 23, 25, and 30?", ("A: 20", "B: 21", "C: 22", "D: 23")),
    BenchmarkQuestion("code-14", "Start x = 3. For n in [2, 4, 6], replace x with 2*x+n. What is final x?", ("A: 40", "B: 42", "C: 44", "D: 46")),
    BenchmarkQuestion("string-14", "Start with ABCDEFGH. Swap the two halves, then reverse each adjacent pair. What results?", ("A: FEHGBADC", "B: EFGHABCD", "C: HGFEDCBA", "D: BADCFEHG")),
    BenchmarkQuestion("unit-14", "A vehicle travels at 72 km/h for 2.75 hours. How far does it travel?", ("A: 188 km", "B: 198 km", "C: 208 km", "D: 218 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-14": "C", "rate-14": "B", "percent-14": "C", "sets-14": "C",
    "probability-14": "C", "bayes-14": "B", "modular-14": "C", "ratio-14": "B",
    "average-14": "C", "code-14": "D", "string-14": "A", "unit-14": "B",
}.items())
HOLDOUT_V13_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V13_QUESTIONS}
HOLDOUT_V13_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V13_QUESTIONS))
HOLDOUT_V13_ROUTING_FINGERPRINTS = {
    item_id: {
        "arithmetic_expression": "constant_rate",
        "percentage_calculation": "constant_rate",
        "proportional_allocation": "constant_rate",
        "arithmetic_mean": "difference_sequence",
        "unit_rate": "constant_rate",
    }.get(fingerprint, fingerprint)
    for item_id, fingerprint in HOLDOUT_V13_ITEM_FINGERPRINTS.items()
}
validate_fingerprint_domains(HOLDOUT_V13_ITEM_DOMAINS, HOLDOUT_V13_ITEM_FINGERPRINTS)


def build_holdout_v13_harness():
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v13-harness", benchmark_id=HOLDOUT_V13_BENCHMARK_ID,
        questions=HOLDOUT_V13_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V13_EVIDENCE_REFS,
    )
