"""Truth-blind state contract for hierarchical derivation choices."""

from __future__ import annotations

import json
from fractions import Fraction
from hashlib import sha256

from .typed_derivation_contracts import BINARY_OPERATORS


HIERARCHICAL_TOOL_CHANNEL_VERSION = "hierarchical_derivation_tool_channel_v0_22"
STRING_OPERATORS = ("SWAP_HALVES", "REVERSE_PAIRS")


def build_hierarchical_channel(*, symbol_values, prior_actions=(), allow_apply=True):
    numeric = [name for name, value in symbol_values.items() if _is_numeric(value)]
    strings = [name for name, value in symbol_values.items()
               if not _is_numeric(value) and len(str(value)) % 2 == 0]
    operators = [operator for operator in BINARY_OPERATORS
                 if _has_binary_choice(operator, numeric, symbol_values, prior_actions)]
    operators.extend(operator for operator in STRING_OPERATORS
                     if _has_unary_choice(operator, strings, prior_actions))
    payload = {
        "channel_version": HIERARCHICAL_TOOL_CHANNEL_VERSION,
        "allow_apply": bool(allow_apply), "operators": operators,
        "numeric_symbols": numeric, "string_symbols": strings,
        "step_symbols": [name for name in symbol_values if name.startswith("STEP_")],
        "symbol_values": dict(symbol_values),
        "prior_apply_actions": [
            {"operator": item["operator"], "inputs": list(item["inputs"])}
            for item in prior_actions if item.get("action") == "APPLY"
        ],
        "hidden_truth_used": False, "provider_semantic_choice": True,
        "adapter_shape_authority": True,
    }
    return {**payload, "channel_hash": _hash(payload)}


def validate_hierarchical_channel(channel):
    keys = {"channel_version", "allow_apply", "operators", "numeric_symbols",
            "string_symbols", "step_symbols", "symbol_values", "prior_apply_actions",
            "hidden_truth_used", "provider_semantic_choice", "adapter_shape_authority",
            "channel_hash"}
    if not isinstance(channel, dict) or set(channel) != keys:
        raise ValueError("hierarchical_tool_channel_shape_invalid")
    committed = {key: channel[key] for key in channel if key != "channel_hash"}
    if (channel["channel_version"] != HIERARCHICAL_TOOL_CHANNEL_VERSION
            or channel["channel_hash"] != _hash(committed)
            or channel["hidden_truth_used"] is not False):
        raise ValueError("hierarchical_tool_channel_binding_invalid")
    symbols = set(channel["symbol_values"])
    if any(name not in symbols for field in ("numeric_symbols", "string_symbols", "step_symbols")
           for name in channel[field]):
        raise ValueError("hierarchical_tool_channel_symbol_invalid")


def action_options(channel):
    values = []
    if channel["allow_apply"] and channel["operators"]:
        values.append("APPLY")
    if channel["step_symbols"]:
        values.append("FINALIZE")
    return (*values, "ABSTAIN")


def operand_options(channel, operator, *, left=None):
    symbols = channel["numeric_symbols"] if operator in BINARY_OPERATORS else channel["string_symbols"]
    prior = {(item["operator"], tuple(item["inputs"])) for item in channel["prior_apply_actions"]}
    if operator not in BINARY_OPERATORS:
        return tuple(name for name in symbols if (operator, (name,)) not in prior)
    if left is None:
        return tuple(name for name in symbols if any(
            _valid_pair(channel, operator, name, right, prior) for right in symbols
        ))
    return tuple(right for right in symbols if _valid_pair(channel, operator, left, right, prior))


def _valid_pair(channel, operator, left, right, prior):
    if operator in {"DIVIDE", "MODULO"} and Fraction(str(channel["symbol_values"][right])) == 0:
        return False
    return (operator, (left, right)) not in prior


def _has_binary_choice(operator, symbols, values, prior_actions):
    channel = {"numeric_symbols": symbols, "symbol_values": values,
               "prior_apply_actions": [{"operator": item.get("operator"),
                                         "inputs": item.get("inputs", [])}
                                        for item in prior_actions]}
    return bool(operand_options(channel, operator))


def _has_unary_choice(operator, symbols, prior_actions):
    prior = {(item.get("operator"), tuple(item.get("inputs", ()))) for item in prior_actions}
    return any((operator, (name,)) not in prior for name in symbols)


def _is_numeric(value):
    try:
        Fraction(str(value))
        return True
    except (ValueError, ZeroDivisionError):
        return False


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
