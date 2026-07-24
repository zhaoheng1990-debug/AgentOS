"""Protocol v0.8: hierarchical structural routing with bounded micro-probes."""

from __future__ import annotations

from typing import Any

from .calibrated_protocol import CalibratedCollaborationProtocol
from .hierarchical_fingerprint_credit import HierarchicalFingerprintProfile
from .holdout_v6_benchmark import (
    HOLDOUT_V6_BENCHMARK_ID,
    HOLDOUT_V6_ITEM_DOMAINS,
    HOLDOUT_V6_ITEM_FINGERPRINTS,
)
from .structural_probe_policy import StructuralMicroProbePolicy


STRUCTURAL_FINGERPRINT_PROTOCOL_VERSION = "structural_fingerprint_collaboration_protocol_v0_8"


class StructuralFingerprintCollaborationProtocol(CalibratedCollaborationProtocol):
    def __init__(
        self,
        *,
        profiles: dict[str, HierarchicalFingerprintProfile],
        fingerprint_credit_snapshot: dict[str, Any],
        probe_schedule: dict[str, str],
        **values: Any,
    ) -> None:
        snapshot_hash = fingerprint_credit_snapshot.get("snapshot_hash", "")
        values.setdefault("policy", StructuralMicroProbePolicy(profiles=profiles, probe_schedule=probe_schedule))
        values.setdefault("item_domains", HOLDOUT_V6_ITEM_DOMAINS)
        values.setdefault("item_contexts", HOLDOUT_V6_ITEM_FINGERPRINTS)
        values.setdefault("arm_namespace", "HOLDOUT_V6")
        values.setdefault("profile_receipt_hash", snapshot_hash)
        values.setdefault("exploration_schedule", {})
        super().__init__(profiles=profiles, **values)
        self.fingerprint_credit_snapshot = fingerprint_credit_snapshot
        self.probe_schedule = dict(probe_schedule)

    def run(self, experiment_id: str, **values: Any) -> dict[str, Any]:
        report = super().run(experiment_id, **values)
        probe_outcome = self.base.harness.calibrate_routing(
            experiment_id=experiment_id + "-micro-probe-outcome",
            calibration_receipt_hash=self.fingerprint_credit_snapshot["snapshot_hash"],
            route_decisions=tuple(report["route_decisions"]),
            item_domains=self.item_domains,
            resolved_actions=("MICRO_PROBE_RESOLVED",),
        )
        report["protocol"].update({
            "protocol_version": STRUCTURAL_FINGERPRINT_PROTOCOL_VERSION,
            "holdout_benchmark": HOLDOUT_V6_BENCHMARK_ID,
            "fingerprint_credit_snapshot_ref": self.fingerprint_credit_snapshot["snapshot_hash"],
            "historical_cycles_used_for_current_route": True,
            "v08_outcomes_used_for_current_route": False,
            "micro_probe_budget": len(self.probe_schedule),
            "structural_fingerprint_scope_bound": True,
        })
        report["hierarchical_fingerprint_credit"] = self.fingerprint_credit_snapshot
        report["micro_probe_schedule"] = self.probe_schedule
        report["micro_probe_outcome_receipt"] = probe_outcome.as_dict()
        report["structural_fingerprint_arm"] = report.pop("calibrated_arm")
        report["comparisons"].update({
            "micro_probe_corrections": probe_outcome.corrected_count,
            "micro_probe_harms": probe_outcome.harmed_count,
            "micro_probe_observed_net_cbit": probe_outcome.observed_net_cbit,
            "micro_probe_absolute_calibration_error": probe_outcome.absolute_calibration_error,
            "structural_fingerprint_improvement_status": report["comparisons"].pop("calibrated_improvement_status"),
        })
        return report
