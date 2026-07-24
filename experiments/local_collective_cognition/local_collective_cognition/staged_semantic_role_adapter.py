"""Staged short-label scoring with null calibration and A/B orientation control."""

from __future__ import annotations

import json

from .cognitive_action_protocol import ActionCost, build_action_receipt, validate_action_receipt
from .context_calibrated_role_adapter import ContextCalibratedResidentPool, _continuation_scores
from .grammar_backed_role_adapter import ROLE_ACTIONS, ROLE_OBJECTIVES, validate_grammar_output
from .provider_telemetry import hash_payload


STAGED_ADAPTER_VERSION = "staged_semantic_scoring_adapter_v0_16"


class StagedSemanticResidentPool(ContextCalibratedResidentPool):
    def score_labels(self, *, model_id, role_id, item):
        if not self.all_resident:
            raise RuntimeError("staged_semantic_pool_not_fully_resident")
        if model_id not in self._resident:
            raise ValueError(f"staged_semantic_model_not_registered:{model_id}")
        with self._generation_lock:
            tokenizer, model = self._resident[model_id]
            if role_id == "OBJECT_GROUNDING":
                primary = _symmetric_primary(
                    tokenizer=tokenizer, model=model, item=item, role_id=role_id,
                    labels=("A", "B", "NONE", "UNKNOWN"), device=self.device,
                )
                selected = max(primary["scores"], key=primary["scores"].get)
                if selected in ("A", "B"):
                    selected_text = item["candidate_a" if selected == "A" else "candidate_b"]
                    basis = _calibrated_stage(
                        tokenizer=tokenizer, model=model,
                        context=_basis_prompt(item, selected_text, null=False),
                        null=_basis_prompt(item, "withheld candidate meaning", null=True),
                        labels=("LEXICAL", "COMPOSITIONAL"), device=self.device,
                    )
                    basis_label = max(basis["scores"], key=basis["scores"].get)
                    result = {
                        "selected_object": "CANDIDATE_" + selected,
                        "selection_basis": "LEXICAL_EXACT" if basis_label == "LEXICAL" else "COMPOSITIONAL_ENTAILMENT",
                    }
                    secondary = basis
                elif selected == "NONE":
                    basis = _calibrated_stage(
                        tokenizer=tokenizer, model=model,
                        context=_open_basis_prompt(item, null=False),
                        null=_open_basis_prompt(item, null=True),
                        labels=("DEFAULT", "NO_PREFERENCE"), device=self.device,
                    )
                    basis_label = max(basis["scores"], key=basis["scores"].get)
                    result = {"selected_object": "NONE", "selection_basis": "PRAGMATIC_DEFAULT" if basis_label == "DEFAULT" else "NO_PREFERENCE"}
                    secondary = basis
                else:
                    result = {"selected_object": "UNCERTAIN", "selection_basis": "UNCERTAIN"}
                    secondary = None
            elif role_id == "PRAGMATIC_DEFAULT":
                primary = _symmetric_primary(
                    tokenizer=tokenizer, model=model, item=item, role_id=role_id,
                    labels=("A", "B", "NONE", "UNKNOWN"), device=self.device,
                )
                selected = max(primary["scores"], key=primary["scores"].get)
                result = {"pragmatic_preference": {"A": "CANDIDATE_A", "B": "CANDIDATE_B", "NONE": "NONE", "UNKNOWN": "UNCERTAIN"}[selected]}
                secondary = None
            else:
                primary = _calibrated_stage(
                    tokenizer=tokenizer, model=model,
                    context=_skeptic_prompt(item, null=False),
                    null=_skeptic_prompt(item, null=True),
                    labels=("COMPLETE", "INCOMPLETE", "UNKNOWN"), device=self.device,
                )
                selected = max(primary["scores"], key=primary["scores"].get)
                result = {"assessment_completeness": {"COMPLETE": "COMPLETE", "INCOMPLETE": "INCOMPLETE", "UNKNOWN": "UNCERTAIN"}[selected]}
                secondary = None
            stages = [primary] + ([secondary] if secondary else [])
            margins = [stage["margin"] for stage in stages]
            return {
                "result": result,
                "stages": stages,
                "margin": min(margins),
                "input_tokens": sum(stage["input_tokens"] for stage in stages),
                "output_tokens": sum(stage["output_tokens"] for stage in stages),
                "latency_ms": sum(stage["latency_ms"] for stage in stages),
            }


