"""Fresh holdout for constrained enum/tool derivation protocol v0.21."""

from __future__ import annotations

from .frozen_answer_harness import BenchmarkAnswerTruth, BenchmarkQuestion
from .iterative_derivation_harness import IterativeDerivationHarness
from .task_fingerprints import build_item_fingerprints, validate_fingerprint_domains


HOLDOUT_V19_BENCHMARK_ID = "local-reasoning-holdout-v0-19"
HOLDOUT_V19_EVIDENCE_REFS = (f"benchmark://{HOLDOUT_V19_BENCHMARK_ID}",)
HOLDOUT_V19_QUESTIONS = (
    BenchmarkQuestion("arithmetic-20", "What is (73 multiplied by 3) minus 46?", ("A: 163", "B: 173", "C: 183", "D: 193")),
    BenchmarkQuestion("rate-20", "A machine makes 3360 parts in 42 hours at a constant rate. How many in 3.75 hours?", ("A: 290", "B: 300", "C: 310", "D: 320")),
    BenchmarkQuestion("percent-20", "What is 22.5% of 560?", ("A: 116", "B: 121", "C: 126", "D: 131")),
    BenchmarkQuestion("sets-20", "Among 520 users, 315 use A, 240 use B, and 155 use both. How many use neither?", ("A: 110", "B: 115", "C: 120", "D: 125")),
    BenchmarkQuestion("probability-20", "A box has 12 good and 4 defective parts. Two are drawn without replacement. What is the probability of at least one defective?", ("A: 8/20", "B: 9/20", "C: 10/20", "D: 11/20")),
    BenchmarkQuestion("bayes-20", "A condition has 35% prevalence. A test has 84% sensitivity and 78% specificity. What fraction of positive tests are true positives?", ("A: 292/437", "B: 293/437", "C: 294/437", "D: 295/437")),
    BenchmarkQuestion("modular-20", "What is the remainder when 1189 is divided by 37?", ("A: 4", "B: 5", "C: 6", "D: 7")),
    BenchmarkQuestion("ratio-20", "Split 960 in the ratio 11:13. What is the smaller share?", ("A: 430", "B: 440", "C: 450", "D: 460")),
    BenchmarkQuestion("average-20", "What is the arithmetic mean (the sum divided by 5) of 19, 24, 28, 36, and 43?", ("A: 28", "B: 29", "C: 30", "D: 31")),
    BenchmarkQuestion("code-20", "Start x = 5. For n in [4, 6, 11], replace x with 3*x+n. What is final x?", ("A: 196", "B: 198", "C: 200", "D: 202")),
    BenchmarkQuestion("string-20", "Start with ABCDEFGH. Swap the two halves, then reverse each adjacent pair. What results?", ("A: FEHGBADC", "B: EFGHABCD", "C: HGFEDCBA", "D: BADCFEHG")),
    BenchmarkQuestion("unit-20", "A vehicle travels at 84 km/h for 3.25 hours. How far does it travel?", ("A: 253 km", "B: 263 km", "C: 273 km", "D: 283 km")),
)
_TRUTHS = tuple(BenchmarkAnswerTruth(item_id, answer) for item_id, answer in {
    "arithmetic-20": "B", "rate-20": "B", "percent-20": "C", "sets-20": "C",
    "probability-20": "B", "bayes-20": "C", "modular-20": "B", "ratio-20": "B",
    "average-20": "C", "code-20": "C", "string-20": "A", "unit-20": "C",
}.items())
_VALUES = {
    "arithmetic-20": ("73", "3", "46"), "rate-20": ("3360", "42", "3.75"),
    "percent-20": ("22.5", "560"), "sets-20": ("520", "315", "240", "155"),
    "probability-20": ("12", "4"), "bayes-20": ("35", "84", "78"),
    "modular-20": ("1189", "37"), "ratio-20": ("960", "11", "13"),
    "average-20": ("19", "24", "28", "36", "43", "5"),
    "code-20": ("5", "4", "6", "11", "3"), "string-20": ("ABCDEFGH",),
    "unit-20": ("84", "3.25"),
}
HOLDOUT_V19_ITEM_DOMAINS = {item.item_id: "procedural" if item.item_id.startswith(("code", "string")) else "quantitative" for item in HOLDOUT_V19_QUESTIONS}
HOLDOUT_V19_ITEM_FINGERPRINTS = build_item_fingerprints(tuple(item.item_id for item in HOLDOUT_V19_QUESTIONS))
HOLDOUT_V19_ROUTING_FINGERPRINTS = {item_id: {"arithmetic_expression": "constant_rate", "percentage_calculation": "constant_rate", "proportional_allocation": "constant_rate", "arithmetic_mean": "difference_sequence", "unit_rate": "constant_rate"}.get(fingerprint, fingerprint) for item_id, fingerprint in HOLDOUT_V19_ITEM_FINGERPRINTS.items()}
validate_fingerprint_domains(HOLDOUT_V19_ITEM_DOMAINS, HOLDOUT_V19_ITEM_FINGERPRINTS)


def build_holdout_v19_harness():
    return IterativeDerivationHarness(
        harness_id="local-reasoning-holdout-v19-harness", benchmark_id=HOLDOUT_V19_BENCHMARK_ID,
        questions=HOLDOUT_V19_QUESTIONS, truths=_TRUTHS, evidence_refs=HOLDOUT_V19_EVIDENCE_REFS,
        derivation_values=_VALUES,
    )
