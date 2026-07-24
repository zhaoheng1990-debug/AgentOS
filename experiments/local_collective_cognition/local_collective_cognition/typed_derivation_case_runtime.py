"""Candidate revision runtime using a Harness-issued typed derivation scaffold."""

from __future__ import annotations

from .candidate_revision_case_runtime import CandidateRevisionCaseRuntime
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .typed_derivation_contracts import typed_derivation_schema, validate_typed_derivation
from .typed_derivation_receipt import TypedDerivationVerifier


class TypedDerivationCaseRuntime(CandidateRevisionCaseRuntime):
    def __init__(self, base) -> None:
        super().__init__(base)
        self.verifier = TypedDerivationVerifier(base.harness)

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        scaffold = self.base.harness.derivation_scaffold(item_id)
        run = self._execute(
            role_id=f"typed-derivation-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_argument",
            objective=(
                "Re-evaluate the original candidate using the supplied public-value scaffold. Build sequential "
                "steps with {step_id, operator, inputs}; each input must name a scaffold value or earlier step. "
                "Return the final supported option, or ABSTAIN with no steps. Never emit formulas or prose."
            ), item_id=item_id,
            round_context={"role": "isolated_typed_candidate_revision", "candidate_id": candidate_id,
                           "original_candidate": candidate_label, "peer_output": "withheld",
                           "derivation_scaffold": scaffold,
                           "step_rules": "STEP_n sequential; result_step is final STEP_n"},
            schema=typed_derivation_schema(item_id, candidate_id, scaffold), stage="ARGUMENT",
        )
        try:
            validate_typed_derivation(
                run.result, item_id=item_id, candidate_id=candidate_id,
                evidence_refs=list(self.base.harness.evidence_refs), scaffold=scaffold,
            )
        except ValueError as exc:
            raise DisagreementCaseProviderFailure(
                stage="ARGUMENT", run=run, failures=(str(exc),),
            ) from exc
        return run

    @staticmethod
    def _record(candidate_id, candidate_label, argument, receipt):
        return {
            "candidate_id": candidate_id, "candidate_label": argument["proposed_candidate"],
            "original_candidate": candidate_label,
            "proposed_candidate": argument["proposed_candidate"],
            "steps": argument["steps"], "result_step": argument["result_step"],
            "verification_receipt": receipt.as_dict(),
        }
