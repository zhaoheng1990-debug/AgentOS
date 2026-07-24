"""Finite truth-blind tool registry for constrained derivation actions."""

from __future__ import annotations

import json
from fractions import Fraction
from hashlib import sha256

from .candidate_revision_contracts import CHOICE_LABELS
from .constrained_tool_contract import canonical_tool_call
from .typed_derivation_contracts import BINARY_OPERATORS


CONSTRAINED_TOOL_CHANNEL_VERSION = "constrained_derivation_tool_channel_v0_21"
NUMERIC_OPERATORS = tuple(BINARY_OPERATORS)
STRING_OPERATORS = ("SWAP_HALVES", "REVERSE_PAIRS")


def build_tool_registry(*, item_id, candidate_id, evidence_refs, symbol_values,
                        prior_actions=(), allow_apply=True):
    options = []
    if allow_apply:
        options.extend(_apply_options(
            item_id, candidate_id, evidence_refs, symbol_values, prior_actions,
        ))
    step_ids = tuple(name for name in symbol_values if name.startswith("STEP_"))
    for step_id in step_ids:
        for label in CHOICE_LABELS:
            options.append(_option(
                f"FINALIZE({step_id},{label})", item_id, candidate_id, evidence_refs,
                action="FINALIZE", operator="NONE", inputs=[step_id], proposed_candidate=label,
            ))
    options.append(_option(
        "ABSTAIN()", item_id, candidate_id, evidence_refs,
        action="ABSTAIN", operator="NONE", inputs=[], proposed_candidate="ABSTAIN",
    ))
    payload = {
        "channel_version": CONSTRAINED_TOOL_CHANNEL_VERSION,
        "options": options,
        "summary": {
            "available_symbols": dict(symbol_values),
            "available_steps": list(step_ids),
            "registered_call_count": len(options),
            "registered_actions": sorted({item["result"]["action"] for item in options}),
            "registered_operators": sorted({item["result"]["operator"] for item in options}),
            "provider_semantic_choice": True,
            "adapter_shape_authority": True,
            "hidden_truth_used": False,
        },
    }
    return {**payload, "registry_hash": _hash(payload)}


def validate_tool_registry(registry):
    if (not isinstance(registry, dict)
            or not {"channel_version", "options", "summary", "registry_hash"}.issubset(registry)):
        raise ValueError("constrained_tool_registry_invalid")
    committed = {key: registry[key] for key in ("channel_version", "options", "summary")}
    if (registry.get("channel_version") != CONSTRAINED_TOOL_CHANNEL_VERSION
            or registry.get("registry_hash") != _hash(committed)
            or not registry.get("options")):
        raise ValueError("constrained_tool_registry_invalid")
    calls = [item.get("call") for item in registry["options"]]
    if (any(not isinstance(item, str) or not item for item in calls)
            or len(calls) != len(set(calls))):
        raise ValueError("constrained_tool_calls_invalid")
    if any(set(item) != {"call", "result"}
           or canonical_tool_call(item["result"]) != item["call"]
           for item in registry["options"]):
        raise ValueError("constrained_tool_call_result_binding_invalid")
    if registry["summary"].get("registered_call_count") != len(calls):
        raise ValueError("constrained_tool_registry_count_invalid")
    if registry["summary"].get("hidden_truth_used") is not False:
        raise ValueError("constrained_tool_truth_boundary_invalid")


def registry_prompt_view(registry):
    validate_tool_registry(registry)
    return {"channel_version": registry["channel_version"],
            "registry_hash": registry["registry_hash"], **registry["summary"]}


def _apply_options(item_id, candidate_id, evidence_refs, symbols, prior_actions):
    prior = {(item.get("operator"), tuple(item.get("inputs", ()))) for item in prior_actions
             if item.get("action") == "APPLY"}
    numeric = {name: _fraction(value) for name, value in symbols.items() if _is_numeric(value)}
    strings = {name: str(value) for name, value in symbols.items()
               if not _is_numeric(value) and len(str(value)) % 2 == 0}
    options = []
    for operator in NUMERIC_OPERATORS:
        for left in numeric:
            for right, denominator in numeric.items():
                if operator in {"DIVIDE", "MODULO"} and denominator == 0:
                    continue
                if (operator, (left, right)) in prior:
                    continue
                options.append(_option(
                    f"APPLY({operator},{left},{right})", item_id, candidate_id, evidence_refs,
                    action="APPLY", operator=operator, inputs=[left, right],
                    proposed_candidate="PENDING",
                ))
    for operator in STRING_OPERATORS:
        for symbol in strings:
            if (operator, (symbol,)) not in prior:
                options.append(_option(
                    f"APPLY({operator},{symbol})", item_id, candidate_id, evidence_refs,
                    action="APPLY", operator=operator, inputs=[symbol],
                    proposed_candidate="PENDING",
                ))
    return options


def _option(call, item_id, candidate_id, evidence_refs, **action):
    return {"call": call, "result": {"item_id": item_id, "candidate_id": candidate_id,
                                      **action, "evidence_refs": list(evidence_refs)}}


def _is_numeric(value):
    try:
        _fraction(value)
        return True
    except (ValueError, ZeroDivisionError):
        return False


def _fraction(value):
    return Fraction(str(value))


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
