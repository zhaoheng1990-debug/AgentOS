"""Fresh holdout for hierarchical enum-scored derivation protocol v0.22."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .iterative_derivation_harness import IterativeDerivationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V20_BENCHMARK_ID = "local-reasoning-holdout-v0-20"
HOLDOUT_V20_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V20_BENCHMARK_ID}",)
HOLDOUT_V20_QUESTIONS = (
    BenchmarkQuestion("arithmetic-21", "What is (86 multiplied by 4) minus 57?", ("A: 277", "B: 287", "C: 297", "D: 307")),
    BenchmarkQuestion("rate-21", "A machine makes 3780 parts in 45 hours at a constant rate. How many in 4.25 hours?", ("A: 347", "B: 357", "C: 367", "D: 377")),
    BenchmarkQuestion("percent-21", "What is 17.5% of 680?", ("A: 109", "B: 114", "C: 119", "D: 124")),
    BenchmarkQuestion("sets-21", "Among 610 users, 360 use A, 285 use B, and 170 use both. How many use neither?", ("A: 125", "B: 130", "C: 135", "D: 140")),
    BenchmarkQuestion("probability-21", "A box has 15 good and 5 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 15/38", "B: 16/38", "C: 17/38", "D: 18/38")),
    BenchmarkQuestion("bayes-21", "A condition has 28% prevalence. A test has 88% sensitivity and 82% specificity. What fraction of positive tests are true positives?", ("A: 152/235", "B: 153/235", "C: 154/235", "D: 155/235")),
    BenchmarkQuestion("modular-21", "What is the remainder when 1438 is divided by 41?", ("A: 2", "B: 3", "C: 4", "D: 5")),
    BenchmarkQuestion("ratio-21", "Split 1176 in the ratio 5:9. What is the smaller share?", ("A: 400", "B: 410", "C: 420", "D: 430")),
    BenchmarkQuestion("average-21", "What is the arithmetic mean (the sum divided by 5) of 17, 26, 31, 39, and 47?", ("A: 30", "B: 31", "C: 32", "D: 33")),
    BenchmarkQuestion("code-21", "Start x = 6. For n in [5, 8, 10], replace x with 2*x+n. What is final x?", ("A: 90", "B: 92", "C: 94", "D: 96")),
    BenchmarkQuestion("string-21", "Start with IJKLMNOP. Swap the two halves, then reverse each adjacent pair. What results?", ("A: NMPOJILK", "B: MNOPIJKL", "C: PONMLKJI", "D: JILKNMPO")),
    BenchmarkQuestion("unit-21", "A vehicle travels at 96 km/h for 2.75 hours. How far does it travel?", ("A: 254 km", "B: 264 km", "C: 274 km", "D: 284 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-21": "B", "rate-21": "B", "percent-21": "C", "sets-21": "C",
    "probability-21": "C", "bayes-21": "C", "modular-21": "B", "ratio-21": "C",
    "average-21": "C", "code-21": "C", "string-21": "A", "unit-21": "B",
}.items())
_VALUES = {
    "arithmetic-21": ("86", "4", "57"), "rate-21": ("3780", "45", "4.25"),
    "percent-21": ("17.5", "680"), "sets-21": ("610", "360", "285", "170"),
    "probability-21": ("15", "5"), "bayes-21": ("28", "88", "82"),
    "modular-21": ("1438", "41"), "ratio-21": ("1176", "5", "9"),
    "average-21": ("17", "26", "31", "39", "47", "5"),
    "code-21": ("6", "5", "8", "10", "2"), "string-21": ("IJKLMNOP",),
    "unit-21": ("96", "2.75"),
}
HOLDOUT_V20_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V20_QUESTIONS}
HOLDOUT_V20_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V20_QUESTIONS))
HOLDOUT_V20_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V20_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V20_ITEM_DOMAINS, HOLDOUT_V20_ITEM_FINGERPRINTS)


def build_holdout_v20_harness():
    return IterativeDerivationHarness(
        harness_id="local-reasoning-holdout-v20-harness", benchmark_id=HOLDOUT_V20_BENCHMARK_ID,
        questions=HOLDOUT_V20_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V20_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
