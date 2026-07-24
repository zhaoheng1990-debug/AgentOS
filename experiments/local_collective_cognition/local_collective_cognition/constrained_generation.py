"""Greedy token-trie decoding over a finite set of registered tool calls."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class ConstrainedCallGeneration:
    selected_call: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class TokenTrie:
    TERMINAL = -1

    def __init__(self, sequences):
        self.root = {}
        for sequence in sequences:
            if not sequence:
                raise ValueError("constrained_call_tokens_empty")
            node = self.root
            for token in sequence:
                node = node.setdefault(int(token), {})
            node[self.TERMINAL] = {}

    def allowed(self, prefix, eos_token_id):
        node = self.root
        for token in prefix:
            node = node.get(int(token))
            if node is None:
                raise ValueError("constrained_call_prefix_outside_registry")
        allowed = [token for token in node if token != self.TERMINAL]
        if self.TERMINAL in node:
            allowed.append(int(eos_token_id))
        return allowed


def generate_constrained_call(*, tokenizer, model, prompt, calls, device):
    if not calls or len(calls) != len(set(calls)):
        raise ValueError("constrained_call_registry_invalid")
    eos = tokenizer.eos_token_id
    if eos is None:
        raise ValueError("constrained_call_eos_missing")
    sequences = [tuple(tokenizer.encode(call, add_special_tokens=False)) for call in calls]
    if len(sequences) != len(set(sequences)):
        raise ValueError("constrained_call_token_collision")
    trie = TokenTrie(sequences)
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    input_tokens = int(inputs.input_ids.shape[1])
    started = time.perf_counter()

    def allowed_tokens(_, input_ids):
        return trie.allowed(input_ids[input_tokens:].tolist(), eos)

    import torch

    with torch.inference_mode():
        generated = model.generate(
            **inputs, max_new_tokens=max(len(item) for item in sequences) + 1,
            do_sample=False, eos_token_id=eos,
            pad_token_id=tokenizer.pad_token_id if tokenizer.pad_token_id is not None else eos,
            prefix_allowed_tokens_fn=allowed_tokens,
        )
    output = tuple(int(item) for item in generated[0][input_tokens:].tolist() if int(item) != eos)
    matches = [call for call, sequence in zip(calls, sequences) if sequence == output]
    if len(matches) != 1:
        raise ValueError("constrained_call_decode_not_registered")
    return ConstrainedCallGeneration(
        selected_call=matches[0], input_tokens=input_tokens, output_tokens=len(output),
        latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
    )
