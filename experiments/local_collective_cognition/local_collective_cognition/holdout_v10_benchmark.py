"""Tenth frozen holdout for disagreement-resolution context v0.12."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V10_BENCHMARK_ID = "local-reasoning-holdout-v0-10"
HOLDOUT_V10_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V10_BENCHMARK_ID}",)

HOLDOUT_V10_QUESTIONS = (
    BenchmarkQuestion("logic-11", "All sculptors are patient. No patient people are hasty. Some nurses are sculptors. Which statement must be true?", ("A: All nurses are patient", "B: No nurses are hasty", "C: Some nurses are not hasty", "D: Some sculptors are hasty")),
    BenchmarkQuestion("schedule-11", "A must be before B and C. Both B and C must be before D. Which order is valid?", ("A: B,A,C,D", "B: A,D,B,C", "C: C,A,B,D", "D: A,C,B,D")),
    BenchmarkQuestion("implication-11", "If P then Q. If Q then R. P is true. Which statement must be true?", ("A: R is true", "B: Q is false", "C: R is false", "D: Nothing follows")),
    BenchmarkQuestion("modular-11", "What is the least positive integer n such that n mod 6 = 1 and n mod 5 = 3?", ("A: 8", "B: 13", "C: 18", "D: 23")),
    BenchmarkQuestion("probability-11", "A batch has 7 good and 3 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 7/15", "B: 1/2", "C: 7/13", "D: 8/15")),
    BenchmarkQuestion("sets-11", "Among 160 users, 95 use A, 85 use B, and 50 use both. How many use neither?", ("A: 30", "B: 35", "C: 40", "D: 45")),
    BenchmarkQuestion("sequence-11", "What comes next in 2, 7, 14, 23, 34?", ("A: 44", "B: 45", "C: 47", "D: 49")),
    BenchmarkQuestion("rate-11", "A processor completes 840 units in 12 hours at a constant rate. How many units does it complete in 5.5 hours?", ("A: 350", "B: 360", "C: 375", "D: 385")),
    BenchmarkQuestion("bayes-11", "A condition has 5% prevalence. A test has 90% sensitivity and 95% specificity. What fraction of positive tests are true positives?", ("A: 18/37", "B: 1/2", "C: 2/3", "D: 18/19")),
    BenchmarkQuestion("code-11", "Start x = 1. For n in [1, 2, 3], replace x with 2*(x+n). What is the final x?", ("A: 28", "B: 30", "C: 32", "D: 34")),
    BenchmarkQuestion("string-11", "Start with ABCDEF. Reverse the whole string, then reverse each adjacent pair. What is the result?", ("A: FABCDE", "B: BADCFE", "C: EFCDBA", "D: EFCDAB")),
    BenchmarkQuestion("causal-11", "A regression-discontinuity design assigns treatment at a score cutoff. Which assumption identifies the local treatment effect?", ("A: Untreated potential outcomes are continuous at the cutoff", "B: Treatment is randomized everywhere", "C: Scores have no measurement error", "D: Treated and untreated groups have equal size")),
)

_HOLDOUT_V10_TRUTHS = (
    BenchmarkAnswerTruth("logic-11", "C"), BenchmarkAnswerTruth("schedule-11", "D"),
    BenchmarkAnswerTruth("implication-11", "A"), BenchmarkAnswerTruth("modular-11", "B"),
    BenchmarkAnswerTruth("probability-11", "D"), BenchmarkAnswerTruth("sets-11", "A"),
    BenchmarkAnswerTruth("sequence-11", "C"), BenchmarkAnswerTruth("rate-11", "D"),
    BenchmarkAnswerTruth("bayes-11", "A"), BenchmarkAnswerTruth("code-11", "B"),
    BenchmarkAnswerTruth("string-11", "D"), BenchmarkAnswerTruth("causal-11", "A"),
)

HOLDOUT_V10_ITEM_DOMAINS = {
    "logic-11": "formal", "schedule-11": "formal", "implication-11": "formal",
    "modular-11": "quantitative", "probability-11": "quantitative", "sets-11": "quantitative",
    "sequence-11": "quantitative", "rate-11": "quantitative", "bayes-11": "quantitative",
    "code-11": "procedural", "string-11": "procedural", "causal-11": "causal",
}
HOLDOUT_V10_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V10_QUESTIONS))
validate_fingerprint_domains(HOLDOUT_V10_ITEM_DOMAINS, HOLDOUT_V10_ITEM_FINGERPRINTS)


def build_holdout_v10_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v10-harness", benchmark_id=HOLDOUT_V10_BENCHMARK_ID,
        questions=HOLDOUT_V10_QUESTIONS, truths=_HOLDOUT_V10_TRUTHS, evidence_refs=HOLDOUT_V10_EVIDENCE_REFS,
    )
