"""Third frozen holdout for evidence-gated collaboration protocol v0.5."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion, FrozenAnswerBenchmarkHarness


HOLDOUT_V3_BENCHMARK_ID = "local-reasoning-holdout-v0-3"
HOLDOUT_V3_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V3_BENCHMARK_ID}",)

HOLDOUT_V3_QUESTIONS = (
    BenchmarkQuestion("logic-4", "All archivists are meticulous. No meticulous people are careless. Some researchers are archivists. Which statement must be true?", ("A: Some researchers are not careless", "B: All researchers are meticulous", "C: Some archivists are careless", "D: No researchers are careless")),
    BenchmarkQuestion("schedule-4", "Q must be before M, M before N, and P after N. Which order is valid?", ("A: M,Q,N,P", "B: Q,M,N,P", "C: Q,N,M,P", "D: Q,M,P,N")),
    BenchmarkQuestion("implication-4", "If A or B is true, then C is true. A is true. What follows?", ("A: C is false", "B: B must be false", "C: C is true", "D: Nothing follows about C")),
    BenchmarkQuestion("modular-4", "What is the least positive integer n such that n mod 4 = 1 and n mod 6 = 3?", ("A: 3", "B: 5", "C: 9", "D: 13")),
    BenchmarkQuestion("probability-4", "A bag has 5 white and 3 black balls. Two are drawn without replacement. What is the probability of drawing exactly one black ball?", ("A: 3/8", "B: 1/2", "C: 15/28", "D: 5/8")),
    BenchmarkQuestion("sets-4", "Among 80 users, 45 use A, 38 use B, and 18 use both. How many use neither?", ("A: 10", "B: 12", "C: 14", "D: 15")),
    BenchmarkQuestion("sequence-4", "What comes next in 5, 11, 19, 29, 41?", ("A: 51", "B: 53", "C: 55", "D: 57")),
    BenchmarkQuestion("rate-4", "A train travels 180 km in 2.25 hours at a constant speed. How far does it travel in 3.5 hours?", ("A: 260 km", "B: 280 km", "C: 300 km", "D: 315 km")),
    BenchmarkQuestion("bayes-4", "A condition has 5% prevalence. A test has 90% sensitivity and 95% specificity. Approximately what fraction of positive tests are true positives?", ("A: 1/3", "B: 1/2", "C: 2/3", "D: 9/10")),
    BenchmarkQuestion("code-4", "Start x = 3. For n in [1, 2, 3], replace x with 2*x + n. What is the final x?", ("A: 29", "B: 31", "C: 33", "D: 35")),
    BenchmarkQuestion("string-4", "Start with ABCDEF. Swap each adjacent pair, then rotate the result left by one character. What is the result?", ("A: BADCFE", "B: ADCFEB", "C: DCFBAE", "D: CFEADB")),
    BenchmarkQuestion("causal-4", "A scholarship is awarded when a score is at least 70. Which design best estimates its causal effect near the cutoff?", ("A: Compare all recipients with all nonrecipients", "B: Compare applicants just above and just below 70", "C: Study recipients only", "D: Ignore the assignment score")),
)

_HOLDOUT_V3_TRUTHS = (
    BenchmarkAnswerTruth("logic-4", "A"),
    BenchmarkAnswerTruth("schedule-4", "B"),
    BenchmarkAnswerTruth("implication-4", "C"),
    BenchmarkAnswerTruth("modular-4", "C"),
    BenchmarkAnswerTruth("probability-4", "C"),
    BenchmarkAnswerTruth("sets-4", "D"),
    BenchmarkAnswerTruth("sequence-4", "C"),
    BenchmarkAnswerTruth("rate-4", "B"),
    BenchmarkAnswerTruth("bayes-4", "B"),
    BenchmarkAnswerTruth("code-4", "D"),
    BenchmarkAnswerTruth("string-4", "B"),
    BenchmarkAnswerTruth("causal-4", "B"),
)

HOLDOUT_V3_ITEM_DOMAINS = {
    "logic-4": "formal", "schedule-4": "formal", "implication-4": "formal",
    "modular-4": "quantitative", "probability-4": "quantitative", "sets-4": "quantitative",
    "sequence-4": "quantitative", "rate-4": "quantitative", "bayes-4": "quantitative",
    "code-4": "procedural", "string-4": "procedural", "causal-4": "causal",
}


def build_holdout_v3_harness() -> FrozenAnswerBenchmarkHarness:
    return FrozenAnswerBenchmarkHarness(
        harness_id="local-reasoning-holdout-v3-harness",
        benchmark_id=HOLDOUT_V3_BENCHMARK_ID,
        questions=HOLDOUT_V3_QUESTIONS,
        truths=_HOLDOUT_V3_TRUTHS,
        evidence_refs=HOLDOUT_V3_EVIDENCE_REFS,
    )
