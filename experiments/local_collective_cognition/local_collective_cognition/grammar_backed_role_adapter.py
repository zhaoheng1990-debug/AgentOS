"""Finite grammar adapter that lifts anonymous semantic choices into action receipts."""

from __future__ import annotations

import json
import re
import time

from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .constrained_generation import generate_constrained_call
from .local_transformers_provider import LocalTransformersResidentPool
from .provider_telemetry import hash_payload


GRAMMAR_ADAPTER_VERSION = "grammar_backed_role_adapter_v0_16"
GRAMMAR_TASK_KIND = "GRAMMAR_BACKED_SPECIALIST_ACTION"
ROLE_OUTPUT_VERSIONS = (
    GRAMMAR_ADAPTER_VERSION,
    "context_calibrated_role_adapter_v0_16",
    "staged_semantic_scoring_adapter_v0_16",
)

ROLE_OPTIONS = {
    "OBJECT_GROUNDING": (
        ({"selected_object": "CANDIDATE_A", "selection_basis": "LEXICAL_EXACT"}, "Candidate A is fixed by explicit lexical wording."),
        ({"selected_object": "CANDIDATE_A", "selection_basis": "COMPOSITIONAL_ENTAILMENT"}, "Candidate A is fixed by the composed meaning, though not by an exact phrase."),
        ({"selected_object": "CANDIDATE_B", "selection_basis": "LEXICAL_EXACT"}, "Candidate B is fixed by explicit lexical wording."),
        ({"selected_object": "CANDIDATE_B", "selection_basis": "COMPOSITIONAL_ENTAILMENT"}, "Candidate B is fixed by the composed meaning, though not by an exact phrase."),
        ({"selected_object": "NONE", "selection_basis": "PRAGMATIC_DEFAULT"}, "Neither candidate is semantically fixed, but one may be a useful contextual default."),
        ({"selected_object": "NONE", "selection_basis": "NO_PREFERENCE"}, "Neither candidate is semantically fixed and neither has a meaningful default advantage."),
        ({"selected_object": "UNCERTAIN", "selection_basis": "UNCERTAIN"}, "The displayed information is insufficient to assess semantic selection."),
    ),
    "PRAGMATIC_DEFAULT": (
        ({"pragmatic_preference": "CANDIDATE_A"}, "Candidate A is the more useful contextual default if clarification is unavailable."),
        ({"pragmatic_preference": "CANDIDATE_B"}, "Candidate B is the more useful contextual default if clarification is unavailable."),
        ({"pragmatic_preference": "NONE"}, "Neither candidate has a meaningful contextual-default advantage."),
        ({"pragmatic_preference": "UNCERTAIN"}, "The displayed information is insufficient to compare contextual defaults."),
    ),
    "ASSESSMENT_SKEPTIC": (
        ({"assessment_completeness": "COMPLETE"}, "The displayed prompt and candidate meanings are sufficient to complete the assessment, including a justified open result."),
        ({"assessment_completeness": "INCOMPLETE"}, "Missing information prevents even deciding whether an open result is warranted."),
        ({"assessment_completeness": "UNCERTAIN"}, "It is unclear whether the displayed information is sufficient to complete the assessment."),
    ),
}

ROLE_ACTIONS = {
    "OBJECT_GROUNDING": "DEFINE_OBJECT",
    "PRAGMATIC_DEFAULT": "COMPARE",
    "ASSESSMENT_SKEPTIC": "AUDIT_UNCERTAINTY",
}

ROLE_OBJECTIVES = {
    "OBJECT_GROUNDING": "Assess only semantic object selection and its strongest basis. Do not decide pragmatic preference or overall completeness.",
    "PRAGMATIC_DEFAULT": "Assess only the more useful contextual default if clarification is unavailable. Do not claim that preference semantically fixes the object.",
    "ASSESSMENT_SKEPTIC": "Assess only whether the displayed information is sufficient to complete the semantic assessment. A justified open result can be complete.",
}


