from copy import deepcopy
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[3]
PACK = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "agentos_core_slim_v0"), str(PACK)]

from local_collective_cognition.grammar_backed_role_adapter import (  # noqa: E402
    ROLE_OPTIONS,
    build_role_choice_registry,
    validate_role_choice_registry,
)


def test_registry_uses_opaque_per_object_calls_and_preserves_semantic_options():
    first = build_role_choice_registry(role_id="OBJECT_GROUNDING", object_ref="object://a", model_id="model-1")
    second = build_role_choice_registry(role_id="OBJECT_GROUNDING", object_ref="object://b", model_id="model-1")
    validate_role_choice_registry(first)
    assert {item["call"] for item in first["options"]}.isdisjoint({item["call"] for item in second["options"]})
    assert len(first["options"]) == len(ROLE_OPTIONS["OBJECT_GROUNDING"])
    assert all("CANDIDATE" not in item["call"] and "COMPLETE" not in item["call"] for item in first["options"])


def test_registry_rejects_reference_leak_or_semantic_call_label():
    registry = build_role_choice_registry(role_id="PRAGMATIC_DEFAULT", object_ref="object://a", model_id="model-1")
    leaked = deepcopy(registry)
    leaked["reference_value_present"] = True
    with pytest.raises(ValueError, match="registry_invalid"):
        validate_role_choice_registry(leaked)

