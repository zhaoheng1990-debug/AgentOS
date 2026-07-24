"""Harness-owned replay of Provider-supplied argument facts without hidden truth."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
from typing import Any

from .provider_telemetry import hash_payload


def _hash(value: Any) -> str:
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _fraction(value: str) -> Fraction:
    return Fraction(value.strip())


def same_value(left: str, right: str) -> bool:
    def numeric_text(value: str):
        matched = re.fullmatch(r"\s*(-?\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?)(?:\s+[A-Za-z/]+)?\s*", value)
        return matched.group(1) if matched else value
    try:
        return _fraction(numeric_text(left)) == _fraction(numeric_text(right))
    except (ValueError, ZeroDivisionError):
        return left.strip().upper() == right.strip().upper()


@dataclass(frozen=True)
class ArgumentVerificationReceipt:
    item_id: str
    candidate_id: str
    status: str
    replayed_fact_count: int
    failed_fact_ids: tuple[str, ...]
    conclusion_bound: bool
    argument_hash: str
    public_question_hash: str
    receipt_hash: str
    harness_owned: bool = True
    hidden_truth_used: bool = False

    def _committed(self) -> dict[str, Any]:
        return {
            **{key: value for key, value in self.__dict__.items() if key != "receipt_hash"},
            "failed_fact_ids": list(self.failed_fact_ids),
        }

    def __post_init__(self) -> None:
        if self.status not in {"VERIFIED", "FAILED"} or not self.harness_owned or self.hidden_truth_used:
            raise ValueError("argument_verification_authority_invalid")
        if self.receipt_hash != _hash(self._committed()):
            raise ValueError("argument_verification_commitment_invalid")

    def as_dict(self) -> dict[str, Any]:
        return {**self._committed(), "receipt_hash": self.receipt_hash}


class MechanicalArgumentVerifier:
    """Replay bounded arithmetic/string expressions; never consult benchmark truth."""

    def __init__(self, harness) -> None:
        self.harness = harness

    def verify(self, *, item_id: str, candidate_id: str, candidate_label: str, argument: dict[str, Any]):
        question = self.harness.provider_inputs((item_id,))["questions"][0]
        prompt = question["prompt"]
        allowed_numbers = {_fraction(item) for item in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", prompt)}
        if "%" in prompt:
            allowed_numbers.add(Fraction(100))
        allowed_numbers.update((Fraction(0), Fraction(1)))
        prior_values: list[str] = []
        failures = []
        for fact in argument["derived_facts"]:
            try:
                replayed = self._replay(fact["expression"], prompt, allowed_numbers, prior_values)
                if not same_value(replayed, fact["claimed_result"]):
                    raise ValueError("claimed_result_mismatch")
                prior_values.append(fact["claimed_result"].strip())
                try:
                    allowed_numbers.add(_fraction(fact["claimed_result"]))
                except (ValueError, ZeroDivisionError):
                    pass
            except (ValueError, SyntaxError, ZeroDivisionError):
                failures.append(fact["fact_id"])
        conclusion_bound = bool(prior_values) and same_value(argument["conclusion_value"], prior_values[-1])
        choice = next((item.split(":", 1)[1].strip() for item in question["choices"] if item.startswith(candidate_label + ":")), "")
        conclusion_bound = conclusion_bound and same_value(argument["conclusion_value"], choice)
        committed = {
            "item_id": item_id, "candidate_id": candidate_id,
            "status": "VERIFIED" if not failures and conclusion_bound else "FAILED",
            "replayed_fact_count": len(argument["derived_facts"]) - len(failures),
            "failed_fact_ids": failures, "conclusion_bound": conclusion_bound,
            "argument_hash": hash_payload(argument), "public_question_hash": _hash(question),
            "harness_owned": True, "hidden_truth_used": False,
        }
        return ArgumentVerificationReceipt(
            **{**committed, "failed_fact_ids": tuple(failures), "receipt_hash": _hash(committed)}
        )

    def replay_single(self, *, item_id: str, expression: str) -> tuple[str, dict[str, Any]]:
        question = self.harness.provider_inputs((item_id,))["questions"][0]
        prompt = question["prompt"]
        allowed = {_fraction(item) for item in re.findall(r"(?<![A-Za-z])\d+(?:\.\d+)?", prompt)}
        if "%" in prompt:
            allowed.add(Fraction(100))
        allowed.update((Fraction(0), Fraction(1)))
        return self._replay(expression, prompt, allowed, []), question

    def _replay(self, expression: str, prompt: str, allowed: set[Fraction], prior: list[str]) -> str:
        string_call = re.fullmatch(r"(SWAP_HALVES|REVERSE_PAIRS)\((.*)\)", expression.strip())
        if string_call:
            inner = string_call.group(2).strip()
            nested = inner.startswith(("SWAP_HALVES(", "REVERSE_PAIRS("))
            value = self._replay(inner, prompt, allowed, prior) if nested else inner
            if not nested and value not in prompt and value not in prior:
                raise ValueError("string_source_unbound")
            if len(value) % 2:
                raise ValueError("string_arity_invalid")
            if string_call.group(1) == "SWAP_HALVES":
                middle = len(value) // 2
                return value[middle:] + value[:middle]
            return "".join(value[index + 1] + value[index] for index in range(0, len(value), 2))
        tree = ast.parse(expression, mode="eval")
        if not any(isinstance(node, ast.BinOp) for node in ast.walk(tree)):
            raise ValueError("argument_expression_not_derived")
        return str(self._eval_node(tree.body, allowed))

    def _eval_node(self, node, allowed: set[Fraction]) -> Fraction:
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            value = Fraction(str(node.value))
            if value not in allowed:
                raise ValueError("numeric_source_unbound")
            return value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self._eval_node(node.operand, allowed)
            return value if isinstance(node.op, ast.UAdd) else -value
        if not isinstance(node, ast.BinOp):
            raise ValueError("argument_expression_operator_invalid")
        left, right = self._eval_node(node.left, allowed), self._eval_node(node.right, allowed)
        operations = {ast.Add: lambda: left + right, ast.Sub: lambda: left - right,
                      ast.Mult: lambda: left * right, ast.Div: lambda: left / right,
                      ast.Mod: lambda: left % right}
        operation = operations.get(type(node.op))
        if operation is None:
            raise ValueError("argument_expression_operator_invalid")
        return operation()
