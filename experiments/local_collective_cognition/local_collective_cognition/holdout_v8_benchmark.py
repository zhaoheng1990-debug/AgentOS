"""Eighth frozen holdout for independent disagreement resolution v0.10."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V8_BENCHMARK_ID = "local-reasoning-holdout-v0-8"
HOLDOUT_V8_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V8_BENCHMARK_ID}",)

HOLDOUT_V8_QUESTIONS = (
    BenchmarkQuestion("logic-9", "All botanists are observant. No observant people are inattentive. Some engineers are botanists. Which statement must be true?", ("A: Some engineers are not inattentive", "B: All engineers are observant", "C: Some botanists are inattentive", "D: No engineers are inattentive")),
    BenchmarkQuestion("schedule-9", "H must be before J and K. Both J and K must be before L. Which order is valid?", ("A: J,H,K,L", "B: H,K,J,L", "C: H,L,J,K", "D: K,H,J,L")),
    BenchmarkQuestion("implication-9", "If U then V. If V then W. U is true. Which statement must be true?", ("A: V is false", "B: W is false", "C: W is true", "D: Nothing follows")),
    BenchmarkQuestion("modular-9", "What is the least positive integer n such that n mod 7 = 4 and n mod 5 = 2?", ("A: 12", "B: 18", "C: 25", "D: 32")),
    BenchmarkQuestion("probability-9", "A batch has 8 good and 2 defective parts. Three are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 7/15", "B: 1/2", "C: 8/15", "D: 3/5")),
    BenchmarkQuestion("sets-9", "Among 180 users, 100 use A, 90 use B, and 55 use both. How many use neither?", ("A: 35", "B: 40", "C: 45", "D: 55")),
    BenchmarkQuestion("sequence-9", "What comes next in 4, 10, 19, 31, 46?", ("A: 60", "B: 61", "C: 63", "D: 64")),
    BenchmarkQuestion("rate-9", "A processor completes 640 units in 8 hours at a constant rate. How many units does it complete in 3.75 hours?", ("A: 280", "B: 300", "C: 320", "D: 340")),
    BenchmarkQuestion("bayes-9", "A condition has 2% prevalence. A test has 95% sensitivity and 98% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 19/20")),
    BenchmarkQuestion("code-9", "Start x = 1. For n in [1, 2, 3], replace x with 3*x+n. What is the final x?", ("A: 39", "B: 42", "C: 44", "D: 45")),
    BenchmarkQuestion("string-9", "Start with ABCDEF. Reverse each adjacent pair, then rotate the result right by two characters. What is the result?", ("A: BADCFE", "B: FEBADC", "C: EFBADC", "D: CFEBAD")),
    BenchmarkQuestion("causal-9", "A randomized encouragement changes treatment uptake but has no direct effect on the outcome. What role can encouragement assignment play?", ("A: A post-treatment control", "B: A collider", "C: An instrumental variable", "D: An outcome proxy")),
)

_HOLDOUT_V8_TRUTHS = (
    BenchmarkAnswerTruth("logic-9", "A"), BenchmarkAnswerTruth("schedule-9", "B"),
    BenchmarkAnswerTruth("implication-9", "C"), BenchmarkAnswerTruth("modular-9", "D"),
    BenchmarkAnswerTruth("probability-9", "C"), BenchmarkAnswerTruth("sets-9", "C"),
    BenchmarkAnswerTruth("sequence-9", "D"), BenchmarkAnswerTruth("rate-9", "B"),
    BenchmarkAnswerTruth("bayes-9", "B"), BenchmarkAnswerTruth("code-9", "D"),
    BenchmarkAnswerTruth("string-9", "B"), BenchmarkAnswerTruth("causal-9", "C"),
)

HOLDOUT_V8_ITEM_DOMAINS = {
    "logic-9": "formal", "schedule-9": "formal", "implication-9": "formal",
    "modular-9": "quantitative", "probability-9": "quantitative", "sets-9": "quantitative",
    "sequence-9": "quantitative", "rate-9": "quantitative", "bayes-9": "quantitative",
    "code-9": "procedural", "string-9": "procedural", "causal-9": "causal",
}
HOLDOUT_V8_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V8_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V8_ITEM_DOMAINS, HOLDOUT_V8_ITEM_FINGERPRINTS)


def build_holdout_v8_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v8-harness", benchmark_id=HOLDOUT_V8_BENCHMARK_ID,
        questions=HOLDOUT_V8_QUESTIONS, truths=_HOLDOUT_V8_TRUTHS, evidence_refs=HOLDOUT_V8_EVIDENCE_REFS,
    )
