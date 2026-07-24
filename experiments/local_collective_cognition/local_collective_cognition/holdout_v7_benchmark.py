"""Seventh frozen holdout for structural operator competition v0.9."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V7_BENCHMARK_ID = "local-reasoning-holdout-v0-7"
HOLDOUT_V7_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V7_BENCHMARK_ID}",)

HOLDOUT_V7_QUESTIONS = (
    BenchmarkQuestion("logic-8", "All archivists are organized. No organized people are careless. Some musicians are archivists. Which statement must be true?", ("A: Some musicians are not careless", "B: All musicians are organized", "C: Some archivists are careless", "D: No musicians are careless")),
    BenchmarkQuestion("schedule-8", "P must be before Q and R. Both Q and R must be before S. Which order is valid?", ("A: Q,P,R,S", "B: P,R,Q,S", "C: P,S,Q,R", "D: R,P,Q,S")),
    BenchmarkQuestion("implication-8", "If A then B. If B then C. C is false. Which statement must be true?", ("A: A is true", "B: B is true", "C: C is true", "D: A is false")),
    BenchmarkQuestion("modular-8", "What is the least positive integer n such that n mod 4 = 1 and n mod 6 = 3?", ("A: 5", "B: 9", "C: 13", "D: 17")),
    BenchmarkQuestion("probability-8", "A bag has 5 red and 4 blue balls. Two are drawn without replacement. What is the probability of drawing exactly one blue ball?", ("A: 4/9", "B: 1/2", "C: 5/9", "D: 2/3")),
    BenchmarkQuestion("sets-8", "Among 200 users, 110 use A, 95 use B, and 60 use both. How many use neither?", ("A: 35", "B: 40", "C: 45", "D: 55")),
    BenchmarkQuestion("sequence-8", "What comes next in 5, 9, 16, 26, 39?", ("A: 52", "B: 55", "C: 57", "D: 60")),
    BenchmarkQuestion("rate-8", "A processor completes 525 units in 7 hours at a constant rate. How many units does it complete in 4.4 hours?", ("A: 300", "B: 315", "C: 330", "D: 350")),
    BenchmarkQuestion("bayes-8", "A condition has 5% prevalence. A test has 90% sensitivity and 95% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 9/10")),
    BenchmarkQuestion("code-8", "Start x = 3. For n in [1, 2, 3], replace x with (x+n)*2. What is the final x?", ("A: 38", "B: 40", "C: 44", "D: 46")),
    BenchmarkQuestion("string-8", "Start with ABCDEF. Swap each adjacent pair, then rotate the result left by one character. What is the result?", ("A: ADCFEB", "B: BADFEC", "C: DCFEBA", "D: ADCFBE")),
    BenchmarkQuestion("causal-8", "A policy starts in one region but not another. Which comparison is the core difference-in-differences contrast?", ("A: Treated region after versus untreated region after", "B: Treated region before versus after", "C: Change over time in treated minus change over time in untreated", "D: Untreated region before versus after")),
)

_HOLDOUT_V7_TRUTHS = (
    BenchmarkAnswerTruth("logic-8", "A"), BenchmarkAnswerTruth("schedule-8", "B"),
    BenchmarkAnswerTruth("implication-8", "D"), BenchmarkAnswerTruth("modular-8", "B"),
    BenchmarkAnswerTruth("probability-8", "C"), BenchmarkAnswerTruth("sets-8", "D"),
    BenchmarkAnswerTruth("sequence-8", "B"), BenchmarkAnswerTruth("rate-8", "C"),
    BenchmarkAnswerTruth("bayes-8", "B"), BenchmarkAnswerTruth("code-8", "D"),
    BenchmarkAnswerTruth("string-8", "A"), BenchmarkAnswerTruth("causal-8", "C"),
)

HOLDOUT_V7_ITEM_DOMAINS = {
    "logic-8": "formal", "schedule-8": "formal", "implication-8": "formal",
    "modular-8": "quantitative", "probability-8": "quantitative", "sets-8": "quantitative",
    "sequence-8": "quantitative", "rate-8": "quantitative", "bayes-8": "quantitative",
    "code-8": "procedural", "string-8": "procedural", "causal-8": "causal",
}
HOLDOUT_V7_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V7_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V7_ITEM_DOMAINS, HOLDOUT_V7_ITEM_FINGERPRINTS)


def build_holdout_v7_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v7-harness", benchmark_id=HOLDOUT_V7_BENCHMARK_ID,
        questions=HOLDOUT_V7_QUESTIONS, truths=_HOLDOUT_V7_TRUTHS, evidence_refs=HOLDOUT_V7_EVIDENCE_REFS,
    )
