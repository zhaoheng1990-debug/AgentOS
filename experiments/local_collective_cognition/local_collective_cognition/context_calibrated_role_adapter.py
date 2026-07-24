"""Role adapter using context-calibrated conditional likelihood instead of menu labels."""

from __future__ import annotations

import json
import time

from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .grammar_backed_role_adapter import (
    ROLE_ACTIONS,
    ROLE_OBJECTIVES,
    ROLE_OPTIONS,
    validate_grammar_output,
)
from .local_transformers_provider import LocalTransformersResidentPool
from .provider_telemetry import hash_payload


CONTEXT_ADAPTER_VERSION = "context_calibrated_role_adapter_v0_16"


class ContextCalibratedResidentPool(LocalTransformersResidentPool):
    def score_role_options(self, *, model_id, role_id, item):
        if not self.all_resident:
            raise RuntimeError("context_calibrated_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"context_calibrated_model_not_registered:{model_id}")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            descriptions = tuple(description for _, description in ROLE_OPTIONS[role_id])
            context_prompt = self._render_prompt(tokenizer, _score_messages(role_id=role_id, item=item, null_context=False))
            null_prompt = self._render_prompt(tokenizer, _score_messages(role_id=role_id, item=item, null_context=True))
            started = time.perf_counter()
            context_scores, context_tokens = _continuation_scores(
                tokenizer=tokenizer, model=model, prompt=context_prompt,
                continuations=descriptions, device=self.device,
            )
            null_scores, null_tokens = _continuation_scores(
                tokenizer=tokenizer, model=model, prompt=null_prompt,
                continuations=descriptions, device=self.device,
            )
            calibrated = tuple(context - null for context, null in zip(context_scores, null_scores))
            best = max(range(len(calibrated)), key=lambda index: (calibrated[index], -index))
            ordered = sorted(calibrated, reverse=True)
            margin = ordered[0] - ordered[1] if len(ordered) > 1 else 0.0
            return {
                "selected_index": best,
                "context_scores": list(context_scores),
                "null_scores": list(null_scores),
                "calibrated_scores": list(calibrated),
                "margin": margin,
                "input_tokens": context_tokens + null_tokens,
                "output_tokens": sum(len(tokenizer.encode(value, add_special_tokens=False)) for value in descriptions) * 2,
                "latency_ms": max(1, round((time.perf_counter() - started) * 1000)),
            }


class ContextCalibratedRoleAdapter:
    def __init__(self, *, model_id: str, pool: ContextCalibratedResidentPool) -> None:
        self.model_id = model_id
        self.pool = pool

    def invoke(self, *, role_id: str, item: dict, evidence_refs: tuple[str, ...]) -> dict:
        if role_id not in ROLE_OPTIONS:
            raise ValueError("context_calibrated_role_unknown")
        object_ref = "object://" + item["conflict_id"]
        scored = self.pool.score_role_options(model_id=self.model_id, role_id=role_id, item=item)
        result, description = ROLE_OPTIONS[role_id][scored["selected_index"]]
        uncertainty = _margin_uncertainty(scored["margin"])
        next_actions = ("CLARIFY",) if uncertainty >= 0.7 else ("FALSIFY", "SYNTHESIZE") if role_id == "OBJECT_GROUNDING" else ("SYNTHESIZE",)
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([CONTEXT_ADAPTER_VERSION, self.model_id, role_id, object_ref])[:18],
            action_type=ROLE_ACTIONS[role_id],
            object_ref=object_ref,
            actor_role=role_id,
            actor_instance=self.model_id,
            method=CONTEXT_ADAPTER_VERSION,
            result_state="OPEN" if uncertainty >= 0.7 else "CANDIDATE",
            result=result,
            evidence_refs=evidence_refs,
            support=(description,),
            uncertainty=uncertainty,
            recommended_next_actions=next_actions,
            cost=ActionCost(
                provider_calls=1,
                input_tokens=scored["input_tokens"],
                output_tokens=scored["output_tokens"],
                latency_ms=scored["latency_ms"],
            ),
        )
        validate_action_receipt(receipt)
        score_commitment = {
            "score_version": CONTEXT_ADAPTER_VERSION,
            "context_scores": scored["context_scores"],
            "null_scores": scored["null_scores"],
            "calibrated_scores": scored["calibrated_scores"],
            "selected_index": scored["selected_index"],
            "margin": scored["margin"],
            "context_object_present": True,
            "null_object_present": False,
            "reference_value_present": False,
        }
        score_receipt = {**score_commitment, "score_hash": hash_payload(score_commitment)}
        commitment = {
            "adapter_version": CONTEXT_ADAPTER_VERSION,
            "model_id": self.model_id,
            "role_id": role_id,
            "object_ref": object_ref,
            "registry_hash": hash_payload([CONTEXT_ADAPTER_VERSION, role_id, len(ROLE_OPTIONS[role_id])]),
            "selected_call": f"SCORE_OPTION_{scored['selected_index']}",
            "action_receipt": receipt,
            "score_receipt": score_receipt,
            "wall_latency_ms": scored["latency_ms"],
            "reference_available": False,
        }
        output = {**commitment, "output_hash": hash_payload(commitment)}
        validate_grammar_output(output, item=item)
        return output


def _score_messages(*, role_id, item, null_context):
    if null_context:
        object_text = "The object prompt and both candidate meanings are withheld for context calibration."
    else:
        public = {key: item[key] for key in ("public_prompt", "candidate_a", "candidate_b")}
        object_text = json.dumps(public, ensure_ascii=True, sort_keys=True)
    return [
        {"role": "system", "content": "You are one context-isolated cognitive role. Evaluate the object only within the assigned role."},
        {"role": "user", "content": f"Role objective:\n{ROLE_OBJECTIVES[role_id]}\n\nObject:\n{object_text}\n\nThe best assessment is:"},
    ]


def _continuation_scores(*, tokenizer, model, prompt, continuations, device):
    import torch

    prompt_ids = tokenizer.encode(prompt, add_special_tokens=False)
    continuation_ids = [tokenizer.encode(value, add_special_tokens=False) for value in continuations]
    if not prompt_ids or any(not values for values in continuation_ids):
        raise ValueError("context_calibrated_tokenization_empty")
    sequences = [prompt_ids + values for values in continuation_ids]
    maximum = max(len(values) for values in sequences)
    pad = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id
    if pad is None:
        raise ValueError("context_calibrated_pad_token_missing")
    input_ids = torch.full((len(sequences), maximum), int(pad), dtype=torch.long, device=device)
    attention = torch.zeros_like(input_ids)
    for row, values in enumerate(sequences):
        input_ids[row, :len(values)] = torch.tensor(values, dtype=torch.long, device=device)
        attention[row, :len(values)] = 1
    with torch.inference_mode():
        logits = model(input_ids=input_ids, attention_mask=attention).logits
        log_probs = torch.log_softmax(logits.float(), dim=-1)
    scores = []
    for row, values in enumerate(continuation_ids):
        token_scores = []
        for offset, token in enumerate(values):
            position = len(prompt_ids) + offset
            token_scores.append(float(log_probs[row, position - 1, token].item()))
        scores.append(sum(token_scores) / len(token_scores))
    processed = sum(len(values) for values in sequences)
    return tuple(scores), processed


def _margin_uncertainty(margin):
    if margin >= 0.5:
        return 0.2
    if margin >= 0.15:
        return 0.45
    return 0.75

