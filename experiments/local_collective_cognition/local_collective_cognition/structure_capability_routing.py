"""Transfer-candidate capability routing and cheap packet pre-gating."""

from __future__ import annotations

import re

from .provider_telemetry import hash_payload


STRUCTURE_CAPABILITY_ROUTING_VERSION = "structure_elicitor_capability_routing_v0_1"
PLACEHOLDER_PRE_GATE_VERSION = "structure_packet_placeholder_pre_gate_v0_1"


DEFAULT_ELICITOR_EVIDENCE = (
    {"model_id": "gemma-2-2b-it", "independent_trials": 2, "total_field_gain": 4},
    {"model_id": "qwen2.5-1.5b-instruct", "independent_trials": 2, "total_field_gain": 1},
    {"model_id": "llama-3.2-1b-instruct", "independent_trials": 2, "total_field_gain": 0},
)


def route_structure_elicitor(*, eligible_model_ids, source_report_hash, evidence=DEFAULT_ELICITOR_EVIDENCE):
    eligible = set(eligible_model_ids)
    ranked = sorted(
        (item for item in evidence if item["model_id"] in eligible),
        key=lambda item: (
            item["total_field_gain"] / item["independent_trials"],
            item["independent_trials"], item["model_id"],
        ),
        reverse=True,
    )
    if not ranked:
        raise ValueError("structure_elicitor_capability_candidate_unavailable")
    selected = ranked[0]
    commitment = {
        "policy_version": STRUCTURE_CAPABILITY_ROUTING_VERSION,
        "selected_model_id": selected["model_id"],
        "eligible_model_ids": sorted(eligible),
        "evidence": list(evidence),
        "source_report_hash": source_report_hash,
        "support_mode": "TRANSFER_CANDIDATE_EXPLORATORY",
        "same_context_support": False,
        "selection_authority": False,
        "retention_authority": False,
    }
    return {**commitment, "receipt_hash": hash_payload(commitment)}


def packet_placeholder_pre_gate(*, packet, public_prompt):
    text = str(packet.get("contrastive_packet", "")).strip()
    item_id = str(packet.get("item_id", "")).strip()
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    reasons = []
    if normalized in {item_id.lower(), public_prompt.strip().lower()}:
        reasons.append("PACKET_IDENTIFIER_OR_PROMPT_ONLY")
    if len(normalized) < 24:
        reasons.append("PACKET_TOO_SHORT_FOR_STRUCTURAL_CONTENT")
    if re.fullmatch(r"(?:todo|tbd|n/?a|none|placeholder|unknown|<[^>]+>)", normalized):
        reasons.append("PACKET_EXPLICIT_PLACEHOLDER")
    commitment = {
        "gate_version": PLACEHOLDER_PRE_GATE_VERSION,
        "item_id": item_id,
        "packet_hash": hash_payload(packet),
        "public_prompt_hash": hash_payload(public_prompt),
        "status": "BLOCK" if reasons else "ALLOW",
        "reasons": list(dict.fromkeys(reasons)),
        "mechanical_only": True,
        "provider_authority": False,
    }
    return {**commitment, "receipt_hash": hash_payload(commitment)}
