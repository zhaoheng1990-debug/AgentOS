"""Hidden direct-calibration cases for contrastive structure elicitation."""

from __future__ import annotations

from dataclasses import dataclass

from .provider_telemetry import hash_payload


BENCHMARK_ID = "local-structure-elicitor-calibration-v0-1"
EVIDENCE_REFS = (f"benchmark://{BENCHMARK_ID}",)


@dataclass(frozen=True)
class StructureElicitorCalibrationCase:
    item_id: str
    prompt: str
    rival_a_terms: tuple[str, ...]
    rival_b_terms: tuple[str, ...]
    question_terms: tuple[str, ...]

    def public_input(self):
        return {"item_id": self.item_id, "prompt": self.prompt}

    def truth_commitment(self):
        return hash_payload({
            "item_id": self.item_id,
            "rival_a_terms": list(self.rival_a_terms),
            "rival_b_terms": list(self.rival_b_terms),
            "question_terms": list(self.question_terms),
        })


CASES = (
    StructureElicitorCalibrationCase(
        "cal-bins", (
            "A storage controller receives 257 items and a capacity of 12 items per bin. "
            "It must emit one integer, but the specification does not say what that integer represents. "
            "Elicit the competing object structures and the deciding clarification; do not solve."
        ),
        ("quotient", "completed bins", "full bins", "number of bins", "groups"),
        ("remainder", "leftover", "remaining items", "unused items"),
        ("quotient", "remainder", "completed bins", "leftover", "output"),
    ),
    StructureElicitorCalibrationCase(
        "cal-ratio", (
            "A record gives a total quantity of 3450 and the relation 5:10, then requests one number. "
            "It is unclear whether the number is an allocated share or the common scale unit. "
            "Elicit both object structures and the deciding clarification; do not solve."
        ),
        ("allocated share", "smaller share", "partition", "allocation"),
        ("scale unit", "common unit", "multiplier", "ratio unit"),
        ("share", "scale", "allocation", "unit", "requested number"),
    ),
    StructureElicitorCalibrationCase(
        "cal-sets", (
            "A survey records a population, membership in A, membership in B, and their overlap, "
            "then requests one count without saying whether it means people in either set or in neither set. "
            "Elicit both object structures and the deciding clarification; do not solve."
        ),
        ("union", "either set", "at least one", "a or b"),
        ("neither", "complement", "outside both", "not in either"),
        ("union", "neither", "complement", "either set", "requested count"),
    ),
    StructureElicitorCalibrationCase(
        "cal-test", (
            "A diagnostic-test record supplies prevalence, sensitivity, and specificity, then asks for one "
            "probability without saying whether it means sensitivity or the probability of disease after a "
            "positive result. Elicit both object structures and the deciding clarification; do not solve."
        ),
        ("sensitivity", "true positive rate", "positive given disease", "p(+|disease)"),
        ("posterior", "positive predictive value", "disease given positive", "p(disease|+)"),
        ("sensitivity", "posterior", "given positive", "conditional direction", "requested probability"),
    ),
)


TRUTH_COMMITMENT = hash_payload([item.truth_commitment() for item in CASES])


def public_inputs(cases=CASES):
    return tuple(item.public_input() for item in cases)
