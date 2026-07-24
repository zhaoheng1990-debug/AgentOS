"""Single-token enum scoring for bounded Provider decisions."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass


@dataclass(frozen=True)
class EnumScore:
    selected: str
    scores: tuple[dict[str, float | str], ...]
    selected_probability: float
    margin: float
    entropy: float
    input_tokens: int
    latency_ms: int


def score_enum(*, tokenizer, model, prompt, options, device) -> EnumScore:
    if not options or len(options) != len(set(options)):
        raise ValueError("enum_scoring_options_invalid")
    labels = single_token_labels(tokenizer, len(options))
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    started = time.perf_counter()
    import torch

    with torch.inference_mode():
        logits = model(**inputs).logits[0, -1]
    selected_logits = torch.stack([logits[token_id] for _, token_id in labels])
    probabilities = torch.softmax(selected_logits.float(), dim=0).tolist()
    ranked = sorted(range(len(options)), key=lambda index: probabilities[index], reverse=True)
    winner = ranked[0]
    scores = tuple({
        "option": option, "label": labels[index][0],
        "probability": round(float(probabilities[index]), 12),
    } for index, option in enumerate(options))
    entropy = -sum(value * math.log(value) for value in probabilities if value > 0.0)
    runner_up = probabilities[ranked[1]] if len(ranked) > 1 else 0.0
    return EnumScore(
        selected=options[winner], scores=scores,
        selected_probability=round(float(probabilities[winner]), 12),
        margin=round(float(probabilities[winner] - runner_up), 12),
        entropy=round(entropy, 12), input_tokens=int(inputs.input_ids.shape[1]),
        latency_ms=max(1, round((time.perf_counter() - started) * 1000)),
    )


def single_token_labels(tokenizer, count):
    candidates = [*"ABCDEFGHIJKLMNOPQRSTUVWXYZ", *"0123456789"]
    labels, token_ids = [], set()
    for label in candidates[:count]:
        encoded = tokenizer.encode(label, add_special_tokens=False)
        if len(encoded) != 1 or encoded[0] in token_ids:
            raise ValueError("enum_scoring_single_token_label_invalid")
        labels.append((label, int(encoded[0])))
        token_ids.add(int(encoded[0]))
    return tuple(labels)
