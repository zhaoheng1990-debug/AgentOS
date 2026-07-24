"""Context-calibrated label scoring with reusable model/menu-size priors."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

from .enum_scoring import single_token_labels


@dataclass(frozen=True)
class EnumCalibrationPrior:
    log_probabilities: tuple[float, ...]
    probabilities: tuple[float, ...]
    input_tokens: int
    latency_ms: int


@dataclass(frozen=True)
class CalibratedEnumScore:
    selected: str
    scores: tuple[dict[str, float | str], ...]
    selected_probability: float
    margin: float
    entropy: float
    input_tokens: int
    latency_ms: int
    inference_passes: int
    calibration_ref: str
    calibration_cached: bool


def build_calibration_prior(*, tokenizer, model, prompt, count, device):
    labels = single_token_labels(tokenizer, count)
    log_probs, probabilities, tokens, latency = _label_distribution(
        tokenizer, model, prompt, labels, device,
    )
    return EnumCalibrationPrior(tuple(log_probs), tuple(probabilities), tokens, latency)


def score_calibrated_enum(*, tokenizer, model, prompt, options, device, prior,
                          calibration_ref, calibration_cached):
    if not options or len(options) != len(set(options)):
        raise ValueError("calibrated_enum_options_invalid")
    labels = single_token_labels(tokenizer, len(options))
    context_logs, context_probs, tokens, latency = _label_distribution(
        tokenizer, model, prompt, labels, device,
    )
    import torch

    adjusted = torch.tensor(context_logs) - torch.tensor(prior.log_probabilities)
    calibrated = torch.softmax(adjusted, dim=0).tolist()
    ranked = sorted(range(len(options)), key=lambda index: calibrated[index], reverse=True)
    winner = ranked[0]
    scores = tuple({
        "option": option, "label": labels[index][0],
        "probability": round(float(calibrated[index]), 12),
        "context_probability": round(float(context_probs[index]), 12),
        "prior_probability": round(float(prior.probabilities[index]), 12),
        "calibrated_log_ratio": round(float(adjusted[index]), 12),
    } for index, option in enumerate(options))
    entropy = -sum(value * math.log(value) for value in calibrated if value > 0.0)
    runner_up = calibrated[ranked[1]] if len(ranked) > 1 else 0.0
    return CalibratedEnumScore(
        selected=options[winner], scores=scores,
        selected_probability=round(float(calibrated[winner]), 12),
        margin=round(float(calibrated[winner] - runner_up), 12),
        entropy=round(entropy, 12),
        input_tokens=tokens + (0 if calibration_cached else prior.input_tokens),
        latency_ms=latency + (0 if calibration_cached else prior.latency_ms),
        inference_passes=1 if calibration_cached else 2,
        calibration_ref=calibration_ref, calibration_cached=calibration_cached,
    )


def _label_distribution(tokenizer, model, prompt, labels, device):
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    started = time.perf_counter()
    import torch

    with torch.inference_mode():
        logits = model(**inputs).logits[0, -1]
    selected = torch.stack([logits[token_id] for _, token_id in labels]).float()
    probabilities = torch.softmax(selected, dim=0).tolist()
    log_probabilities = torch.log_softmax(selected, dim=0).tolist()
    return (log_probabilities, probabilities, int(inputs.input_ids.shape[1]),
            max(1, round((time.perf_counter() - started) * 1000)))
