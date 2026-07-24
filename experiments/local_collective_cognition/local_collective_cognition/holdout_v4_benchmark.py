"""Fourth frozen holdout for reliability-lifecycle protocol v0.6."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness


HOLDOUT_V4_BENCHMARK_ID = "local-reasoning-holdout-v0-4"
HOLDOUT_V4_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V4_BENCHMARK_ID}",)

HOLDOUT_V4_QUESTIONS = (
    BenchmarkQuestion("logic-5", "All engineers solve puzzles. Some musicians are engineers. No puzzle-solvers are impatient. Which statement must be true?", ("A: Some musicians are not impatient", "B: All musicians are engineers", "C: Some engineers are impatient", "D: No musicians are impatient")),
    BenchmarkQuestion("schedule-5", "R must be before S, S before U, and T after U. Which order is valid?", ("A: S,R,U,T", "B: R,S,U,T", "C: R,U,S,T", "D: R,S,T,U")),
    BenchmarkQuestion("implication-5", "If D then E, and if E then F. D is true. What follows?", ("A: E is false", "B: F is false", "C: F is true", "D: Nothing follows about F")),
    BenchmarkQuestion("modular-5", "What is the least positive integer n such that n mod 5 = 3 and n mod 7 = 4?", ("A: 11", "B: 18", "C: 23", "D: 33")),
    BenchmarkQuestion("probability-5", "A bag has 4 red and 3 blue balls. Two are drawn without replacement. What is the probability of drawing one ball of each color?", ("A: 2/7", "B: 1/2", "C: 4/7", "D: 5/7")),
    BenchmarkQuestion("sets-5", "Among 100 users, 55 use A, 48 use B, and 25 use both. How many use neither?", ("A: 20", "B: 22", "C: 25", "D: 28")),
    BenchmarkQuestion("sequence-5", "What comes next in 4, 9, 16, 25, 36?", ("A: 42", "B: 45", "C: 48", "D: 49")),
    BenchmarkQuestion("rate-5", "A scanner processes 240 pages in 3.2 hours at a constant rate. How many pages does it process in 4.5 hours?", ("A: 300", "B: 320", "C: 337.5", "D: 360")),
    BenchmarkQuestion("bayes-5", "A condition has 2% prevalence. A test has 95% sensitivity and 98% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 19/20")),
    BenchmarkQuestion("code-5", "Start x = 2. For n in [1, 2, 3], first replace x with x+n, then replace x with 2*x. What is the final x?", ("A: 24", "B: 30", "C: 34", "D: 38")),
    BenchmarkQuestion("string-5", "Start with ABCDE. Rotate right by two characters, then swap the first and last characters. What is the result?", ("A: DEABC", "B: CEABD", "C: CBADE", "D: EABCD")),
    BenchmarkQuestion("causal-5", "A program is introduced to eligible sites in a randomly assigned rollout order. Which comparison best estimates its causal effect?", ("A: Early sites before versus long after rollout without controls", "B: Sites assigned earlier versus later during the randomized rollout window", "C: Only sites with the largest improvement", "D: Sites that voluntarily adopted first")),
)

_HOLDOUT_V4_TRUTHS = (
    BenchmarkAnswerTruth("logic-5", "A"), BenchmarkAnswerTruth("schedule-5", "B"),
    BenchmarkAnswerTruth("implication-5", "C"), BenchmarkAnswerTruth("modular-5", "B"),
    BenchmarkAnswerTruth("probability-5", "C"), BenchmarkAnswerTruth("sets-5", "B"),
    BenchmarkAnswerTruth("sequence-5", "D"), BenchmarkAnswerTruth("rate-5", "C"),
    BenchmarkAnswerTruth("bayes-5", "B"), BenchmarkAnswerTruth("code-5", "D"),
    BenchmarkAnswerTruth("string-5", "B"), BenchmarkAnswerTruth("causal-5", "B"),
)

HOLDOUT_V4_ITEM_DOMAINS = {
    "logic-5": "formal", "schedule-5": "formal", "implication-5": "formal",
    "modular-5": "quantitative", "probability-5": "quantitative", "sets-5": "quantitative",
    "sequence-5": "quantitative", "rate-5": "quantitative", "bayes-5": "quantitative",
    "code-5": "procedural", "string-5": "procedural", "causal-5": "causal",
}


def build_holdout_v4_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v4-harness",
        benchmark_id=HOLDOUT_V4_BENCHMARK_ID,
        questions=HOLDOUT_V4_QUESTIONS,
        truths=_HOLDOUT_V4_TRUTHS,
        evidence_refs=HOLDOUT_V4_EVIDENCE_REFS,
    )
