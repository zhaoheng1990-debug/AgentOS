"""Eleventh frozen holdout for pair-credit transfer protocol v0.13."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V11_BENCHMARK_ID = "local-reasoning-holdout-v0-11"
HOLDOUT_V11_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V11_BENCHMARK_ID}",)

HOLDOUT_V11_QUESTIONS = (
    BenchmarkQuestion("logic-12", "All botanists are observant. No observant people are careless. Some pilots are botanists. Which statement must be true?", ("A: All pilots are observant", "B: No pilots are careless", "C: Some pilots are not careless", "D: Some botanists are careless")),
    BenchmarkQuestion("schedule-12", "E must be before F and G. Both F and G must be before H. Which order is valid?", ("A: F,E,G,H", "B: E,H,F,G", "C: G,E,F,H", "D: E,G,F,H")),
    BenchmarkQuestion("implication-12", "If P then Q. If Q then R. R is false. Which statement must be true?", ("A: P is false", "B: Q is true", "C: P is true", "D: Nothing follows")),
    BenchmarkQuestion("modular-12", "What is the least positive integer n such that n mod 7 = 2 and n mod 5 = 4?", ("A: 4", "B: 9", "C: 16", "D: 23")),
    BenchmarkQuestion("probability-12", "A batch has 8 good and 4 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 14/33", "B: 1/2", "C: 19/33", "D: 2/3")),
    BenchmarkQuestion("sets-12", "Among 180 users, 110 use A, 90 use B, and 55 use both. How many use neither?", ("A: 35", "B: 40", "C: 45", "D: 50")),
    BenchmarkQuestion("sequence-12", "What comes next in 3, 8, 15, 24, 35?", ("A: 44", "B: 45", "C: 47", "D: 48")),
    BenchmarkQuestion("rate-12", "A processor completes 960 units in 16 hours at a constant rate. How many units does it complete in 6.25 hours?", ("A: 350", "B: 360", "C: 375", "D: 390")),
    BenchmarkQuestion("bayes-12", "A condition has 10% prevalence. A test has 85% sensitivity and 90% specificity. What fraction of positive tests are true positives?", ("A: 8/17", "B: 17/35", "C: 1/2", "D: 17/20")),
    BenchmarkQuestion("code-12", "Start x = 2. For n in [1, 2, 3], replace x with 3*(x+n). What is the final x?", ("A: 108", "B: 105", "C: 99", "D: 96")),
    BenchmarkQuestion("string-12", "Start with ABCDEF. Rotate right by two positions, then reverse each adjacent pair. What is the result?", ("A: EFABCD", "B: BADCFE", "C: FEBADC", "D: FABCDE")),
    BenchmarkQuestion("causal-12", "A difference-in-differences study compares treated and control groups before and after treatment. Which assumption identifies the treatment effect?", ("A: Treatment is randomized", "B: Outcomes have equal variance", "C: Groups have equal size", "D: The groups would have followed parallel trends without treatment")),
)

_HOLDOUT_V11_TRUTHS = (
    BenchmarkAnswerTruth("logic-12", "C"), BenchmarkAnswerTruth("schedule-12", "D"),
    BenchmarkAnswerTruth("implication-12", "A"), BenchmarkAnswerTruth("modular-12", "B"),
    BenchmarkAnswerTruth("probability-12", "C"), BenchmarkAnswerTruth("sets-12", "A"),
    BenchmarkAnswerTruth("sequence-12", "D"), BenchmarkAnswerTruth("rate-12", "C"),
    BenchmarkAnswerTruth("bayes-12", "B"), BenchmarkAnswerTruth("code-12", "A"),
    BenchmarkAnswerTruth("string-12", "C"), BenchmarkAnswerTruth("causal-12", "D"),
)

HOLDOUT_V11_ITEM_DOMAINS = {
    "logic-12": "formal", "schedule-12": "formal", "implication-12": "formal",
    "modular-12": "quantitative", "probability-12": "quantitative", "sets-12": "quantitative",
    "sequence-12": "quantitative", "rate-12": "quantitative", "bayes-12": "quantitative",
    "code-12": "procedural", "string-12": "procedural", "causal-12": "causal",
}
HOLDOUT_V11_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V11_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V11_ITEM_DOMAINS, HOLDOUT_V11_ITEM_FINGERPRINTS)


def build_holdout_v11_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v11-harness", benchmark_id=HOLDOUT_V11_BENCHMARK_ID,
        questions=HOLDOUT_V11_QUESTIONS, truths=_HOLDOUT_V11_TRUTHS, evidence_refs=HOLDOUT_V11_EVIDENCE_REFS,
    )
