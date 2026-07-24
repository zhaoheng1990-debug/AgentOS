"""Second frozen holdout for calibrated collaboration protocol v0.4."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness


HOLDOUT_V2_BENCHMARK_ID = "local-reasoning-holdout-v0-2"
HOLDOUT_V2_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V2_BENCHMARK_ID}",)

HOLDOUT_V2_QUESTIONS = (
    BenchmarkQuestion("logic-3", "No botanists are careless. Some researchers are botanists. Which statement must be true?", ("A: Some researchers are not careless", "B: All researchers are botanists", "C: Some careless people are botanists", "D: No researchers are careless")),
    BenchmarkQuestion("schedule-3", "G must be before H, H before J, and K after J. Which order is valid?", ("A: H,G,J,K", "B: G,J,H,K", "C: G,H,J,K", "D: G,H,K,J")),
    BenchmarkQuestion("implication-3", "If R then S. S is false. What follows?", ("A: R is true", "B: R is false", "C: S is true", "D: Nothing follows about R")),
    BenchmarkQuestion("modular-3", "What is the least positive integer n such that n mod 3 = 2 and n mod 5 = 4?", ("A: 5", "B: 8", "C: 11", "D: 14")),
    BenchmarkQuestion("probability-3", "A bag has 3 red and 2 blue balls. Two are drawn without replacement. What is the probability they have the same color?", ("A: 0.3", "B: 0.4", "C: 0.5", "D: 0.6")),
    BenchmarkQuestion("sets-3", "Among 60 users, 35 use A, 32 use B, and 20 use both. How many use neither?", ("A: 10", "B: 12", "C: 13", "D: 15")),
    BenchmarkQuestion("sequence-3", "What comes next in 2, 6, 12, 20, 30?", ("A: 36", "B: 38", "C: 40", "D: 42")),
    BenchmarkQuestion("rate-3", "A pump fills 3/8 of a tank in 6 minutes at a constant rate. How many minutes does it take to fill the tank?", ("A: 12", "B: 16", "C: 18", "D: 24")),
    BenchmarkQuestion("bayes-3", "A condition has 10% prevalence. A test has 90% sensitivity and 80% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 4/5")),
    BenchmarkQuestion("code-3", "Start x = 1. For n in [2, 3, 4], replace x with x*n - 1. What is the final x?", ("A: 7", "B: 11", "C: 15", "D: 19")),
    BenchmarkQuestion("string-3", "Start with ABCDEF. Move the last two characters to the front, then reverse the whole string. What is the result?", ("A: BAFEDC", "B: DCBAFE", "C: EFABCD", "D: FEDCBA")),
    BenchmarkQuestion("causal-3", "A training program is offered first to employees with the lowest prior scores. Which design best estimates its causal effect?", ("A: Compare participants with all nonparticipants without adjustment", "B: Compare only post-training scores", "C: Randomize eligible low-scoring employees to receive training now or later", "D: Exclude prior scores from analysis")),
)

_HOLDOUT_V2_TRUTHS = (
    BenchmarkAnswerTruth("logic-3", "A"),
    BenchmarkAnswerTruth("schedule-3", "C"),
    BenchmarkAnswerTruth("implication-3", "B"),
    BenchmarkAnswerTruth("modular-3", "D"),
    BenchmarkAnswerTruth("probability-3", "B"),
    BenchmarkAnswerTruth("sets-3", "C"),
    BenchmarkAnswerTruth("sequence-3", "D"),
    BenchmarkAnswerTruth("rate-3", "B"),
    BenchmarkAnswerTruth("bayes-3", "A"),
    BenchmarkAnswerTruth("code-3", "A"),
    BenchmarkAnswerTruth("string-3", "B"),
    BenchmarkAnswerTruth("causal-3", "C"),
)

HOLDOUT_V2_ITEM_DOMAINS = {
    "logic-3": "formal", "schedule-3": "formal", "implication-3": "formal",
    "modular-3": "quantitative", "probability-3": "quantitative", "sets-3": "quantitative",
    "sequence-3": "quantitative", "rate-3": "quantitative", "bayes-3": "quantitative",
    "code-3": "procedural", "string-3": "procedural", "causal-3": "causal",
}


def build_holdout_v2_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v2-harness",
        benchmark_id=HOLDOUT_V2_BENCHMARK_ID,
        questions=HOLDOUT_V2_QUESTIONS,
        truths=_HOLDOUT_V2_TRUTHS,
        evidence_refs=HOLDOUT_V2_EVIDENCE_REFS,
    )
