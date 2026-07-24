"""Pair-conditioned resolution using an independently charged third witness."""

from __future__ import annotations

from .resolution_exploration_policy import ResolutionExplorationPolicy
from .structural_operator_policy import StructuralOperatorDecision, ranked_context_models


def build_context_exploration_schedule(
    *, context_credit, profiles, item_domains, item_fingerprints,
    existing_schedule: dict[str, str], budget: int = 2,
) -> dict[str, str]:
    if budget < 0 or set(item_domains) != set(item_fingerprints) or not set(existing_schedule).issubset(item_domains):
        raise ValueError("context_exploration_schedule_invalid")
    candidates = []
    for item_id, fingerprint in item_fingerprints.items():
        if item_id in existing_schedule:
            continue
        ranked = ranked_context_models(
            profiles=profiles, fingerprint=fingerprint, domain=item_domains[item_id],
        )
        pair = context_credit.pair_credit(ranked[0], ranked[1])
        unseen = 1 if pair.feature_type == "GLOBAL" else 0
        uncertainty = 1.0 - min(1.0, abs(pair.expected_net_cbit))
        score = 3.0 * unseen + uncertainty + 1.0 / (1.0 + pair.total)
        candidates.append((score, item_id))
    return {item_id: "PEER_SECOND" for _, item_id in sorted(candidates, reverse=True)[:budget]}


class ContextAwareResolutionPolicy(ResolutionExplorationPolicy):
    def __init__(
        self,
        *,
        context_credit,
        model_ids: tuple[str, ...],
        minimum_context_net_cbit: float = 0.10,
        **values,
    ) -> None:
        super().__init__(**values)
        if len(model_ids) != 3 or len(set(model_ids)) != 3:
            raise ValueError("context_resolution_model_scope_invalid")
        self.context_credit = context_credit
        self.model_ids = frozenset(model_ids)
        self.minimum_context_net_cbit = minimum_context_net_cbit

    def resolve_probe(self, decision, primary, peer) -> StructuralOperatorDecision:
        if decision.action != "VERIFY_PEER" or decision.reviewer_model_id != peer.model_id:
            raise ValueError("context_resolution_probe_binding_invalid")
        if primary.answer == peer.answer:
            return super().resolve_probe(decision, primary, peer)
        context_ids = self.model_ids - {primary.model_id, peer.model_id}
        if len(context_ids) != 1:
            raise ValueError("context_resolution_witness_binding_invalid")
        return StructuralOperatorDecision(**{
            **decision.__dict__, "action": "REQUEST_CONTEXT_WITNESS",
            "context_model_id": next(iter(context_ids)),
            "reason": "primary_peer_disagreement_requires_independent_context",
            "final_answer": "",
        })

    def resolve_context(self, decision, primary, peer, witness) -> StructuralOperatorDecision:
        if (
            decision.action != "REQUEST_CONTEXT_WITNESS"
            or decision.primary_model_id != primary.model_id
            or decision.reviewer_model_id != peer.model_id
            or decision.context_model_id != witness.model_id
        ):
            raise ValueError("context_resolution_witness_result_binding_invalid")
        topology = (
            "THIRD_SUPPORTS_PEER" if witness.answer == peer.answer
            else "THIRD_SUPPORTS_PRIMARY" if witness.answer == primary.answer
            else "ALL_DIFFER"
        )
        signal = self.context_credit.resolve(
            fingerprint=self.item_fingerprints[primary.item_id],
            primary_model_id=primary.model_id,
            peer_model_id=peer.model_id,
            support_topology=topology,
        )
        override = signal.override_evidence_eligible and signal.expected_net_cbit >= self.minimum_context_net_cbit
        return StructuralOperatorDecision(**{
            **decision.__dict__,
            "action": "PEER_OVERRIDE_RESOLVED" if override else "PRIMARY_KEEP_RESOLVED",
            "final_answer": peer.answer if override else primary.answer,
            "reason": "context_credit_overrides" if override else "context_credit_keeps_primary",
            "resolution_policy": "CONTEXT_PEER_OVERRIDE" if override else "CONTEXT_KEEP_PRIMARY",
            "resolution_expected_net_cbit": signal.expected_net_cbit,
            "resolution_evidence_level": "PAIR_CONTEXT",
            "context_support_topology": topology,
            "context_expected_net_cbit": signal.expected_net_cbit,
            "context_pair_correction_surplus": signal.pair_correction_surplus,
            "context_pair_evidence_count": signal.pair_evidence_count,
            "context_witness_used": True,
        })
