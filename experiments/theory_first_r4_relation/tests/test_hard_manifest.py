import hashlib
import json
from pathlib import Path

from theory_first_r4_relation.hard_cases import HARD_CASES
from theory_first_r4_relation.hard_prompts import (
    CASE_ORDER,
    SYSTEM_PROMPT,
    hard_batch_prompt,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = (
    REPO_ROOT
    / "research/theory_first_reset/"
    "R4_FRESH_HARD_RELATION_CORPUS_MANIFEST_V0_3E.json"
)
SOURCE_DIR = (
    REPO_ROOT
    / "experiments/theory_first_r4_relation/theory_first_r4_relation"
)


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def test_frozen_hard_sources_and_prompts_match() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for name, expected in manifest["source_hashes"].items():
        assert _sha((SOURCE_DIR / name).read_bytes()) == expected
    user_prompt = hard_batch_prompt()
    call = json.dumps(
        {"system": SYSTEM_PROMPT, "user": user_prompt},
        ensure_ascii=True,
        sort_keys=True,
    )
    assert _sha(SYSTEM_PROMPT.encode("utf-8")) == manifest["system_prompt_sha256"]
    assert _sha(user_prompt.encode("utf-8")) == manifest["user_prompt_sha256"]
    assert _sha(call.encode("utf-8")) == manifest["call_prompt_sha256"]
    assert (
        _sha(
            json.dumps(CASE_ORDER, separators=(",", ":")).encode("utf-8")
        )
        == manifest["case_order_sha256"]
    )


def test_frozen_public_and_private_surfaces_match() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    public = json.dumps(
        [case.public_dict() for case in HARD_CASES],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    private = json.dumps(
        [
            {
                "case_id": case.case_id,
                "state": case.private_relation_state,
                "action": case.private_action,
                "basis": case.private_adjudication_basis,
                "ruled_out": case.private_ruled_out_neighbor,
                "compatible": case.private_compatible_states,
            }
            for case in HARD_CASES
        ],
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    assert _sha(public.encode("utf-8")) == manifest["public_corpus_sha256"]
    assert _sha(private.encode("utf-8")) == manifest["private_reference_sha256"]

