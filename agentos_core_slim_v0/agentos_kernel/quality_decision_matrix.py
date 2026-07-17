"""Isolated quality decisions for AgentOS runtime artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


SEVERITY_INFO = "INFO"
SEVERITY_WARN = "WARN"
SEVERITY_BLOCKER = "BLOCKER"


@dataclass(frozen=True)
class QualityFinding:
    control_object: str
    severity: str
    repair_action: str
    blocking_effect: str
    evidence_refs: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "control_object": self.control_object,
            "severity": self.severity,
            "repair_action": self.repair_action,
            "blocking_effect": self.blocking_effect,
            "evidence_refs": list(self.evidence_refs),
        }


@dataclass(frozen=True)
class QualityDecision:
    gate_id: str
    status: str
    findings: tuple[QualityFinding, ...]
    blocked_control_objects: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "gate_id": self.gate_id,
            "status": self.status,
            "findings": [item.as_dict() for item in self.findings],
            "blocked_control_objects": list(self.blocked_control_objects),
        }


class EvidenceAdmissionGate:
    gate_id = "EvidenceAdmissionGate"

    def evaluate(self, context: dict[str, Any]) -> QualityDecision:
        findings: list[QualityFinding] = []
        for claim in context.get("claims", []):
            refs = tuple(claim.get("evidence_refs") or [])
            if not refs or not claim.get("support_path"):
                findings.append(
                    QualityFinding(
                        control_object=claim.get("claim_id", "claim"),
                        severity=SEVERITY_BLOCKER,
                        repair_action="attach_traceable_support_path_or_remove_claim",
                        blocking_effect="blocks_claim_admission_only",
                        evidence_refs=refs,
                    )
                )
        return _decision(self.gate_id, findings)


class ScopeCoverageGate:
    gate_id = "ScopeCoverageGate"

    def evaluate(self, context: dict[str, Any]) -> QualityDecision:
        findings: list[QualityFinding] = []
        for item in context.get("coverage_objects", []):
            state = item.get("state", "missing")
            if state == "missing":
                findings.append(
                    QualityFinding(
                        control_object=item["object_id"],
                        severity=SEVERITY_WARN,
                        repair_action="collect_more_evidence_or_mark_missing",
                        blocking_effect="qualifies_scope_without_blocking_readability",
                        evidence_refs=tuple(item.get("evidence_refs") or []),
                    )
                )
            elif state == "qualified":
                findings.append(
                    QualityFinding(
                        control_object=item["object_id"],
                        severity=SEVERITY_INFO,
                        repair_action="retain_qualification_label",
                        blocking_effect="no_readability_block",
                        evidence_refs=tuple(item.get("evidence_refs") or []),
                    )
                )
        return _decision(self.gate_id, findings)


class ReaderIntegrityGate:
    gate_id = "ReaderIntegrityGate"

    def evaluate(self, context: dict[str, Any]) -> QualityDecision:
        findings = tuple(
            QualityFinding(
                control_object=defect.get("revision_id", context.get("revision_id", "revision")),
                severity=SEVERITY_BLOCKER,
                repair_action=defect.get("repair_action", "repair_reader_surface"),
                blocking_effect="blocks_revision_readability_only",
                evidence_refs=tuple(defect.get("evidence_refs") or []),
            )
            for defect in context.get("reader_defects", [])
        )
        return _decision(self.gate_id, findings)


class PublicationRetentionGate:
    gate_id = "PublicationRetentionGate"

    def evaluate(self, context: dict[str, Any]) -> QualityDecision:
        findings: list[QualityFinding] = []
        if context.get("candidate_status") != "readable":
            findings.append(
                QualityFinding(
                    control_object=context.get("candidate_revision_id", "candidate_revision"),
                    severity=SEVERITY_BLOCKER,
                    repair_action="keep_previous_published_pointer",
                    blocking_effect="blocks_current_pointer_move_only",
                    evidence_refs=tuple(context.get("evidence_refs") or []),
                )
            )
        return _decision(self.gate_id, findings)


class BaselineEligibilityGate:
    gate_id = "BaselineEligibilityGate"

    def evaluate(self, context: dict[str, Any]) -> QualityDecision:
        findings: list[QualityFinding] = []
        if not context.get("baseline_authorization"):
            findings.append(
                QualityFinding(
                    control_object=context.get("candidate_revision_id", "candidate_revision"),
                    severity=SEVERITY_BLOCKER,
                    repair_action="request_baseline_authorization",
                    blocking_effect="blocks_baseline_pointer_move_only",
                    evidence_refs=tuple(context.get("evidence_refs") or []),
                )
            )
        return _decision(self.gate_id, findings)


class QualityDecisionMatrix:
    """Runs quality gates without collapsing their control objects."""

    def __init__(self) -> None:
        self.gates = {
            EvidenceAdmissionGate.gate_id: EvidenceAdmissionGate(),
            ScopeCoverageGate.gate_id: ScopeCoverageGate(),
            ReaderIntegrityGate.gate_id: ReaderIntegrityGate(),
            PublicationRetentionGate.gate_id: PublicationRetentionGate(),
            BaselineEligibilityGate.gate_id: BaselineEligibilityGate(),
        }

    def evaluate(self, gate_id: str, context: dict[str, Any]) -> QualityDecision:
        if gate_id not in self.gates:
            raise ValueError(f"unknown_quality_gate:{gate_id}")
        return self.gates[gate_id].evaluate(context)


def _decision(gate_id: str, findings: list[QualityFinding] | tuple[QualityFinding, ...]) -> QualityDecision:
    items = tuple(findings)
    blocked = tuple(item.control_object for item in items if item.severity == SEVERITY_BLOCKER)
    return QualityDecision(
        gate_id=gate_id,
        status="BLOCKED" if blocked else "PASS",
        findings=items,
        blocked_control_objects=blocked,
    )