class StagedSemanticRoleAdapter:
    def __init__(self, *, model_id, pool):
        self.model_id = model_id
        self.pool = pool

    def invoke(self, *, role_id, item, evidence_refs):
        object_ref = "object://" + item["conflict_id"]
        scored = self.pool.score_labels(model_id=self.model_id, role_id=role_id, item=item)
        uncertainty = 0.75 if scored["margin"] < 0.05 else 0.45 if scored["margin"] < 0.2 else 0.2
        result = scored["result"]
        receipt = build_action_receipt(
            action_id="action-" + hash_payload([STAGED_ADAPTER_VERSION, self.model_id, role_id, object_ref])[:18],
            action_type=ROLE_ACTIONS[role_id], object_ref=object_ref,
            actor_role=role_id, actor_instance=self.model_id,
            method=STAGED_ADAPTER_VERSION,
            result_state="OPEN" if uncertainty >= 0.7 else "CANDIDATE",
            result=result, evidence_refs=evidence_refs,
            support=("context-calibrated staged semantic classification",),
            uncertainty=uncertainty,
            recommended_next_actions=("CLARIFY",) if uncertainty >= 0.7 else ("SYNTHESIZE",),
            cost=ActionCost(provider_calls=1, input_tokens=scored["input_tokens"], output_tokens=scored["output_tokens"], latency_ms=scored["latency_ms"]),
        )
        validate_action_receipt(receipt)
        score_commitment = {
            "score_version": STAGED_ADAPTER_VERSION,
            "stages": scored["stages"],
            "margin": scored["margin"],
            "orientation_control": role_id in ("OBJECT_GROUNDING", "PRAGMATIC_DEFAULT"),
            "null_calibration": True,
            "reference_value_present": False,
        }
        score_receipt = {**score_commitment, "score_hash": hash_payload(score_commitment)}
        commitment = {
            "adapter_version": STAGED_ADAPTER_VERSION,
            "model_id": self.model_id, "role_id": role_id, "object_ref": object_ref,
            "registry_hash": hash_payload([STAGED_ADAPTER_VERSION, role_id]),
            "selected_call": "STAGED_SCORE",
            "action_receipt": receipt, "score_receipt": score_receipt,
            "wall_latency_ms": scored["latency_ms"], "reference_available": False,
        }
        output = {**commitment, "output_hash": hash_payload(commitment)}
        validate_grammar_output(output, item=item)
        return output


def _symmetric_primary(*, tokenizer, model, item, role_id, labels, device):
    original = _calibrated_stage(
        tokenizer=tokenizer, model=model,
        context=_primary_prompt(item, role_id, swapped=False, null=False),
        null=_primary_prompt(item, role_id, swapped=False, null=True),
        labels=labels, device=device,
    )
    swapped = _calibrated_stage(
        tokenizer=tokenizer, model=model,
        context=_primary_prompt(item, role_id, swapped=True, null=False),
        null=_primary_prompt(item, role_id, swapped=True, null=True),
        labels=labels, device=device,
    )
    scores = {
        "A": (original["scores"]["A"] + swapped["scores"]["B"]) / 2,
        "B": (original["scores"]["B"] + swapped["scores"]["A"]) / 2,
        "NONE": (original["scores"]["NONE"] + swapped["scores"]["NONE"]) / 2,
        "UNKNOWN": (original["scores"]["UNKNOWN"] + swapped["scores"]["UNKNOWN"]) / 2,
    }
    return {
        "stage": "SYMMETRIC_PRIMARY",
        "scores": scores,
        "orientation_scores": {"original": original["scores"], "swapped": swapped["scores"]},
        "margin": _margin(scores),
        "input_tokens": original["input_tokens"] + swapped["input_tokens"],
        "output_tokens": original["output_tokens"] + swapped["output_tokens"],
        "latency_ms": original["latency_ms"] + swapped["latency_ms"],
    }


