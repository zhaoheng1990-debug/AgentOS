"""Capability-routed quality lifecycle for one fresh structural holdout."""

from __future__ import annotations

from .quality_gated_structural_runtime import QualityGatedStructuralRuntime
from .structure_capability_routing import packet_placeholder_pre_gate, route_structure_elicitor


DEFAULT_ASSIGNMENTS = (
    ("modular-28", "qwen2.5-1.5b-instruct"),
    ("ratio-28", "llama-3.2-1b-instruct"),
    ("sets-28", "qwen2.5-1.5b-instruct"),
    ("bayes-28", "llama-3.2-1b-instruct"),
    ("string-28", "qwen2.5-1.5b-instruct"),
    ("unit-28", "llama-3.2-1b-instruct"),
)


class CapabilityRoutedStructuralRuntime(QualityGatedStructuralRuntime):
    def __init__(self, base, *, capability_source_report_hash):
        super().__init__(base)
        if len(capability_source_report_hash) != 64:
            raise ValueError("structure_capability_source_hash_invalid")
        self.capability_source_report_hash = capability_source_report_hash
        self._routing_receipt = None

    def run(self, *, experiment_id, assignments=DEFAULT_ASSIGNMENTS):
        report = super().run(experiment_id=experiment_id, assignments=assignments)
        protocol = report.get("protocol")
        if protocol:
            protocol.update({
                "protocol_version": "capability_routed_packet_quality_mini_pilot_v0_4",
                "evidence_backed_elicitor_routing": True,
                "routing_support_mode": "TRANSFER_CANDIDATE_EXPLORATORY",
                "mechanical_placeholder_pre_gate": True,
                "provider_semantic_quality_receipt_invoked": report.get("quality_judgment") is not None,
            })
        return report

    def _elicitor(self, assignments, selected_ids):
        proposers = {model_id for item_id, model_id in assignments if item_id in selected_ids}
        eligible = tuple(set(self.base.small_adapters) - proposers)
        self._routing_receipt = route_structure_elicitor(
            eligible_model_ids=eligible,
            source_report_hash=self.capability_source_report_hash,
        )
        return self._routing_receipt["selected_model_id"]

    def _mechanical_pre_gate(self, packet, public_prompt):
        return packet_placeholder_pre_gate(packet=packet, public_prompt=public_prompt)

    def _capability_routing_receipt(self):
        return self._routing_receipt
