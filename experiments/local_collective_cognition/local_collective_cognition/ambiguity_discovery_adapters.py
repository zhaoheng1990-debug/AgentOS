"""Compact discovery prompts for local small models and the Ollama ceiling."""

from __future__ import annotations

import json

from .ambiguity_discovery_contracts import TASK_KIND, state_order
from .local_transformers_provider import LocalTransformersJsonAdapter
from .ollama_provider import OllamaJsonAdapter


def ambiguity_discovery_messages(task):
    if task.task_kind != TASK_KIND:
        raise ValueError("ambiguity_discovery_adapter_task_kind_invalid")
    public = task.inputs["public_task"]
    ordered_states = state_order(public["item_id"])
    return [{"role": "system", "content": (
        "Classify the requested output object. Return one JSON object only. Do not solve the task, "
        "assume ambiguity, cite model identity, or claim authority."
    )}, {"role": "user", "content": (
        f"Choose discovery_state from this item-specific counterbalanced order: {json.dumps(ordered_states)}. "
        "Use AMBIGUITY_PRESENT only for two materially plausible incompatible output objects; then fill "
        "two rivals, decisive contrast, and a question ending in ?. If object, unit, boundary, direction, "
        "and operation are sufficiently explicit, use NO_MATERIAL_AMBIGUITY and leave all four text "
        "fields empty. UNCERTAIN also uses empty text fields. Return exactly these keys: item_id, "
        "discovery_state, rival_a, rival_b, decisive_contrast, discriminating_question, confidence, "
        "evidence_refs. Confidence must be your own number from 0 to 1; there is no default. Copy "
        f"item_id={json.dumps(public['item_id'])} and evidence_refs={json.dumps(task.allowed_evidence)} exactly. "
        f"Public task: {json.dumps(public['task'])}"
    )}]


class LocalAmbiguityDiscoveryAdapter(LocalTransformersJsonAdapter):
    def _messages(self, task):
        return ambiguity_discovery_messages(task)


class OllamaAmbiguityDiscoveryAdapter(OllamaJsonAdapter):
    def _messages(self, task):
        return ambiguity_discovery_messages(task)