class GrammarBackedResidentPool(LocalTransformersResidentPool):
    def generate_choice(self, *, model_id, messages, calls):
        if not self.all_resident:
            raise RuntimeError("grammar_backed_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"grammar_backed_model_not_registered:{model_id}")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            prompt = self._render_prompt(tokenizer, messages)
            return generate_constrained_call(
                tokenizer=tokenizer,
                model=model,
                prompt=prompt,
                calls=tuple(calls),
                device=self.device,
            )


def build_role_choice_registry(*, role_id: str, object_ref: str, model_id: str) -> dict:
    if role_id not in ROLE_OPTIONS:
        raise ValueError("grammar_backed_role_unknown")
    options = []
    for index, (result, description) in enumerate(ROLE_OPTIONS[role_id]):
        opaque = hash_payload([GRAMMAR_ADAPTER_VERSION, object_ref, model_id, role_id, index])[:8].upper()
        options.append({"call": f"CHOOSE_{opaque}", "description": description, "result": result})
    options.sort(key=lambda item: hash_payload([GRAMMAR_ADAPTER_VERSION, object_ref, model_id, item["call"]]))
    commitment = {
        "adapter_version": GRAMMAR_ADAPTER_VERSION,
        "role_id": role_id,
        "object_ref": object_ref,
        "model_id": model_id,
        "options": options,
        "reference_value_present": False,
        "fixed_semantic_label_in_call": False,
        "provider_semantic_choice": True,
        "harness_shape_authority": True,
    }
    return {**commitment, "registry_hash": hash_payload(commitment)}


def validate_role_choice_registry(registry: dict) -> None:
    commitment = {key: value for key, value in registry.items() if key != "registry_hash"}
    options = registry.get("options")
    calls = [item.get("call") for item in options or []]
    if (
        registry.get("registry_hash") != hash_payload(commitment)
        or registry.get("adapter_version") != GRAMMAR_ADAPTER_VERSION
        or registry.get("role_id") not in ROLE_OPTIONS
        or not options
        or len(calls) != len(set(calls))
        or any(not re.fullmatch(r"CHOOSE_[0-9A-F]{8}", call or "") for call in calls)
        or registry.get("reference_value_present") is not False
        or registry.get("fixed_semantic_label_in_call") is not False
        or registry.get("provider_semantic_choice") is not True
        or registry.get("harness_shape_authority") is not True
    ):
        raise ValueError("grammar_backed_registry_invalid")
    expected = {json.dumps(result, sort_keys=True) for result, _ in ROLE_OPTIONS[registry["role_id"]]}
    observed = {json.dumps(item.get("result"), sort_keys=True) for item in options}
    if observed != expected or any(not isinstance(item.get("description"), str) or not item["description"] for item in options):
        raise ValueError("grammar_backed_registry_semantics_invalid")


class GrammarBackedRoleAdapter:
    def __init__(self, *, model_id: str, pool: GrammarBackedResidentPool) -> None:
        self.model_id = model_id
        self.pool = pool

    def invoke(self, *, role_id: str, item: dict, evidence_refs: tuple[str, ...]) -> dict:
        object_ref = "object://" + item["conflict_id"]
        registry = build_role_choice_registry(role_id=role_id, object_ref=object_ref, model_id=self.model_id)
        validate_role_choice_registry(registry)
        by_call = {option["call"]: option for option in registry["options"]}
        started = time.perf_counter()
        generated = self.pool.generate_choice(
            model_id=self.model_id,
            messages=_choice_messages(role_id=role_id, item=item, registry=registry),
            calls=tuple(by_call),
        )
        option = by_call[generated.selected_call]
        uncertainty = 0.75 if "UNCERTAIN" in option["result"].values() else 0.35 if "NONE" in option["result"].values() else 0.15
        next_actions = ("CLARIFY",) if uncertainty >= 0.7 else ("FALSIFY", "SYNTHESIZE") if role_id == "OBJECT_GROUNDING" else ("SYNTHESIZE",)
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([GRAMMAR_ADAPTER_VERSION, self.model_id, role_id, object_ref])[:18],
            action_type=ROLE_ACTIONS[role_id],
            object_ref=object_ref,
            actor_role=role_id,
            actor_instance=self.model_id,
            method=GRAMMAR_ADAPTER_VERSION,
            result_state="OPEN" if uncertainty >= 0.7 else "CANDIDATE",
            result=option["result"],
            evidence_refs=evidence_refs,
            support=(option["description"],),
            uncertainty=uncertainty,
            recommended_next_actions=next_actions,
            cost=ActionCost(
                provider_calls=1,
                input_tokens=generated.input_tokens,
                output_tokens=generated.output_tokens,
                latency_ms=generated.latency_ms,
            ),
        )
        validate_action_receipt(receipt)
        commitment = {
            "adapter_version": GRAMMAR_ADAPTER_VERSION,
            "model_id": self.model_id,
            "role_id": role_id,
            "object_ref": object_ref,
            "registry_hash": registry["registry_hash"],
            "selected_call": generated.selected_call,
            "action_receipt": receipt,
            "wall_latency_ms": max(1, round((time.perf_counter() - started) * 1000)),
            "reference_available": False,
        }
        return {**commitment, "output_hash": hash_payload(commitment)}


def validate_grammar_output(output: dict, *, item: dict | None = None) -> None:
    commitment = {key: value for key, value in output.items() if key != "output_hash"}
    if output.get("output_hash") != hash_payload(commitment) or output.get("adapter_version") not in ROLE_OUTPUT_VERSIONS:
        raise ValueError("grammar_backed_output_invalid")
    validate_action_receipt(output["action_receipt"])
    if output["action_receipt"]["actor_instance"] != output["model_id"] or output["action_receipt"]["actor_role"] != output["role_id"]:
        raise ValueError("grammar_backed_output_actor_binding_invalid")
    if item is not None and output["object_ref"] != "object://" + item["conflict_id"]:
        raise ValueError("grammar_backed_output_object_binding_invalid")
    if output.get("reference_available") is not False:
        raise ValueError("grammar_backed_output_reference_leak")


def _choice_messages(*, role_id: str, item: dict, registry: dict) -> list[dict[str, str]]:
    menu = "\n".join(f"{option['call']}: {option['description']}" for option in registry["options"])
    public_item = {key: item[key] for key in ("public_prompt", "candidate_a", "candidate_b")}
    return [
        {
            "role": "system",
            "content": "You are one context-isolated cognitive role. Select exactly one anonymous registered call. Syntax is constrained; make only the semantic choice assigned to your role.",
        },
        {
            "role": "user",
            "content": f"Role objective:\n{ROLE_OBJECTIVES[role_id]}\n\nObject:\n{json.dumps(public_item, ensure_ascii=True, sort_keys=True)}\n\nRegistered choices:\n{menu}\n\nReturn one call only.",
        },
    ]
