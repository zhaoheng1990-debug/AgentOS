import hashlib
import json
from pathlib import Path

from theory_first_r4_relation.inference_cases import INFERENCE_CASES, PAIR_EXPECTATIONS
from theory_first_r4_relation.inference_prompts import SYSTEM_PROMPT, inference_batch_prompt


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "research/theory_first_reset"
    / "R4_PROVIDER_TRANSFORMATION_ATTRIBUTE_INFERENCE_CORPUS_MANIFEST_V0_3G.json"
)
MODULE_ROOT = (
    REPO_ROOT
    / "experiments/theory_first_r4_relation/theory_first_r4_relation"
)


def _hash_payload(value) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def test_frozen_manifest_matches_corpus_prompt_and_implementation() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    public = [case.public_dict() for case in INFERENCE_CASES]
    private = [
        {
            "case_id": case.case_id,
            "attributes": case.attributes(),
            "attribute_refs": case.attribute_refs(),
            "relation": case.expected_relation_state,
            "action": case.expected_action,
            "missing": case.true_missing_attributes,
        }
        for case in INFERENCE_CASES
    ]
    assert _hash_payload(public) == manifest["public_corpus_sha256"]
    assert _hash_payload(private) == manifest["private_reference_sha256"]
    assert _hash_payload(PAIR_EXPECTATIONS) == manifest["pair_expectations_sha256"]
    assert _hash_payload(
        {"system": SYSTEM_PROMPT, "user": inference_batch_prompt()}
    ) == manifest["executed_prompt_sha256"]
    for name, expected_hash in manifest["implementation_files"].items():
        assert (
            hashlib.sha256((MODULE_ROOT / name).read_bytes()).hexdigest()
            == expected_hash
        )

