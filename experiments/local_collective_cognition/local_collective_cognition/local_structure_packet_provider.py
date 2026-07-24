"""Local Provider transport specialized for free-text structure packets."""

from __future__ import annotations

import json
import re
import time

from .contrastive_structural_contracts import contrastive_batch_transport_failures
from .ephemeral_structural_prior_contracts import STRUCTURAL_PRIOR_TASK_KIND
from .local_contrastive_quality_provider import LocalContrastiveQualityAdapter


STRUCTURE_ELICITOR_ROLE = "batched_contrastive_structure_elicitor"


class LocalQualityGatedStructureAdapter(LocalContrastiveQualityAdapter):
    """Avoid presenting a full JSON Schema to small free-text elicitors."""

    def invoke(self, task):
        context = task.inputs.get("round_context", {})
        if (task.task_kind == STRUCTURAL_PRIOR_TASK_KIND
                and context.get("role") == STRUCTURE_ELICITOR_ROLE):
            return self._invoke_structure_packet(task)
        return super().invoke(task)

    def _invoke_structure_packet(self, task):
        attempts, last_error = [], ""
        messages = self._structure_messages(task)
        item_ids = tuple(task.inputs["benchmark_item_ids"])
        for _ in range(self.max_attempts):
            started = time.perf_counter()
            try:
                generated = self.pool.generate_json(
                    model_id=self.profile.model_id, messages=messages,
                    max_new_tokens=self.max_new_tokens,
                )
            except Exception as exc:
                attempts.append(self._record_failure(task, started, exc))
                last_error = type(exc).__name__
                continue
            failures = (
                (generated.parse_error or "provider_response_json_invalid",)
                if generated.result is None else contrastive_batch_transport_failures(
                    generated.result, item_ids=item_ids,
                )
            )
            result = generated.result
            if failures and len(item_ids) == 1:
                recovered = recover_single_packet_payload(generated.raw_text, f"item_1_packet")
                if recovered is not None:
                    result = recovered
                    failures = contrastive_batch_transport_failures(result, item_ids=item_ids)
            attempts.append(self._record_generation(
                task, generated, "FAILED" if failures else "COMPLETED", ";".join(failures),
            ))
            if not failures:
                return {
                    "result": result,
                    "usage": {
                        "input_tokens": sum(item.input_tokens for item in attempts),
                        "output_tokens": sum(item.output_tokens for item in attempts),
                        "cached_tokens": 0, "provider_calls": len(attempts),
                        "latency_ms": sum(item.latency_ms for item in attempts),
                    },
                    "provenance_refs": list(task.allowed_evidence),
                }
            last_error = ";".join(failures)
            messages.append({"role": "user", "content": (
                f"Rejected: {last_error}. Return only the requested packet-key JSON object."
            )})
        raise ValueError(f"local_structure_packet_output_invalid:{last_error}")

    @staticmethod
    def _structure_messages(task):
        keys = list(task.expected_schema.get("required", ()))
        public = task.inputs["benchmark_public_input"]
        questions = public.get("questions", []) if isinstance(public, dict) else []
        if len(keys) != len(questions):
            raise ValueError("structure_packet_public_input_binding_invalid")
        semantic_items = [
            {
                "output_key": key,
                "public_input": {
                    name: value for name, value in question.items()
                    if name not in {"item_id", "id"}
                },
            }
            for key, question in zip(keys, questions, strict=True)
        ]
        return [{"role": "system", "content": (
            "Elicit compact rival object structures from public inputs only. Return one JSON "
            "object, no markdown, schema description, answer label, or authority claim."
        )}, {"role": "user", "content": (
            f"Return exactly these keys and no others: {json.dumps(keys)}. "
            "Every value must be your actual analysis containing two complete rival object "
            "hypotheses, their decisive contrast, and one question that would discriminate "
            "between them. Use exactly this internal text grammar: RIVAL_A: ... | RIVAL_B: ... "
            "| CONTRAST: ... | QUESTION: ...? Do not copy instructions or emit placeholders, type, properties, "
            "required, additionalProperties, or any unlisted packet key.\n"
            "The output-key mapping below deliberately omits internal item identifiers. Never "
            "return an output key or identifier as packet content. "
            f"Semantic inputs: {json.dumps(semantic_items, sort_keys=True)}"
        )}]


_PACKET_GRAMMAR = re.compile(
    r"RIVAL_A:\s*.+?\s*\|\s*RIVAL_B:\s*.+?\s*\|\s*CONTRAST:\s*.+?\s*\|\s*QUESTION:\s*.+?\?",
    re.IGNORECASE | re.DOTALL,
)


def recover_single_packet_payload(raw_text, output_key):
    """Wrap one complete raw packet grammar without altering semantic content."""
    if not isinstance(raw_text, str) or not output_key:
        return None
    matches = _PACKET_GRAMMAR.findall(raw_text)
    if len(matches) != 1:
        return None
    packet = " ".join(matches[0].strip().split())
    return {output_key: packet} if len(packet) <= 1000 else None
