"""Frozen holdout benchmark for selective-collaboration protocol v0.3."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness


HOLDOUT_BENCHMARK_ID = "local-reasoning-holdout-v0-1"
HOLDOUT_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_BENCHMARK_ID}",)

HOLDOUT_QUESTIONS = (
    BenchmarkQuestion("logic-2", "All poets are readers. Some teachers are poets. Which statement must be true?", ("A: Some teachers are readers", "B: All teachers are readers", "C: No readers are teachers", "D: Some poets are not readers")),
    BenchmarkQuestion("schedule-2", "W must be before X, X before Z, and Z before Y. Which order is valid?", ("A: X,W,Z,Y", "B: W,Z,X,Y", "C: W,X,Z,Y", "D: W,X,Y,Z")),
    BenchmarkQuestion("implication-2", "The rule P implies Q is true, and P is true. What follows about Q?", ("A: Q is false", "B: Q is true", "C: Q is both true and false", "D: Nothing follows")),
    BenchmarkQuestion("modular-2", "What is the least positive integer n such that n mod 4 = 3 and n mod 5 = 2?", ("A: 3", "B: 5", "C: 6", "D: 7")),
    BenchmarkQuestion("probability-2", "A bag has 4 green and 1 yellow ball. Two are drawn without replacement. What is the probability of drawing at least one yellow?", ("A: 0.2", "B: 0.4", "C: 0.6", "D: 0.8")),
    BenchmarkQuestion("sets-2", "Among 50 users, 30 use A, 28 use B, and 15 use both. How many use neither?", ("A: 5", "B: 6", "C: 7", "D: 8")),
    BenchmarkQuestion("sequence-2", "What comes next in 3, 8, 15, 24, 35?", ("A: 44", "B: 45", "C: 46", "D: 48")),
    BenchmarkQuestion("rate-2", "A machine makes 150 parts in 12 minutes at a constant rate. How many does it make in 30 minutes?", ("A: 300", "B: 375", "C: 400", "D: 450")),
    BenchmarkQuestion("bayes-2", "A condition has 20% prevalence. A test has 80% sensitivity and 90% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 4/5")),
    BenchmarkQuestion("code-2", "Start y = 2. For n in [1, 2, 3], replace y with y + 2*n. What is the final y?", ("A: 14", "B: 12", "C: 10", "D: 8")),
    BenchmarkQuestion("string-2", "Start with ABCDE. Move the first character to the end, twice. What is the result?", ("A: BCDEA", "B: DEABC", "C: EABCD", "D: CDEAB")),
    BenchmarkQuestion("causal-2", "Disease severity affects both treatment choice and recovery. Which design best estimates the treatment's causal effect?", ("A: Compare treated and untreated records without adjustment", "B: Randomize treatment within comparable severity strata", "C: Remove severity from the dataset", "D: Study only recovered patients")),
)

_HOLDOUT_TRUTHS = (
    BenchmarkAnswerTruth("logic-2", "A"),
    BenchmarkAnswerTruth("schedule-2", "C"),
    BenchmarkAnswerTruth("implication-2", "B"),
    BenchmarkAnswerTruth("modular-2", "D"),
    BenchmarkAnswerTruth("probability-2", "B"),
    BenchmarkAnswerTruth("sets-2", "C"),
    BenchmarkAnswerTruth("sequence-2", "D"),
    BenchmarkAnswerTruth("rate-2", "B"),
    BenchmarkAnswerTruth("bayes-2", "C"),
    BenchmarkAnswerTruth("code-2", "A"),
    BenchmarkAnswerTruth("string-2", "D"),
    BenchmarkAnswerTruth("causal-2", "B"),
)

HOLDOUT_ITEM_DOMAINS = {
    "logic-2": "formal",
    "schedule-2": "formal",
    "implication-2": "formal",
    "modular-2": "quantitative",
    "probability-2": "quantitative",
    "sets-2": "quantitative",
    "sequence-2": "quantitative",
    "rate-2": "quantitative",
    "bayes-2": "quantitative",
    "code-2": "procedural",
    "string-2": "procedural",
    "causal-2": "causal",
}


def build_holdout_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-harness",
        benchmark_id=HOLDOUT_BENCHMARK_ID,
        questions=HOLDOUT_QUESTIONS,
        truths=_HOLDOUT_TRUTHS,
        evidence_refs=HOLDOUT_EVIDENCE_REFS,
    )
