"""Receipt-source adapter for Anti-Additive governed baseline proposals."""

from __future__ import annotations

from agentos_kernel import BaselineEvolutionProposalProtocol, methodology_candidate_commitment

from .anti_additive_source import (
    AntiAdditiveMethodologyReceiptSource,
    resolve_anti_additive_methodology_receipt,
)


class AntiAdditiveBaselineEvolutionRuntime:
    """Keep source resolution outside the Kernel proposal protocol."""

    def __init__(
        self,
        *,
        project_scope: str,
        methodology_source: AntiAdditiveMethodologyReceiptSource,
        protocol: BaselineEvolutionProposalProtocol | None = None,
    ) -> None:
        if not project_scope.startswith("project://"):
            raise ValueError("baseline_evolution_runtime_project_scope_invalid")
        self.project_scope = project_scope
        self.methodology_source = methodology_source
        self.protocol = protocol or BaselineEvolutionProposalProtocol()

    def review_eligibility(self, candidate: dict, *, methodology_audit_id: str):
        receipt = resolve_anti_additive_methodology_receipt(
            source=self.methodology_source,
            audit_id=methodology_audit_id,
            project_scope=self.project_scope,
            candidate_id=str(candidate.get("candidate_id") or ""),
            candidate_payload_hash=methodology_candidate_commitment(candidate),
            target_type="BaselineEvolutionProposal",
            authority_requirement="CANDIDATE_ONLY",
        )
        return self.protocol.review_eligibility(
            candidate,
            methodology_receipt=receipt,
            require_methodology_receipt=True,
        )

    def build_proposal(self, candidate: dict, review):
        return self.protocol.build_proposal(candidate, review)
