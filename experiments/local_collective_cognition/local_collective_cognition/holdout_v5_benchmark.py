"""Fifth frozen holdout for contextual arbitration protocol v0.7."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness


HOLDOUT_V5_BENCHMARK_ID = "local-reasoning-holdout-v0-5"
HOLDOUT_V5_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V5_BENCHMARK_ID}",)

HOLDOUT_V5_QUESTIONS = (
    BenchmarkQuestion("logic-6", "All pilots are attentive. No attentive people are reckless. Some doctors are pilots. Which statement must be true?", ("A: Some doctors are not reckless", "B: All doctors are pilots", "C: Some pilots are reckless", "D: No doctors are reckless")),
    BenchmarkQuestion("schedule-6", "A must be before B and C. Both B and C must be before D. Which order is valid?", ("A: B,A,C,D", "B: A,B,C,D", "C: A,D,B,C", "D: A,B,D,C")),
    BenchmarkQuestion("implication-6", "If X then Y. If not Y then Z. X is true. Which statement must be true?", ("A: Z is true", "B: Z is false", "C: Y is true", "D: Y is false")),
    BenchmarkQuestion("modular-6", "What is the least positive integer n such that n mod 6 = 5 and n mod 7 = 3?", ("A: 11", "B: 17", "C: 23", "D: 31")),
    BenchmarkQuestion("probability-6", "A batch has 6 good and 2 defective parts. Two are selected without replacement. What is the probability of selecting at least one defective part?", ("A: 3/14", "B: 5/14", "C: 13/28", "D: 1/2")),
    BenchmarkQuestion("sets-6", "Among 120 users, 70 use A, 65 use B, and 40 use both. How many use neither?", ("A: 15", "B: 20", "C: 25", "D: 30")),
    BenchmarkQuestion("sequence-6", "What comes next in 1, 4, 10, 19, 31?", ("A: 40", "B: 42", "C: 44", "D: 46")),
    BenchmarkQuestion("rate-6", "A processor completes 360 units in 4.8 hours at a constant rate. How many units does it complete in 2.6 hours?", ("A: 180", "B: 195", "C: 208", "D: 225")),
    BenchmarkQuestion("bayes-6", "A condition has 10% prevalence. A test has 85% sensitivity and 90% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 17/20")),
    BenchmarkQuestion("code-6", "Start x = 1. For n in [1, 2, 3], replace x with (x+n)*n. What is the final x?", ("A: 24", "B: 27", "C: 33", "D: 36")),
    BenchmarkQuestion("string-6", "Start with ABCDEF. Reverse each three-character block, then rotate the result right by one character. What is the result?", ("A: CBAFED", "B: FEDCBA", "C: EDCBAF", "D: DCBAFE")),
    BenchmarkQuestion("causal-6", "Access to a program is assigned by lottery, but some winners do not participate. Which comparison identifies the intention-to-treat effect?", ("A: Participants versus nonparticipants", "B: Lottery winners versus lottery losers", "C: Participants with the largest gains versus everyone else", "D: Winners who participated versus losers who later enrolled")),
)

_HOLDOUT_V5_TRUTHS = (
    BenchmarkAnswerTruth("logic-6", "A"), BenchmarkAnswerTruth("schedule-6", "B"),
    BenchmarkAnswerTruth("implication-6", "C"), BenchmarkAnswerTruth("modular-6", "B"),
    BenchmarkAnswerTruth("probability-6", "C"), BenchmarkAnswerTruth("sets-6", "C"),
    BenchmarkAnswerTruth("sequence-6", "D"), BenchmarkAnswerTruth("rate-6", "B"),
    BenchmarkAnswerTruth("bayes-6", "B"), BenchmarkAnswerTruth("code-6", "C"),
    BenchmarkAnswerTruth("string-6", "D"), BenchmarkAnswerTruth("causal-6", "B"),
)

HOLDOUT_V5_ITEM_DOMAINS = {
    "logic-6": "formal", "schedule-6": "formal", "implication-6": "formal",
    "modular-6": "quantitative", "probability-6": "quantitative", "sets-6": "quantitative",
    "sequence-6": "quantitative", "rate-6": "quantitative", "bayes-6": "quantitative",
    "code-6": "procedural", "string-6": "procedural", "causal-6": "causal",
}


def build_holdout_v5_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v5-harness",
        benchmark_id=HOLDOUT_V5_BENCHMARK_ID,
        questions=HOLDOUT_V5_QUESTIONS,
        truths=_HOLDOUT_V5_TRUTHS,
        evidence_refs=HOLDOUT_V5_EVIDENCE_REFS,
    )