def _calibrated_stage(*, tokenizer, model, context, null, labels, device):
    import time
    started = time.perf_counter()
    context_prompt = _render_messages(tokenizer, context)
    null_prompt = _render_messages(tokenizer, null)
    context_scores, context_tokens = _continuation_scores(tokenizer=tokenizer, model=model, prompt=context_prompt, continuations=labels, device=device)
    null_scores, null_tokens = _continuation_scores(tokenizer=tokenizer, model=model, prompt=null_prompt, continuations=labels, device=device)
    scores = {label: context_scores[index] - null_scores[index] for index, label in enumerate(labels)}
    return {
        "stage": "CALIBRATED_LABELS", "labels": list(labels), "scores": scores,
        "context_scores": dict(zip(labels, context_scores)), "null_scores": dict(zip(labels, null_scores)),
        "margin": _margin(scores), "input_tokens": context_tokens + null_tokens,
        "output_tokens": sum(len(tokenizer.encode(label, add_special_tokens=False)) for label in labels) * 2,
        "latency_ms": max(1, round((time.perf_counter() - started) * 1000)),
    }


def _primary_prompt(item, role_id, *, swapped, null):
    if null:
        candidate_a, candidate_b, prompt = "withheld option one", "withheld option two", "The object request is withheld."
    elif swapped:
        candidate_a, candidate_b, prompt = item["candidate_b"], item["candidate_a"], item["public_prompt"]
    else:
        candidate_a, candidate_b, prompt = item["candidate_a"], item["candidate_b"], item["public_prompt"]
    question = "Which option is the more useful contextual default? Answer A, B, NONE, or UNKNOWN." if role_id == "PRAGMATIC_DEFAULT" else "Which option is semantically selected? Answer A, B, NONE, or UNKNOWN."
    return _messages(role_id, f"Request: {prompt}\nCandidate A: {candidate_a}\nCandidate B: {candidate_b}\n{question}")


def _basis_prompt(item, selected_text, *, null):
    prompt = "The object request is withheld." if null else item["public_prompt"]
    return _messages("OBJECT_GROUNDING", f"Request: {prompt}\nSelected candidate: {selected_text}\nIs selection fixed by exact lexical wording or composed meaning? Answer LEXICAL or COMPOSITIONAL.")


def _open_basis_prompt(item, *, null):
    prompt = "The object request and candidates are withheld." if null else json.dumps({key: item[key] for key in ("public_prompt", "candidate_a", "candidate_b")}, ensure_ascii=True)
    return _messages("OBJECT_GROUNDING", f"Object: {prompt}\nIf neither candidate is semantically fixed, does one still have a contextual default advantage? Answer DEFAULT or NO_PREFERENCE.")


def _skeptic_prompt(item, *, null):
    prompt = "The object request and candidate meanings are withheld." if null else json.dumps({key: item[key] for key in ("public_prompt", "candidate_a", "candidate_b")}, ensure_ascii=True)
    return _messages("ASSESSMENT_SKEPTIC", f"Object: {prompt}\nIs there enough displayed information to complete the semantic assessment, where a justified open result counts as complete? Answer COMPLETE, INCOMPLETE, or UNKNOWN.")


def _messages(role_id, content):
    return [
        {"role": "system", "content": f"You are a context-isolated role. {ROLE_OBJECTIVES[role_id]}"},
        {"role": "user", "content": content},
    ]


def _render_messages(tokenizer, messages):
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception as exc:
        if type(exc).__name__ != "TemplateError":
            raise
        merged = "\n\n".join(item["content"] for item in messages)
        return tokenizer.apply_chat_template([{"role": "user", "content": merged}], tokenize=False, add_generation_prompt=True)


def _margin(scores):
    ordered = sorted(scores.values(), reverse=True)
    return ordered[0] - ordered[1] if len(ordered) > 1 else 0.0
