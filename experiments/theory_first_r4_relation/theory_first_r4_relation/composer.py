"""Runtime-owned deterministic packet composition."""

from __future__ import annotations

import math

from .contracts import (
    CognitivePacket,
    CompositionPlan,
    CompositionReceipt,
    hash_payload,
)


FORMULA = "SUM_PACKET_LOG_ODDS_MINUS_DUPLICATED_PRIOR_LOG_ODDS"


def compose(
    packets: tuple[CognitivePacket, ...], plan: CompositionPlan
) -> CompositionReceipt:
    packet_map = {packet.packet_id: packet for packet in packets}
    probability = None
    if plan.action != "BLOCK":
        selected = [packet_map[packet_id] for packet_id in plan.selected_packet_ids]
        prior = selected[0].prior_y1
        prior_log_odds = math.log(prior / (1.0 - prior))
        combined_log_odds = sum(
            math.log(packet.probability_y1 / (1.0 - packet.probability_y1))
            for packet in selected
        ) - (len(selected) - 1) * prior_log_odds
        probability = 1.0 / (1.0 + math.exp(-combined_log_odds))
    values = {
        "case_id": plan.case_id,
        "action": plan.action,
        "probability_y1": probability,
        "selected_packet_ids": plan.selected_packet_ids,
        "excluded_duplicate_ids": plan.excluded_duplicate_ids,
        "graph_hash": plan.graph_hash,
        "formula": FORMULA,
        "provider_calls": 0,
    }
    return CompositionReceipt(**values, receipt_hash=hash_payload(values))


def compose_naively(packets: tuple[CognitivePacket, ...]) -> float:
    prior = packets[0].prior_y1
    prior_log_odds = math.log(prior / (1.0 - prior))
    combined_log_odds = sum(
        math.log(packet.probability_y1 / (1.0 - packet.probability_y1))
        for packet in packets
    ) - (len(packets) - 1) * prior_log_odds
    return 1.0 / (1.0 + math.exp(-combined_log_odds))
