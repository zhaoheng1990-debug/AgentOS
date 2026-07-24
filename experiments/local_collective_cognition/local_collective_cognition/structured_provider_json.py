"""Shared structured-JSON prompt and parsing helpers for local adapters."""

from __future__ import annotations

import json
import re
from typing import Any

from agentos_kernel import ProviderCognitiveTask


def structured_json_messages(task: ProviderCognitiveTask) -> list[dict[str, str]]:
    visible_inputs = {key: value for key, value in task.inputs.items() if key != "audit_context"}
    return [
        {
            "role": "system",
            "content": (
                "You are one bounded AgentOS cognitive role. Return exactly one JSON object matching the "
                "provided schema. Do not include markdown or authority claims. Cite only admitted evidence."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Objective:\n{task.objective}\n\n"
                f"JSON schema:\n{json.dumps(task.expected_schema, sort_keys=True)}\n\n"
                f"Inputs:\n{json.dumps(visible_inputs, sort_keys=True, default=str)}"
            ),
        },
    ]


def parse_json_object(text: str) -> dict[str, Any]:
    value = text.strip()
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        start = value.find("{")
        if start < 0:
            raise ValueError("provider_response_contains_no_json_object") from None
        decoder = json.JSONDecoder()
        try:
            parsed, _ = decoder.raw_decode(value[start:])
        except json.JSONDecodeError as exc:
            raise ValueError("provider_response_json_invalid") from exc
    if not isinstance(parsed, dict):
        raise ValueError("provider_response_json_not_object")
    return parsed


def schema_failures(schema: dict[str, Any], result: dict[str, Any]) -> tuple[str, ...]:
    failures = [f"missing:{name}" for name in schema.get("required", ()) if name not in result]
    properties = schema.get("properties") or {}
    if schema.get("additionalProperties") is False:
        failures.extend(f"additionalProperty:{name}" for name in sorted(set(result) - set(properties)))
    expected_types = {"array": list, "object": dict, "string": str,
                      "number": (int, float), "integer": int, "boolean": bool}
    for name, spec in properties.items():
        if name not in result or spec.get("type") not in expected_types:
            continue
        expected = expected_types[spec["type"]]
        value = result[name]
        if not isinstance(value, expected) or spec["type"] in {"number", "integer"} and isinstance(value, bool):
            failures.append(f"type:{name}:{spec['type']}")
        elif "enum" in spec and value not in spec["enum"]:
            failures.append(f"enum:{name}")
        elif spec["type"] == "string" and len(value) < spec.get("minLength", 0):
            failures.append(f"minLength:{name}")
        elif spec["type"] == "string" and len(value) > spec.get("maxLength", len(value)):
            failures.append(f"maxLength:{name}")
        elif (spec["type"] == "string" and "pattern" in spec
              and re.fullmatch(spec["pattern"], value, flags=re.DOTALL) is None):
            failures.append(f"pattern:{name}")
        elif spec["type"] == "array" and len(value) < spec.get("minItems", 0):
            failures.append(f"minItems:{name}")
        elif spec["type"] == "array" and spec.get("items", {}).get("type") in expected_types:
            item_type = expected_types[spec["items"]["type"]]
            if any(not isinstance(item, item_type) for item in value):
                failures.append(f"items:{name}:{spec['items']['type']}")
        elif spec["type"] in {"number", "integer"} and "minimum" in spec and value < spec["minimum"]:
            failures.append(f"minimum:{name}")
        elif spec["type"] in {"number", "integer"} and "maximum" in spec and value > spec["maximum"]:
            failures.append(f"maximum:{name}")
    return tuple(failures)
