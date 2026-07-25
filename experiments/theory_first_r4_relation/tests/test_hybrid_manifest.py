import hashlib
import json
from pathlib import Path

from theory_first_r4_relation.semantic_cases import CASES
from theory_first_r4_relation.semantic_prompts import (
    SYSTEM_PROMPT,
    batch_prompt,
    single_prompt,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "research/theory_first_reset/"
    "R4_HYBRID_PRESENTATION_IMPLEMENTATION_MANIFEST_V0_3D.json"
)
SOURCE_DIR = (
    REPO_ROOT
    / "experiments/theory_first_r4_relation/theory_first_r4_relation"
)


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _prompt_hash(user_prompt: str) -> str:
    content = json.dumps(
        {"system": SYSTEM_PROMPT, "user": user_prompt},
        ensure_ascii=True,
        sort_keys=True,
    )
    return _sha_bytes(content.encode("utf-8"))


def test_frozen_source_and_prompt_hashes_match() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for name, expected in manifest["source_hashes"].items():
        assert _sha_bytes((SOURCE_DIR / name).read_bytes()) == expected
    prompts = {"batch_B": _prompt_hash(batch_prompt("B"))}
    prompts.update(
        {
            f"single_{case.case_id}": _prompt_hash(single_prompt(case, index))
            for index, case in enumerate(CASES)
        }
    )
    assert prompts == manifest["call_prompt_hashes"]


def test_public_case_payload_has_no_private_assignment() -> None:
    public = json.dumps(
        [case.public_dict() for case in CASES],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    forbidden = (
        "private_relation_state",
        "private_action",
        "relation_state",
        "DEDUPE_AND_COMBINE",
        "COMBINE",
        "BLOCK",
    )
    assert not any(value in public for value in forbidden)

