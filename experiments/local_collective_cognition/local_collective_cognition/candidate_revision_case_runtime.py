"""Provider-backed belief revision with Harness replay before blinded judgment."""

from __future__ import annotations

from .candidate_revision_contracts import candidate_revision_schema, validate_candidate_revision
from .candidate_revision_receipt import CandidateRevisionVerifier
from .disagreement_case_failure import DisagreementCaseProviderFailure
from .verified_case_runtime import VerifiedDisagreementCaseRuntime


class CandidateRevisionCaseRuntime(VerifiedDisagreementCaseRuntime):
    def __init__(self, base) -> None:
        super().__init__(base)
        self.verifier = CandidateRevisionVerifier(base.harness)

    def _evidence_run(self, item_id: str, model_id: str, candidate_id: str, candidate_label: str):
        run = self._execute(
            role_id=f"candidate-revision-{model_id}-{item_id}", model_id=model_id,
            task_kind="pilot_disagreement_argument",
            objective=(
                "Re-evaluate the original candidate from the public question. Return one replayable expression "
                "and the option it actually supports. You may revise to A, B, C, or D; use ABSTAIN with an "
                "empty expression when no reliable derivation is available. Do not defend the original by default."
            ), item_id=item_id,
            round_context={"role": "isolated_candidate_revision", "candidate_id": candidate_id,
                           "original_candidate": candidate_label, "peer_output": "withheld"},
            schema=candidate_revision_schema(item_id, candidate_id), stage="ARGUMENT",
        )
        try:
            validate_candidate_revision(
                run.result, item_id, candidate_id, list(self.base.harness.evidence_refs),
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
            "expression": argument["expression"], "verification_receipt": receipt.as_dict(),
        }
